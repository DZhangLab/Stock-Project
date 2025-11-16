"""
Main entry point for scheduled data collection tasks.
Registers and runs scheduled jobs using APScheduler.
"""
import logging
import signal
import sys
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .jobs.quotes import run_quote_cycle
from .jobs.intraday import run_intraday_cycle

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("python_ingestion.log")
    ]
)

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = BackgroundScheduler()


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received. Stopping scheduler...")
        scheduler.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def register_jobs():
    """Register scheduled jobs with the scheduler."""
    # Quote collection job: runs every 9 seconds (matching app.js cron schedule)
    scheduler.add_job(
        run_quote_cycle,
        trigger=IntervalTrigger(seconds=9),
        id="quote_collection",
        name="Daily Quote Collection",
        max_instances=1,
        replace_existing=True
    )
    
    # Intraday collection job: runs every 20 seconds (matching collecting.js cron schedule)
    scheduler.add_job(
        run_intraday_cycle,
        trigger=IntervalTrigger(seconds=20),
        id="intraday_collection",
        name="Intraday 1-Minute Collection",
        max_instances=1,
        replace_existing=True
    )
    
    logger.info("Scheduled jobs registered:")
    logger.info("  - Quote Collection: every 9 seconds")
    logger.info("  - Intraday Collection: every 20 seconds")


def main():
    """Main entry point."""
    logger.info("Starting Python Stock Data Ingestion Service")
    
    # Setup signal handlers
    setup_signal_handlers()
    
    # Register jobs
    register_jobs()
    
    # Start scheduler
    try:
        scheduler.start()
        logger.info("Scheduler started. Press Ctrl+C to stop.")
        
        # Keep main thread alive
        import time
        while True:
            time.sleep(1)
            
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()
        logger.info("Shutdown complete.")


if __name__ == "__main__":
    main()

