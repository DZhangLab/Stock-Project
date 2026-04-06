"""
Daily closing quote collection job.
Corresponds to app.js functionality.
"""
import logging
from typing import Optional
from datetime import datetime
import zoneinfo

from ..config import load_config
from ..symbols import load_symbols
from ..db import get_db_manager
from ..twelve_data import TwelveDataClient, QuoteModel

logger = logging.getLogger(__name__)

# Quote collection is restricted to this time window (America/Chicago).
# The scheduler CronTrigger enforces the window at the trigger level;
# this constant is used for a defensive guard inside the job itself.
_QUOTE_TZ = zoneinfo.ZoneInfo("America/Chicago")
_QUOTE_START_HOUR = 8   # 08:00 inclusive
_QUOTE_END_HOUR = 18    # 18:00 exclusive


class QuoteCollector:
    """Collects daily closing quotes for all symbols."""
    
    def __init__(self):
        """Initialize quote collector with database and API clients."""
        self.config = load_config()
        self.db = get_db_manager()
        self.api_client = TwelveDataClient(self.config.api)
        self.symbols = load_symbols()
        self.current_index = 0
        self.max_iterations = 500
    
    def persist_quote(self, quote: QuoteModel) -> bool:
        """
        Persist quote data to everydayAfterClose table.
        
        Args:
            quote: QuoteModel instance with quote data
            
        Returns:
            bool: True if insert was successful
        """
        # Clean name: replace single quote with comma (matching JS behavior)
        name = quote.name.replace("'", ",")
        
        # Handle missing fifty_two_week fields gracefully
        fifty_two_week_low = quote.fifty_two_week_low
        fifty_two_week_high = quote.fifty_two_week_high
        fifty_two_week_low_change = quote.fifty_two_week_low_change
        fifty_two_week_high_change = quote.fifty_two_week_high_change
        fifty_two_week_low_change_percent = quote.fifty_two_week_low_change_percent
        fifty_two_week_high_change_percent = quote.fifty_two_week_high_change_percent
        fifty_two_week_range = quote.fifty_two_week_range
        
        insert_sql = """
        INSERT INTO everydayAfterClose (
            symbol, name, exchange, currency, datetime, timestamp,
            open, high, low, close, volume, previous_close, `change`,
            percent_change, average_volume, is_market_open,
            fifty_two_week_low, fifty_two_week_high, fifty_two_week_low_change,
            fifty_two_week_high_change, fifty_two_week_low_change_percent,
            fifty_two_week_high_change_percent, fifty_two_week_range
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
            name = VALUES(name),
            exchange = VALUES(exchange),
            currency = VALUES(currency),
            timestamp = VALUES(timestamp),
            open = VALUES(open),
            high = VALUES(high),
            low = VALUES(low),
            close = VALUES(close),
            volume = VALUES(volume),
            previous_close = VALUES(previous_close),
            `change` = VALUES(`change`),
            percent_change = VALUES(percent_change),
            average_volume = VALUES(average_volume),
            is_market_open = VALUES(is_market_open),
            fifty_two_week_low = VALUES(fifty_two_week_low),
            fifty_two_week_high = VALUES(fifty_two_week_high),
            fifty_two_week_low_change = VALUES(fifty_two_week_low_change),
            fifty_two_week_high_change = VALUES(fifty_two_week_high_change),
            fifty_two_week_low_change_percent = VALUES(fifty_two_week_low_change_percent),
            fifty_two_week_high_change_percent = VALUES(fifty_two_week_high_change_percent),
            fifty_two_week_range = VALUES(fifty_two_week_range)
        """
        
        # Convert boolean to int (0 or 1) for MySQL
        is_market_open_int = 1 if quote.is_market_open else 0
        
        params = (
            quote.symbol,
            name,
            quote.exchange,
            quote.currency,
            quote.datetime,
            quote.timestamp,
            quote.open,
            quote.high,
            quote.low,
            quote.close,
            quote.volume,
            quote.previous_close,
            quote.change,
            quote.percent_change,
            quote.average_volume,
            is_market_open_int,
            fifty_two_week_low,
            fifty_two_week_high,
            fifty_two_week_low_change,
            fifty_two_week_high_change,
            fifty_two_week_low_change_percent,
            fifty_two_week_high_change_percent,
            fifty_two_week_range
        )
        
        try:
            self.db.execute(insert_sql, params)
            logger.info(f"Successfully inserted quote for {quote.symbol}")
            return True
        except Exception as e:
            logger.error(f"Error inserting quote for {quote.symbol}: {e}")
            return False
    
    def collect_quote(self, symbol: str) -> bool:
        """
        Collect and persist quote for a single symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            bool: True if collection was successful
        """
        try:
            quote = self.api_client.get_quote(symbol)
            return self.persist_quote(quote)
        except Exception as e:
            logger.error(f"Error collecting quote for {symbol}: {e}")
            return False
    
    def run_quote_cycle(self) -> Optional[int]:
        """
        Run one cycle of quote collection.
        Processes one symbol and increments index.
        
        Returns:
            Optional[int]: Current index if successful, None if finished
        """
        if self.current_index >= min(len(self.symbols), self.max_iterations):
            logger.info(f"Quote collection finished. Processed {self.current_index} symbols.")
            return None
        
        symbol = self.symbols[self.current_index]
        success = self.collect_quote(symbol)
        
        if success:
            logger.info(f"Quote cycle {self.current_index}: {symbol} - Success")
        else:
            logger.warning(f"Quote cycle {self.current_index}: {symbol} - Failed")
        
        self.current_index += 1
        return self.current_index


# Global collector instance
_collector: Optional[QuoteCollector] = None


def get_quote_collector() -> QuoteCollector:
    """Get or create global quote collector instance."""
    global _collector
    if _collector is None:
        _collector = QuoteCollector()
    return _collector


def _outside_collection_window() -> bool:
    """Return True if current America/Chicago time is outside 08:00-18:00."""
    now = datetime.now(_QUOTE_TZ)
    return now.hour < _QUOTE_START_HOUR or now.hour >= _QUOTE_END_HOUR


def run_quote_cycle():
    """
    Function to be called by scheduler.
    Runs one quote collection cycle.
    """
    # Defensive guard: skip if outside the allowed collection window,
    # even if the scheduler fires unexpectedly.
    if _outside_collection_window():
        now = datetime.now(_QUOTE_TZ)
        logger.info(
            "Quote collection skipped: current time %s is outside "
            "the %02d:00-%02d:00 America/Chicago window.",
            now.strftime("%H:%M %Z"), _QUOTE_START_HOUR, _QUOTE_END_HOUR,
        )
        return

    collector = get_quote_collector()
    result = collector.run_quote_cycle()
    
    if result is None:
        logger.info("Quote collection completed. Stopping scheduler.")
    elif result % 100 == 0:
        logger.info(f"Quote collection progress: {result}/{min(len(collector.symbols), collector.max_iterations)}")

