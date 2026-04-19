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
        Creates table if it doesn't exist, then migrates legacy schema
        if needed (INT price columns -> DECIMAL, missing UNIQUE KEY).

        Args:
            symbol: Stock symbol
            table_name: Optional custom table name (defaults to normalized symbol)

        Returns:
            bool: True if table exists or was created successfully
        """
        from .symbols import normalize_table_name

        if table_name is None:
            table_name = normalize_table_name(symbol)

        # Use DECIMAL for price data and DOUBLE for volume
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
            self._migrate_intraday_schema(table_name)
            logger.info(f"Table {table_name} ensured for symbol {symbol}")
            return True
        except Error as e:
            logger.error(f"Error creating table {table_name}: {e}")
            return False

    def _migrate_intraday_schema(self, table_name: str) -> None:
        """
        Migrate legacy intraday tables to the current schema.

        Fixes two problems found in tables created before the Python
        ingestion system was introduced:

        1. Price columns (minuteOpen/High/Low/Close) were INT, which
           truncated decimal prices on insert.  Changed to DECIMAL(18,4).
        2. Missing UNIQUE KEY on timePoint, which prevented ON DUPLICATE
           KEY UPDATE from working correctly.  Duplicates are removed
           (keeping the newest row) before adding the constraint.

        This method is idempotent — it checks information_schema before
        making any changes and is safe to call on every startup.
        """
        db_name = self.config.database

        # --- Step 1: Fix INT price columns -> DECIMAL(18,4) ---
        col_rows = self.execute(
            """
            SELECT DATA_TYPE FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
              AND COLUMN_NAME = 'minuteOpen'
            LIMIT 1
            """,
            (db_name, table_name),
        ) or []
        if col_rows and col_rows[0][0] == "int":
            self.execute(f"""
                ALTER TABLE {table_name}
                    MODIFY minuteOpen  DECIMAL(18, 4),
                    MODIFY minuteHigh  DECIMAL(18, 4),
                    MODIFY minuteLow   DECIMAL(18, 4),
                    MODIFY minuteClose DECIMAL(18, 4),
                    MODIFY minuteVolume DOUBLE
            """)
            logger.info(
                f"Migrated {table_name}: price columns INT -> DECIMAL(18,4)"
            )

        # --- Step 2: Ensure UNIQUE KEY uq_timepoint exists ---
        uq_rows = self.execute(
            """
            SELECT 1 FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
              AND INDEX_NAME = 'uq_timepoint'
            LIMIT 1
            """,
            (db_name, table_name),
        ) or []
        if not uq_rows:
            # Remove duplicate timePoints (keep the highest id per group)
            self.execute(f"""
                DELETE a FROM {table_name} a
                INNER JOIN (
                    SELECT timePoint, MAX(id) AS keep_id
                    FROM {table_name}
                    GROUP BY timePoint
                    HAVING COUNT(*) > 1
                ) b ON a.timePoint = b.timePoint AND a.id < b.keep_id
            """)
            self.execute(
                f"ALTER TABLE {table_name} ADD UNIQUE KEY uq_timepoint (timePoint)"
            )
            logger.info(f"Added UNIQUE KEY uq_timepoint to {table_name}")

    def ensure_company_news_table(self) -> bool:
        """
        Ensure company_news table exists.
        This table is used by the company news ingestion flow (symbol-keyed).

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
            av_overall_sentiment_score DECIMAL(10, 4) NULL,
            av_overall_sentiment_label VARCHAR(32) NULL,
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

            sentiment_score_rows = self.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name = 'company_news'
                  AND column_name = 'av_overall_sentiment_score'
                LIMIT 1
                """,
                (self.config.database,)
            ) or []
            if not sentiment_score_rows:
                self.execute(
                    "ALTER TABLE company_news ADD COLUMN av_overall_sentiment_score DECIMAL(10, 4) NULL AFTER published_at"
                )

            sentiment_label_rows = self.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name = 'company_news'
                  AND column_name = 'av_overall_sentiment_label'
                LIMIT 1
                """,
                (self.config.database,)
            ) or []
            if not sentiment_label_rows:
                self.execute(
                    "ALTER TABLE company_news ADD COLUMN av_overall_sentiment_label VARCHAR(32) NULL AFTER av_overall_sentiment_score"
                )

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

    def ensure_company_news_ai_summary_table(self) -> bool:
        """
        Ensure company_news_ai_summary table exists.

        Returns:
            bool: True if table exists or was created successfully
        """
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS company_news_ai_summary (
            id BIGINT NOT NULL AUTO_INCREMENT,
            symbol VARCHAR(16) NOT NULL,
            analysis_date DATE NOT NULL,
            source_window_label VARCHAR(64) NOT NULL,
            source_news_count INT NOT NULL,
            overall_sentiment_label VARCHAR(32) NOT NULL,
            overall_sentiment_summary TEXT NOT NULL,
            main_themes_json JSON NOT NULL,
            top_positive_driver TEXT NULL,
            top_risk_concern TEXT NULL,
            confidence_note TEXT NULL,
            provider VARCHAR(64) NOT NULL,
            model_name VARCHAR(128) NOT NULL,
            prompt_version VARCHAR(32) NOT NULL,
            source_articles_json JSON NULL,
            raw_model_response_json JSON NOT NULL,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY uq_company_news_ai_summary_symbol_analysis_date (symbol, analysis_date),
            INDEX idx_company_news_ai_summary_symbol_updated (symbol, updated_at DESC)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """

        try:
            self.execute(create_table_sql)
            logger.info("Table company_news_ai_summary ensured")
            return True
        except Error as e:
            logger.error(f"Error creating table company_news_ai_summary: {e}")
            return False

    def ensure_quarterly_reporting_snapshot_table(self) -> bool:
        """
        Ensure quarterly_reporting_snapshot table exists.

        Returns:
            bool: True if table exists or was created successfully
        """
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS quarterly_reporting_snapshot (
            id BIGINT NOT NULL AUTO_INCREMENT,
            symbol VARCHAR(16) NOT NULL,
            fiscal_date_ending DATE NOT NULL,
            reported_date DATE NULL,
            fiscal_period_label VARCHAR(32) NULL,
            reported_currency VARCHAR(16) NULL,
            total_revenue DECIMAL(20, 2) NULL,
            gross_profit DECIMAL(20, 2) NULL,
            operating_income DECIMAL(20, 2) NULL,
            net_income DECIMAL(20, 2) NULL,
            reported_eps DECIMAL(20, 4) NULL,
            estimated_eps DECIMAL(20, 4) NULL,
            surprise DECIMAL(20, 4) NULL,
            surprise_percentage DECIMAL(10, 4) NULL,
            source VARCHAR(64) NOT NULL DEFAULT 'ALPHA_VANTAGE',
            raw_payload_json JSON NULL,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY uq_quarterly_reporting_snapshot_symbol_fiscal_date (symbol, fiscal_date_ending),
            INDEX idx_quarterly_reporting_snapshot_symbol_updated (symbol, updated_at DESC)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """

        try:
            self.execute(create_table_sql)
            logger.info("Table quarterly_reporting_snapshot ensured")
            return True
        except Error as e:
            logger.error(f"Error creating table quarterly_reporting_snapshot: {e}")
            return False

    def ensure_earnings_call_summary_table(self) -> bool:
        """
        Ensure earnings_call_summary table exists.
        Stores latest earnings call management commentary summary per symbol.

        Returns:
            bool: True if table exists or was created successfully
        """
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS earnings_call_summary (
            id BIGINT NOT NULL AUTO_INCREMENT,
            symbol VARCHAR(16) NOT NULL,
            fiscal_period_label VARCHAR(32) NOT NULL,
            call_date DATE NULL,
            source VARCHAR(64) NOT NULL DEFAULT 'ALPHA_VANTAGE',
            summary_text MEDIUMTEXT NOT NULL,
            key_takeaways_json JSON NULL,
            transcript_url VARCHAR(1024) NULL,
            raw_payload_json JSON NULL,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY uq_earnings_call_summary_symbol_period (symbol, fiscal_period_label),
            INDEX idx_earnings_call_summary_symbol_updated (symbol, updated_at DESC)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """

        try:
            self.execute(create_table_sql)
            logger.info("Table earnings_call_summary ensured")
            return True
        except Error as e:
            logger.error(f"Error creating table earnings_call_summary: {e}")
            return False

    def ensure_earnings_ai_analysis_table(self) -> bool:
        """
        Ensure earnings_ai_analysis table exists.
        Stores latest earnings AI analysis per symbol by fiscal period.

        Returns:
            bool: True if table exists or was created successfully
        """
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS earnings_ai_analysis (
            id BIGINT NOT NULL AUTO_INCREMENT,
            symbol VARCHAR(16) NOT NULL,
            fiscal_period_label VARCHAR(32) NOT NULL,
            call_date DATE NULL,
            source VARCHAR(64) NOT NULL DEFAULT 'ALPHA_VANTAGE',
            transcript_url VARCHAR(1024) NULL,
            transcript_char_count INT NOT NULL,
            transcript_segment_count INT NOT NULL,
            tone_analyzer VARCHAR(64) NOT NULL,
            tone_summary_json JSON NOT NULL,
            overall_tone VARCHAR(32) NOT NULL,
            key_highlights_json JSON NOT NULL,
            main_risks_concerns_json JSON NOT NULL,
            outlook_guidance_json JSON NOT NULL,
            provider VARCHAR(64) NOT NULL,
            model_name VARCHAR(128) NOT NULL,
            prompt_version VARCHAR(32) NOT NULL,
            raw_model_response_json JSON NOT NULL,
            raw_transcript_payload_json JSON NULL,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY uq_earnings_ai_analysis_symbol_period (symbol, fiscal_period_label),
            INDEX idx_earnings_ai_analysis_symbol_updated (symbol, updated_at DESC)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """

        try:
            self.execute(create_table_sql)
            logger.info("Table earnings_ai_analysis ensured")
            return True
        except Error as e:
            logger.error(f"Error creating table earnings_ai_analysis: {e}")
            return False
    
    def has_valid_earnings_call_summary(self, symbol: str, fiscal_period_label: str) -> bool:
        """Return True if a complete earnings call summary exists for the given quarter."""
        rows = self.execute(
            "SELECT summary_text FROM earnings_call_summary "
            "WHERE symbol = %s AND fiscal_period_label = %s LIMIT 1",
            (symbol, fiscal_period_label),
        )
        if not rows:
            return False
        summary = rows[0][0] if rows[0] else None
        return bool(summary and str(summary).strip())

    def has_valid_earnings_ai_analysis(self, symbol: str, fiscal_period_label: str) -> bool:
        """Return True if a complete AI earnings analysis exists for the given quarter."""
        rows = self.execute(
            "SELECT overall_tone FROM earnings_ai_analysis "
            "WHERE symbol = %s AND fiscal_period_label = %s LIMIT 1",
            (symbol, fiscal_period_label),
        )
        if not rows:
            return False
        tone = rows[0][0] if rows[0] else None
        return bool(tone and str(tone).strip())

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
