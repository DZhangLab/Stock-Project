"""
One-shot full AAPL data refresh.

Usage:
    python -m python_ingestion.refresh_all

Runs every data pipeline step once in dependency-safe order, then exits.
Does NOT start the scheduler — use main.py for that.
"""
import logging
import sys
import time

logger = logging.getLogger(__name__)

STEPS = [
    "AAPL Quote",
    "AAPL Intraday",
    "AAPL News",
    "AAPL News AI Summary",
    "AAPL Quarterly Snapshot",
    "AAPL Earnings Commentary",
    "AAPL Earnings AI Analysis",
]

# Seconds to pause between Alpha Vantage-heavy steps to respect rate limits.
AV_COOLDOWN = 2.0


def _run_quote():
    from .jobs.quotes import QuoteCollector
    collector = QuoteCollector()
    return collector.collect_quote("AAPL")


def _run_intraday():
    from .jobs.intraday import IntradayCollector
    collector = IntradayCollector()
    return collector.collect_intraday("AAPL")


def _run_news():
    from .jobs.apple_news import run_apple_news_once
    return run_apple_news_once(limit=20)


def _run_news_ai():
    from .jobs.company_news_ai_summary import run_company_news_ai_summary_once
    return run_company_news_ai_summary_once(symbol="AAPL", limit=10)


def _run_quarterly():
    from .jobs.aapl_quarterly_snapshot import run_aapl_quarterly_snapshot_once
    return run_aapl_quarterly_snapshot_once()


def _run_earnings_commentary():
    from .jobs.aapl_earnings_commentary import run_aapl_earnings_commentary_once
    return run_aapl_earnings_commentary_once()


def _run_earnings_ai():
    from .jobs.aapl_earnings_ai_analysis import run_aapl_earnings_ai_analysis_once
    return run_aapl_earnings_ai_analysis_once()


# Each entry: (step_name, runner_func, sleep_after)
_PIPELINE = [
    (STEPS[0], _run_quote,                0),
    (STEPS[1], _run_intraday,             0),
    (STEPS[2], _run_news,                 AV_COOLDOWN),
    (STEPS[3], _run_news_ai,              0),
    (STEPS[4], _run_quarterly,            AV_COOLDOWN),
    (STEPS[5], _run_earnings_commentary,  AV_COOLDOWN),
    (STEPS[6], _run_earnings_ai,          0),
]


def refresh_all():
    """Run every pipeline step once, log results, and return a summary."""
    results = {}
    for step_name, runner, cooldown in _PIPELINE:
        logger.info("▶ Starting: %s", step_name)
        try:
            result = runner()
            results[step_name] = "ok"
            logger.info("✓ Finished: %s (result=%s)", step_name, result)
        except Exception:
            results[step_name] = "FAILED"
            logger.exception("✗ Failed: %s", step_name)

        if cooldown > 0:
            logger.info("  … cooling down %.1fs (API rate limit)", cooldown)
            time.sleep(cooldown)

    succeeded = sum(1 for v in results.values() if v == "ok")
    failed = len(results) - succeeded
    return succeeded, failed, results


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("=" * 60)
    logger.info("AAPL full refresh — one-shot pipeline")
    logger.info("=" * 60)

    succeeded, failed, results = refresh_all()

    logger.info("=" * 60)
    logger.info("Refresh complete: %s succeeded, %s failed", succeeded, failed)
    for step, status in results.items():
        logger.info("  %-30s %s", step, status)
    logger.info("=" * 60)

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
