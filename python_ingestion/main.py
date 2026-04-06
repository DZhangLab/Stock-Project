"""
Main entry point for scheduled data collection tasks.
Registers and runs scheduled jobs using APScheduler.
"""
import logging
import signal
import sys
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .jobs.quotes import run_quote_cycle
from .jobs.intraday import run_intraday_cycle
from .jobs.apple_news import run_apple_news_once
from .jobs.aapl_quarterly_snapshot import run_aapl_quarterly_snapshot_once
from .jobs.aapl_earnings_commentary import run_aapl_earnings_commentary_once
from .jobs.aapl_earnings_ai_analysis import run_aapl_earnings_ai_analysis_once
from .jobs.company_news_ai_summary import run_company_news_ai_summary_once

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
    # Quote collection job: runs once per minute, only during 08:00-17:59 America/Chicago.
    # Staggered to second :30 of each minute so quote and intraday API calls
    # don't land in the same second (intraday fires at :00).
    scheduler.add_job(
        run_quote_cycle,
        trigger=CronTrigger(
            second="30",
            minute="*",
            hour="8-17",
            timezone="America/Chicago",
        ),
        id="quote_collection",
        name="Daily Quote Collection",
        max_instances=1,
        replace_existing=True
    )
    
    # Intraday collection job: runs once per minute, only during 08:00-17:59 America/Chicago.
    # CronTrigger with hour="8-17" ensures the scheduler itself never fires outside the window.
    scheduler.add_job(
        run_intraday_cycle,
        trigger=CronTrigger(
            minute="*",
            hour="8-17",
            timezone="America/Chicago",
        ),
        id="intraday_collection",
        name="Intraday 1-Minute Collection",
        max_instances=1,
        replace_existing=True
    )
    
    # Apple news ingestion: daily at 08:00 AM
    scheduler.add_job(
        run_apple_news_once,
        trigger=CronTrigger(hour=8, minute=0),
        id="apple_news_ingestion",
        name="AAPL News Ingestion",
        max_instances=1,
        replace_existing=True
    )

    # Company news AI summary: daily at 08:10 AM (after news ingestion)
    scheduler.add_job(
        run_company_news_ai_summary_once,
        trigger=CronTrigger(hour=8, minute=10),
        kwargs={"symbol": "AAPL", "limit": 10},
        id="company_news_ai_summary",
        name="AAPL Company News AI Summary",
        max_instances=1,
        replace_existing=True
    )

    # Quarterly snapshot: every Monday at 08:05 AM
    scheduler.add_job(
        run_aapl_quarterly_snapshot_once,
        trigger=CronTrigger(day_of_week="mon", hour=8, minute=5),
        id="aapl_quarterly_snapshot",
        name="AAPL Quarterly Snapshot",
        max_instances=1,
        replace_existing=True
    )

    # Earnings commentary: every Monday at 08:15 AM
    scheduler.add_job(
        run_aapl_earnings_commentary_once,
        trigger=CronTrigger(day_of_week="mon", hour=8, minute=15),
        id="aapl_earnings_commentary",
        name="AAPL Earnings Commentary",
        max_instances=1,
        replace_existing=True
    )

    # Earnings AI analysis: every Monday at 08:30 AM
    scheduler.add_job(
        run_aapl_earnings_ai_analysis_once,
        trigger=CronTrigger(day_of_week="mon", hour=8, minute=30),
        id="aapl_earnings_ai_analysis",
        name="AAPL Earnings AI Analysis",
        max_instances=1,
        replace_existing=True
    )

    logger.info("Scheduled jobs registered:")
    logger.info("  - Quote Collection: every minute at :30s, 08:00-17:59 America/Chicago")
    logger.info("  - Intraday Collection: every minute, 08:00-17:59 America/Chicago")
    logger.info("  - AAPL News Ingestion: daily at 08:00")
    logger.info("  - AAPL Company News AI Summary: daily at 08:10")
    logger.info("  - AAPL Quarterly Snapshot: every Monday at 08:05")
    logger.info("  - AAPL Earnings Commentary: every Monday at 08:15")
    logger.info("  - AAPL Earnings AI Analysis: every Monday at 08:30")


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

