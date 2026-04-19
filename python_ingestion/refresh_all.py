"""
One-shot full data refresh for the pipeline scope.

Usage:
    python -m python_ingestion.refresh_all

Runs every data pipeline step once in dependency-safe order for each symbol
in PIPELINE_SYMBOLS (default: AAPL), then exits.
Does NOT start the scheduler — use main.py for that.
"""
import logging
import sys
import time

from .config import PIPELINE_SYMBOLS

logger = logging.getLogger(__name__)

STEPS = [
    "Quote",
    "Intraday",
    "Company News",
    "Company News AI Summary",
    "Quarterly Snapshot",
    "Earnings Commentary",
    "Earnings AI Analysis",
]

# Seconds to pause between Alpha Vantage-heavy steps to respect rate limits.
AV_COOLDOWN = 2.0


def _run_quote():
    from .jobs.quotes import QuoteCollector
    collector = QuoteCollector()
    total = 0
    for symbol in PIPELINE_SYMBOLS:
        total += collector.collect_quote(symbol) or 0
    return total


def _run_intraday():
    from .jobs.intraday import IntradayCollector
    collector = IntradayCollector()
    total = 0
    for symbol in PIPELINE_SYMBOLS:
        total += collector.collect_intraday(symbol) or 0
    return total


def _run_news():
    from .jobs.company_news import run_company_news_once
    total = 0
    for symbol in PIPELINE_SYMBOLS:
        total += run_company_news_once(symbol=symbol, limit=20) or 0
    return total


def _run_news_ai():
    from .jobs.company_news_ai_summary import run_company_news_ai_summary_once
    total = 0
    for symbol in PIPELINE_SYMBOLS:
        total += run_company_news_ai_summary_once(symbol=symbol, limit=10) or 0
    return total


def _run_quarterly():
    from .jobs.quarterly_snapshot import run_quarterly_snapshot_once
    total = 0
    for symbol in PIPELINE_SYMBOLS:
        total += run_quarterly_snapshot_once(symbol=symbol) or 0
    return total


def _run_earnings_commentary():
    from .jobs.earnings_commentary import run_earnings_commentary_once
    total = 0
    for symbol in PIPELINE_SYMBOLS:
        total += run_earnings_commentary_once(symbol=symbol) or 0
    return total


def _run_earnings_ai():
    from .jobs.earnings_ai_analysis import run_earnings_ai_analysis_once
    total = 0
    for symbol in PIPELINE_SYMBOLS:
        total += run_earnings_ai_analysis_once(symbol=symbol) or 0
    return total


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
    logger.info("Full refresh — one-shot pipeline (scope: %s)", PIPELINE_SYMBOLS)
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
