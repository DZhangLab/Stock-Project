"""
Historical time range data collection job.
Corresponds to SingleCollection.js functionality.
"""
import logging
import argparse
from typing import List, Optional
from datetime import datetime, timedelta

from ..config import load_config
from ..symbols import normalize_table_name
from ..db import get_db_manager
from ..twelve_data import TwelveDataClient, TimeSeriesPoint

logger = logging.getLogger(__name__)


class HistoricalCollector:
    """Collects historical time series data for specified date ranges."""
    
    def __init__(self):
        """Initialize historical collector with database and API clients."""
        self.config = load_config()
        self.db = get_db_manager()
        self.api_client = TwelveDataClient(self.config.api)
    
    def ensure_table(self, symbol: str, table_name: Optional[str] = None) -> bool:
        """
        Ensure table exists for symbol or custom table name.
        
        Args:
            symbol: Stock symbol
            table_name: Optional custom table name (defaults to normalized symbol)
            
        Returns:
            bool: True if table exists or was created
        """
        if table_name is None:
            table_name = normalize_table_name(symbol)
        
        # Use the same table structure as intraday
        return self.db.ensure_intraday_table(symbol, table_name)
    
    def persist_historical_data(
        self,
        table_name: str,
        data_points: List[TimeSeriesPoint]
    ) -> int:
        """
        Persist historical data points to specified table using bulk insert.
        
        Args:
            table_name: Target table name
            data_points: List of time series data points
            
        Returns:
            int: Number of rows inserted
        """
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
            logger.info(f"Inserted {len(params_list)} rows into {table_name} (affected: {affected_rows})")
            return affected_rows
        except Exception as e:
            logger.error(f"Error inserting historical data into {table_name}: {e}")
            return 0
    
    def collect_range(
        self,
        symbol: str,
        start_datetime: datetime,
        end_datetime: datetime,
        table_name: Optional[str] = None
    ) -> int:
        """
        Collect historical data for a symbol within a date range.
        
        Args:
            symbol: Stock symbol
            start_datetime: Start datetime
            end_datetime: End datetime
            table_name: Optional custom table name
            
        Returns:
            int: Number of rows inserted
        """
        try:
            # Format dates for API (YYYY-MM-DD HH:MM:SS)
            start_date_str = start_datetime.strftime("%Y-%m-%d %H:%M:%S")
            end_date_str = end_datetime.strftime("%Y-%m-%d %H:%M:%S")
            
            # Determine table name
            if table_name is None:
                table_name = normalize_table_name(symbol)
            
            # Ensure table exists
            if not self.ensure_table(symbol, table_name):
                logger.error(f"Failed to ensure table {table_name} for {symbol}")
                return 0
            
            # Fetch time series data
            data_points = self.api_client.get_time_series_range(
                symbol=symbol,
                interval="1min",
                start_date=start_date_str,
                end_date=end_date_str
            )
            
            if not data_points:
                logger.warning(f"No data points returned for {symbol} in range {start_date_str} to {end_date_str}")
                return 0
            
            # Sort by datetime (ascending)
            data_points.sort(key=lambda x: x.datetime)
            
            # Persist data
            rows_inserted = self.persist_historical_data(table_name, data_points)
            
            logger.info(
                f"Collected {len(data_points)} data points for {symbol} "
                f"({start_date_str} to {end_date_str}), inserted {rows_inserted} rows"
            )
            
            return rows_inserted
            
        except Exception as e:
            logger.error(f"Error collecting historical data for {symbol}: {e}")
            return 0


def main():
    """CLI entry point for historical data collection."""
    parser = argparse.ArgumentParser(description="Collect historical stock data for a date range")
    parser.add_argument("symbol", help="Stock symbol (e.g., AAPL, MSFT)")
    parser.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--start-time", default="09:30:00", help="Start time (HH:MM:SS, default: 09:30:00)")
    parser.add_argument("--end-date", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--end-time", default="15:59:00", help="End time (HH:MM:SS, default: 15:59:00)")
    parser.add_argument("--table-name", help="Custom table name (defaults to normalized symbol)")
    
    args = parser.parse_args()
    
    # Parse dates
    try:
        start_datetime = datetime.strptime(
            f"{args.start_date} {args.start_time}",
            "%Y-%m-%d %H:%M:%S"
        )
        end_datetime = datetime.strptime(
            f"{args.end_date} {args.end_time}",
            "%Y-%m-%d %H:%M:%S"
        )
    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        return
    
    # Collect data
    collector = HistoricalCollector()
    rows_inserted = collector.collect_range(
        symbol=args.symbol,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        table_name=args.table_name
    )
    
    print(f"Collection complete. Inserted {rows_inserted} rows.")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    main()

