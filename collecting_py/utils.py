"""Utility helpers shared across collectors."""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Iterable


_RESERVED_WORDS = {"ACCESS", "ADD", "ALL", "ALTER", "ANALYZE", "AND", "AS", "ASC", "CHANGE", "COLUMN", "CREATE", "DELETE", "DESC", "DISTINCT", "DROP", "FROM", "GROUP", "INDEX", "INSERT", "LIKE", "LIMIT", "ORDER", "PRIMARY", "REFERENCES", "RENAME", "SCHEMA", "SELECT", "SET", "TABLE", "TRIGGER", "UNION", "UNIQUE", "UPDATE", "WHERE", "NOW"}


@lru_cache()
def normalise_symbol(symbol: str) -> str:
    """Return a database-friendly table suffix derived from *symbol*.

    The original JavaScript scripts contained a series of ``if`` statements that
    replaced problematic characters (``.`` or ``/``) and reserved words such as
    ``NOW``.  The Python version provides a deterministic transformation:

    * keep alphanumeric characters, replacing everything else with ``_``;
    * ensure the name starts with an alphabetic prefix;
    * suffix reserved words with ``_SYM`` to avoid clashing with SQL keywords.
    """

    cleaned = re.sub(r"[^0-9a-zA-Z]", "_", symbol.upper())
    if not cleaned:
        raise ValueError("Symbol cannot be empty after sanitisation")
    if cleaned[0].isdigit():
        cleaned = f"SYM_{cleaned}"
    if cleaned in _RESERVED_WORDS:
        cleaned = f"{cleaned}_SYM"
    return cleaned


def chunked(iterable: Iterable, size: int):
    """Yield successive chunks from *iterable* with at most ``size`` items."""

    chunk = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk

