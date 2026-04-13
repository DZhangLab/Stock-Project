"""Tests for python_ingestion.symbols.normalize_table_name.

These cover the reserved-word and dot-stripping rules that the per-symbol
intraday table names depend on. The Java side has a mirror test in
SymbolNormalizerTest with the same cases.
"""
import pytest

from python_ingestion.symbols import normalize_table_name


def test_plain_symbol_unchanged():
    assert normalize_table_name("AAPL") == "AAPL"
    assert normalize_table_name("MSFT") == "MSFT"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("BRK.B", "BRKB"),
        ("BF.B", "BFB"),
    ],
)
def test_dot_stripped(raw, expected):
    assert normalize_table_name(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("NOW", "NOW1"),
        ("ALL", "ALL1"),
        ("KEYS", "KEYS1"),
        ("KEY", "KEY1"),
    ],
)
def test_reserved_words_suffixed(raw, expected):
    assert normalize_table_name(raw) == expected


def test_reserved_word_only_exact_match():
    # "NOWX" should not be mangled — only exact "NOW" collides with the
    # MySQL reserved word.
    assert normalize_table_name("NOWX") == "NOWX"
