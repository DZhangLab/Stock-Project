"""
Intraday 1-minute interval data collection job.
Corresponds to collecting.js functionality.
"""
import logging
from typing import List, Tuple, Optional
from datetime import datetime

from ..config import load_config
from ..symbols import load_symbols, normalize_table_name
from ..db import get_db_manager
from ..twelve_data import TwelveDataClient, TimeSeriesPoint

logger = logging.getLogger(__name__)


class IntradayCollector:
    """Collects intraday 1-minute data for all symbols."""
    
    def __init__(self):
        """Initialize intraday collector with database and API clients."""
        self.config = load_config()
        self.db = get_db_manager()
        self.api_client = TwelveDataClient(self.config.api)
        self.symbols = load_symbols()
        self.current_index = 0
        self.max_iterations = 500
    
    def ensure_table(self, symbol: str) -> bool:
        """
        Ensure table exists for symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            bool: True if table exists or was created
        """
        return self.db.ensure_intraday_table(symbol)
    
    def persist_intraday_data(self, symbol: str, data_points: List[TimeSeriesPoint]) -> int:
        """
        Persist intraday data points to symbol's table using bulk insert.
        
        Args:
            symbol: Stock symbol
            data_points: List of time series data points
            
        Returns:
            int: Number of rows inserted
        """
        table_name = normalize_table_name(symbol)
        
        # Prepare data for bulk insert
        insert_sql = f"""
        INSERT INTO {table_name} (timePoint, minuteOpen, minuteHigh, minuteLow, minuteClose, minuteVolume)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            minuteOpen = VALUES(minuteOpen),
            minuteHigh = VALUES(minuteHigh),
            minuteLow = VALUES(minuteLow),
            minuteClose = VALUES(minuteClose),
            minuteVolume = VALUES(minuteVolume)
        """
        
        # Convert data points to tuples
        params_list = [
            (
                point.datetime,
                point.open,
                point.high,
                point.low,
                point.close,
                point.volume
            )
            for point in data_points
        ]
        
        try:
            affected_rows = self.db.executemany(insert_sql, params_list)
            logger.info(f"Inserted {len(params_list)} rows for {symbol} (affected: {affected_rows})")
            return affected_rows
        except Exception as e:
            logger.error(f"Error inserting intraday data for {symbol}: {e}")
            return 0
    
    def collect_intraday(self, symbol: str) -> bool:
        """
        Collect and persist intraday data for a single symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            bool: True if collection was successful
        """
        try:
            # Ensure table exists
            if not self.ensure_table(symbol):
                logger.error(f"Failed to ensure table for {symbol}")
                return False
            
            # Fetch 390 data points (1 minute intervals for trading day)
            data_points = self.api_client.get_intraday(symbol, interval="1min", outputsize=390)
            
            if not data_points:
                logger.warning(f"No data points returned for {symbol}")
                return False
            
            # Sort by datetime (ascending) to ensure chronological order
            data_points.sort(key=lambda x: x.datetime)
            
            # Persist data
            rows_inserted = self.persist_intraday_data(symbol, data_points)
            
            if rows_inserted > 0:
                logger.info(f"Successfully collected {rows_inserted} data points for {symbol}")
                return True
            else:
                logger.warning(f"No rows inserted for {symbol}")
                return False
                
        except Exception as e:
            logger.error(f"Error collecting intraday data for {symbol}: {e}")
            return False
    
    def run_intraday_cycle(self) -> Optional[int]:
        """
        Run one cycle of intraday collection.
        Processes one symbol and increments index.
        
        Returns:
            Optional[int]: Current index if successful, None if finished
        """
        if self.current_index >= min(len(self.symbols), self.max_iterations):
            logger.info(f"Intraday collection finished. Processed {self.current_index} symbols.")
            return None
        
        symbol = self.symbols[self.current_index]
        success = self.collect_intraday(symbol)
        
        if success:
            logger.info(f"Intraday cycle {self.current_index}: {symbol} - Success")
        else:
            logger.warning(f"Intraday cycle {self.current_index}: {symbol} - Failed")
        
        self.current_index += 1
        return self.current_index


# Global collector instance
_collector: Optional[IntradayCollector] = None


def get_intraday_collector() -> IntradayCollector:
    """Get or create global intraday collector instance."""
    global _collector
    if _collector is None:
        _collector = IntradayCollector()
    return _collector


def run_intraday_cycle():
    """
    Function to be called by scheduler.
    Runs one intraday collection cycle.
    """
    collector = get_intraday_collector()
    result = collector.run_intraday_cycle()
    
    if result is None:
        logger.info("Intraday collection completed. Stopping scheduler.")
    elif result % 100 == 0:
        logger.info(f"Intraday collection progress: {result}/{min(len(collector.symbols), collector.max_iterations)}")


