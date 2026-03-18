"""
Database module for MySQL connection pooling, table creation, and batch operations.
"""
import logging
import mysql.connector
from mysql.connector import pooling, Error
from mysql.connector.pooling import MySQLConnectionPool
from typing import List, Tuple, Optional, Any
from contextlib import contextmanager

from .config import DatabaseConfig, load_config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages MySQL database connections and operations."""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        """
        Initialize database manager with connection pool.
        
        Args:
            config: Database configuration. If None, loads from environment.
        """
        if config is None:
            config = load_config().database
        
        self.config = config
        self.pool: Optional[MySQLConnectionPool] = None
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize MySQL connection pool."""
        try:
            pool_config = {
                "pool_name": "stock_pool",
                "pool_size": self.config.pool_size,
                "pool_reset_session": self.config.pool_reset_session,
                "host": self.config.host,
                "port": self.config.port,
                "user": self.config.user,
                "password": self.config.password,
                "database": self.config.database,
                "autocommit": self.config.autocommit,
                "charset": "utf8mb4",
                "collation": "utf8mb4_unicode_ci",
                "connect_timeout": 10,
                "use_unicode": True,
            }
            
            self.pool = mysql.connector.pooling.MySQLConnectionPool(**pool_config)
            logger.info(f"Database connection pool initialized with size {self.config.pool_size}")
        except Error as e:
            logger.error(f"Error creating connection pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for getting database connections from pool.
        
        Yields:
            mysql.connector.connection.MySQLConnection: Database connection
        """
        connection = None
        try:
            connection = self.pool.get_connection()
            yield connection
        except Error as e:
            logger.error(f"Error getting connection from pool: {e}")
            if connection:
                connection.rollback()
            raise
        finally:
            if connection and connection.is_connected():
                connection.close()
    
    def execute(self, sql: str, params: Optional[Tuple] = None) -> Optional[Any]:
        """
        Execute a single SQL statement.
        
        Args:
            sql: SQL statement with placeholders (%s)
            params: Parameters for the SQL statement
            
        Returns:
            Optional result from cursor.fetchall() or cursor.lastrowid
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, params or ())
                result = cursor.fetchall() if cursor.description else cursor.lastrowid
                conn.commit()
                return result
            except Error as e:
                logger.error(f"Error executing SQL: {e}")
                conn.rollback()
                raise
            finally:
                cursor.close()
    
    def executemany(self, sql: str, params_list: List[Tuple]) -> int:
        """
        Execute a SQL statement multiple times with different parameters.
        
        Args:
            sql: SQL statement with placeholders (%s)
            params_list: List of parameter tuples
            
        Returns:
            int: Number of affected rows
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.executemany(sql, params_list)
                affected_rows = cursor.rowcount
                conn.commit()
                logger.info(f"Bulk insert: {affected_rows} rows affected")
                return affected_rows
            except Error as e:
                logger.error(f"Error executing bulk SQL: {e}")
                conn.rollback()
                raise
            finally:
                cursor.close()
    
    def ensure_intraday_table(self, symbol: str, table_name: Optional[str] = None) -> bool:
        """
        Ensure intraday table exists for the given symbol.
        Creates table if it doesn't exist.
        
        Args:
            symbol: Stock symbol
            table_name: Optional custom table name (defaults to normalized symbol)
            
        Returns:
            bool: True if table exists or was created successfully
        """
        from .symbols import normalize_table_name
        
        if table_name is None:
            table_name = normalize_table_name(symbol)
        
        # Use DECIMAL for price data and DOUBLE for volume to match JS behavior
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INT NOT NULL AUTO_INCREMENT,
            timePoint DATETIME NOT NULL,
            minuteOpen DECIMAL(18, 4),
            minuteHigh DECIMAL(18, 4),
            minuteLow DECIMAL(18, 4),
            minuteClose DECIMAL(18, 4),
            minuteVolume DOUBLE,
            PRIMARY KEY (id),
            UNIQUE KEY uq_timepoint (timePoint),
            INDEX idx_timepoint (timePoint)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        
        try:
            self.execute(create_table_sql)
            logger.info(f"Table {table_name} ensured for symbol {symbol}")
            return True
        except Error as e:
            logger.error(f"Error creating table {table_name}: {e}")
            return False

    def ensure_company_news_table(self) -> bool:
        """
        Ensure company_news table exists.
        This table is used by the Apple news MVP ingestion flow.

        Returns:
            bool: True if table exists or was created successfully
        """
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS company_news (
            id BIGINT NOT NULL AUTO_INCREMENT,
            symbol VARCHAR(16) NOT NULL,
            title VARCHAR(512) NOT NULL,
            summary TEXT NULL,
            url VARCHAR(1024) NOT NULL,
            url_hash CHAR(64) NOT NULL,
            source VARCHAR(128) NULL,
            published_at DATETIME NOT NULL,
            ingestion_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY uq_company_news_symbol_url_hash (symbol, url_hash),
            INDEX idx_company_news_symbol_published_at (symbol, published_at DESC)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """

        try:
            self.execute(create_table_sql)

            # Minimal forward-compatible migration for existing tables.
            column_rows = self.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name = 'company_news'
                  AND column_name = 'url_hash'
                LIMIT 1
                """,
                (self.config.database,)
            ) or []
            if not column_rows:
                self.execute("ALTER TABLE company_news ADD COLUMN url_hash CHAR(64) NULL AFTER url")
            self.execute("UPDATE company_news SET url_hash = SHA2(url, 256) WHERE url_hash IS NULL")
            self.execute("ALTER TABLE company_news MODIFY COLUMN url_hash CHAR(64) NOT NULL")

            old_unique_rows = self.execute(
                """
                SELECT 1
                FROM information_schema.statistics
                WHERE table_schema = %s
                  AND table_name = 'company_news'
                  AND index_name = 'uq_company_news_symbol_url'
                LIMIT 1
                """,
                (self.config.database,)
            ) or []
            if old_unique_rows:
                self.execute("ALTER TABLE company_news DROP INDEX uq_company_news_symbol_url")

            new_unique_rows = self.execute(
                """
                SELECT 1
                FROM information_schema.statistics
                WHERE table_schema = %s
                  AND table_name = 'company_news'
                  AND index_name = 'uq_company_news_symbol_url_hash'
                LIMIT 1
                """,
                (self.config.database,)
            ) or []
            if not new_unique_rows:
                self.execute(
                    "ALTER TABLE company_news ADD UNIQUE KEY uq_company_news_symbol_url_hash (symbol, url_hash)"
                )

            logger.info("Table company_news ensured")
            return True
        except Error as e:
            logger.error(f"Error creating table company_news: {e}")
            return False
    
    def close_pool(self):
        """Close all connections in the pool."""
        if self.pool:
            # MySQL connector pool doesn't have explicit close method
            # Connections are closed when pool is garbage collected
            logger.info("Database pool will be closed on cleanup")
            self.pool = None


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager(config: Optional[DatabaseConfig] = None) -> DatabaseManager:
    """
    Get or create global database manager instance.
    
    Args:
        config: Database configuration. Only used on first call.
        
    Returns:
        DatabaseManager: Global database manager instance
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(config)
    return _db_manager

