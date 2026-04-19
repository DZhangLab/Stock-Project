"""
Quarterly reporting snapshot ingestion job.
Supports any stock symbol (defaults to AAPL for backward compatibility).
"""
import argparse
import json
import logging
import time
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from ..alpha_vantage import AlphaVantageClient
from ..db import get_db_manager

logger = logging.getLogger(__name__)


class QuarterlySnapshotCollector:
    SOURCE = "ALPHA_VANTAGE"
    REQUEST_DELAY_SECONDS = 1.3

    def __init__(self, symbol: str = "AAPL"):
        self.symbol = symbol.strip().upper()
        self.db = get_db_manager()
        self.api_client = AlphaVantageClient()

    def ensure_table(self) -> bool:
        return self.db.ensure_quarterly_reporting_snapshot_table()

    @staticmethod
    def _parse_date(value: Any) -> Optional[date]:
        if value is None:
            return None
        raw = str(value).strip()
        if not raw:
            return None
        for pattern in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
            try:
                return datetime.strptime(raw, pattern).date()
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            return None

    @staticmethod
    def _safe_decimal(value: Any) -> Optional[Decimal]:
        if value is None:
            return None
        raw = str(value).strip()
        if not raw or raw.lower() == "none":
            return None
        try:
            return Decimal(raw)
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _derive_period_label(fiscal_date: Optional[date]) -> Optional[str]:
        if fiscal_date is None:
            return None
        quarter = ((fiscal_date.month - 1) // 3) + 1
        return f"FY{fiscal_date.year}Q{quarter}"

    @staticmethod
    def _latest_row(payload: Dict[str, Any], key: str) -> Optional[Dict[str, Any]]:
        rows = payload.get(key, [])
        if not isinstance(rows, list) or not rows:
            return None
        valid_rows = [row for row in rows if isinstance(row, dict)]
        valid_rows.sort(key=lambda row: str(row.get("fiscalDateEnding", "")), reverse=True)
        return valid_rows[0] if valid_rows else None

    @staticmethod
    def _top_n_rows(payload: Dict[str, Any], key: str, n: int = 8) -> List[Dict[str, Any]]:
        """Return the *n* most recent quarterly rows sorted by fiscalDateEnding DESC."""
        rows = payload.get(key, [])
        if not isinstance(rows, list) or not rows:
            return []
        valid = [r for r in rows if isinstance(r, dict)]
        valid.sort(key=lambda r: str(r.get("fiscalDateEnding", "")), reverse=True)
        return valid[:n]

    @staticmethod
    def _earnings_index(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        result: Dict[str, Dict[str, Any]] = {}
        rows = payload.get("quarterlyEarnings", [])
        if not isinstance(rows, list):
            return result
        for row in rows:
            if not isinstance(row, dict):
                continue
            fiscal = str(row.get("fiscalDateEnding", "")).strip()
            if fiscal:
                result[fiscal] = row
        return result

    def _select_rows(
        self,
        income_payload: Dict[str, Any],
        earnings_payload: Dict[str, Any],
    ) -> Optional[Tuple[Dict[str, Any], Optional[Dict[str, Any]]]]:
        income_row = self._latest_row(income_payload, "quarterlyReports")
        if income_row is None:
            logger.warning("INCOME_STATEMENT quarterlyReports is empty")
            return None

        earnings_by_fiscal = self._earnings_index(earnings_payload)
        income_fiscal = str(income_row.get("fiscalDateEnding", "")).strip()
        earnings_row = earnings_by_fiscal.get(income_fiscal)

        if earnings_row is None:
            fallback = self._latest_row(earnings_payload, "quarterlyEarnings")
            if fallback is not None:
                logger.warning(
                    "No matching earnings quarter for fiscalDateEnding=%s, using fallback quarter=%s",
                    income_fiscal or "N/A",
                    fallback.get("fiscalDateEnding"),
                )
                earnings_row = fallback
            else:
                logger.warning("EARNINGS quarterlyEarnings is empty")

        return income_row, earnings_row

    def _select_multiple_rows(
        self,
        income_payload: Dict[str, Any],
        earnings_payload: Dict[str, Any],
        n: int = 8,
    ) -> List[Tuple[Dict[str, Any], Optional[Dict[str, Any]]]]:
        """Select up to *n* recent quarters, pairing each income row with its earnings row."""
        income_rows = self._top_n_rows(income_payload, "quarterlyReports", n)
        if not income_rows:
            logger.warning("INCOME_STATEMENT quarterlyReports is empty")
            return []
        earnings_by_fiscal = self._earnings_index(earnings_payload)
        pairs: List[Tuple[Dict[str, Any], Optional[Dict[str, Any]]]] = []
        for inc in income_rows:
            fiscal = str(inc.get("fiscalDateEnding", "")).strip()
            pairs.append((inc, earnings_by_fiscal.get(fiscal)))
        return pairs

    def _build_params(
        self,
        income_row: Dict[str, Any],
        earnings_row: Optional[Dict[str, Any]],
    ) -> Optional[Tuple]:
        fiscal_date = self._parse_date(income_row.get("fiscalDateEnding"))
        if fiscal_date is None:
            logger.warning("Missing or invalid fiscalDateEnding")
            return None

        reported_date = self._parse_date(income_row.get("reportedDate"))
        if reported_date is None and earnings_row is not None:
            reported_date = self._parse_date(earnings_row.get("reportedDate"))

        payload = {
            "income_statement": income_row,
            "earnings": earnings_row or {},
        }

        return (
            self.symbol,
            fiscal_date,
            reported_date,
            self._derive_period_label(fiscal_date),
            str(income_row.get("reportedCurrency", "")).strip()[:16] or None,
            self._safe_decimal(income_row.get("totalRevenue")),
            self._safe_decimal(income_row.get("grossProfit")),
            self._safe_decimal(income_row.get("operatingIncome")),
            self._safe_decimal(income_row.get("netIncome")),
            self._safe_decimal(earnings_row.get("reportedEPS")) if earnings_row else None,
            self._safe_decimal(earnings_row.get("estimatedEPS")) if earnings_row else None,
            self._safe_decimal(earnings_row.get("surprise")) if earnings_row else None,
            self._safe_decimal(earnings_row.get("surprisePercentage")) if earnings_row else None,
            self.SOURCE,
            json.dumps(payload, ensure_ascii=True),
        )

    def persist_snapshot(self, params: Tuple) -> int:
        sql = """
        INSERT INTO quarterly_reporting_snapshot (
            symbol, fiscal_date_ending, reported_date, fiscal_period_label, reported_currency,
            total_revenue, gross_profit, operating_income, net_income,
            reported_eps, estimated_eps, surprise, surprise_percentage, source, raw_payload_json
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
            reported_date = VALUES(reported_date),
            fiscal_period_label = VALUES(fiscal_period_label),
            reported_currency = VALUES(reported_currency),
            total_revenue = VALUES(total_revenue),
            gross_profit = VALUES(gross_profit),
            operating_income = VALUES(operating_income),
            net_income = VALUES(net_income),
            reported_eps = VALUES(reported_eps),
            estimated_eps = VALUES(estimated_eps),
            surprise = VALUES(surprise),
            surprise_percentage = VALUES(surprise_percentage),
            source = VALUES(source),
            raw_payload_json = VALUES(raw_payload_json),
            updated_at = CURRENT_TIMESTAMP
        """
        self.db.execute(sql, params)
        return 1

    def collect_latest_snapshot(self) -> int:
        if not self.ensure_table():
            logger.error("Failed to ensure quarterly_reporting_snapshot table")
            return 0

        try:
            income_payload = self.api_client.get_income_statement(self.symbol)
            # Free-tier safety: Alpha Vantage allows roughly 1 request/second.
            # This prevents the second call from being sent too quickly.
            time.sleep(self.REQUEST_DELAY_SECONDS)
            earnings_payload = self.api_client.get_earnings(self.symbol)
        except ValueError as e:
            logger.error("%s", e)
            return 0
        except Exception as e:
            logger.error("Error fetching quarterly snapshot data: %s", e)
            return 0

        selected = self._select_rows(income_payload, earnings_payload)
        if selected is None:
            return 0

        income_row, earnings_row = selected
        params = self._build_params(income_row, earnings_row)
        if params is None:
            return 0

        try:
            self.persist_snapshot(params)
            logger.info(
                "Saved quarterly snapshot: symbol=%s fiscal_date_ending=%s period=%s",
                params[0],
                params[1],
                params[3],
            )
            return 1
        except Exception as e:
            logger.error("Error persisting quarterly snapshot: %s", e)
            return 0


    def collect_recent_snapshots(self, n: int = 8) -> int:
        """Fetch and persist the most recent *n* quarters (default 8 for YoY coverage)."""
        if not self.ensure_table():
            logger.error("Failed to ensure quarterly_reporting_snapshot table")
            return 0

        try:
            income_payload = self.api_client.get_income_statement(self.symbol)
            time.sleep(self.REQUEST_DELAY_SECONDS)
            earnings_payload = self.api_client.get_earnings(self.symbol)
        except ValueError as e:
            logger.error("%s", e)
            return 0
        except Exception as e:
            logger.error("Error fetching quarterly snapshot data: %s", e)
            return 0

        pairs = self._select_multiple_rows(income_payload, earnings_payload, n)
        saved = 0
        for income_row, earnings_row in pairs:
            params = self._build_params(income_row, earnings_row)
            if params is None:
                continue
            try:
                self.persist_snapshot(params)
                saved += 1
            except Exception as e:
                logger.error("Error persisting snapshot for fiscal_date=%s: %s", params[1], e)

        logger.info("Saved %d quarterly snapshots for %s", saved, self.symbol)
        return saved


def run_quarterly_snapshot_once(symbol: str = "AAPL") -> int:
    collector = QuarterlySnapshotCollector(symbol=symbol)
    return collector.collect_recent_snapshots()


def main():
    parser = argparse.ArgumentParser(description="Collect and store quarterly reporting snapshots")
    parser.add_argument("--symbol", default="AAPL", help="Stock symbol, default: AAPL")
    args = parser.parse_args()

    rows = run_quarterly_snapshot_once(symbol=args.symbol)
    print(f"{args.symbol} quarterly snapshot ingestion complete. Affected rows: {rows}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    main()
