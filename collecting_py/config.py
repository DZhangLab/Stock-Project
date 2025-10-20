"""Configuration helpers for the Python data collection package.

This module centralises the logic for reading environment variables and
providing strongly typed access to runtime configuration.  It mirrors the
behaviour that existed implicitly in the JavaScript scripts where API keys and
MySQL credentials were hard coded, but exposes them in a single place so the new
collectors can depend on a consistent set of settings.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import os
from pathlib import Path
from typing import Iterable, List, Optional

from zoneinfo import ZoneInfo


ENV_FILE = Path(__file__).resolve().parent / ".env"


def _parse_env_file(path: Path) -> None:
    """Populate ``os.environ`` from a simple ``.env`` file if present.

    The implementation intentionally avoids third-party dependencies so that the
    collectors can run in constrained environments.  Lines that start with ``#``
    are treated as comments and ignored.  Variables that already exist in the
    environment are left untouched, preserving user overrides.
    """

    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass
class Settings:
    """Runtime configuration for the collectors.

    Attributes mirror the knobs that previously lived across multiple JavaScript
    files (API keys, request cadence, database credentials).  Storing the data in
    a dataclass simplifies passing configuration around without relying on global
    state.
    """

    twelve_api_key: str
    database_url: str
    timezone: ZoneInfo = field(default_factory=lambda: ZoneInfo("America/New_York"))
    request_timeout: int = 30
    intraday_symbols: List[str] = field(default_factory=list)
    intraday_interval_seconds: int = 20
    quote_symbols: List[str] = field(default_factory=list)
    quote_interval_seconds: int = 9

    history_batch_days: int = 7

    @classmethod
    def from_environment(cls) -> "Settings":
        """Build :class:`Settings` from the current process environment."""

        timezone_name = os.getenv("TZ", "America/New_York")
        tz = ZoneInfo(timezone_name)

        intraday_symbols = _split_symbols(os.getenv("INTRADAY_SYMBOLS"))
        if not intraday_symbols:
            default_path = Path(__file__).resolve().parent / 'data' / 'symbols.txt'
            intraday_symbols = list(load_default_symbol_list(default_path))
        quote_symbols = _split_symbols(os.getenv("QUOTE_SYMBOLS"))
        if not quote_symbols:
            quote_symbols = intraday_symbols

        return cls(
            twelve_api_key=_required("TWELVE_API_KEY"),
            database_url=_required("DATABASE_URL"),
            timezone=tz,
            request_timeout=int(os.getenv("REQUEST_TIMEOUT", "30")),
            intraday_symbols=intraday_symbols,
            intraday_interval_seconds=int(os.getenv("INTRADAY_INTERVAL_SECONDS", "20")),
            quote_symbols=quote_symbols,
            quote_interval_seconds=int(os.getenv("QUOTE_INTERVAL_SECONDS", "9")),
            history_batch_days=int(os.getenv("HISTORY_BATCH_DAYS", "7")),
        )


@lru_cache()
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance.

    The cache ensures every module receives the same configuration object and
    avoids repeatedly parsing environment variables.
    """

    _parse_env_file(ENV_FILE)
    return Settings.from_environment()


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required.")
    return value


def _split_symbols(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return [symbol.strip().upper() for symbol in raw.split(",") if symbol.strip()]


def load_default_symbol_list(path: Path) -> Iterable[str]:
    """Read a newline separated list of tickers from *path* if it exists."""

    if not path.exists():
        return []
    return [line.strip().upper() for line in path.read_text(encoding="utf8").splitlines() if line.strip()]

