# Python Data Collection Toolkit

This package reimplements the logic from the original Node.js scripts using
Python.  It introduces structured configuration, SQLAlchemy-based persistence and
APScheduler driven scheduling so the collectors are easier to reason about and
extend.

## Installation

```
python -m venv .venv
source .venv/bin/activate
pip install -r collecting_py/requirements.txt
```

Copy `.env.example` to `.env` and provide your Twelve Data API key as well as a
SQLAlchemy-compatible `DATABASE_URL`.

## Commands

Use the `main.py` module to trigger the collectors:

```
python -m collecting_py.main collect-intraday AAPL MSFT
python -m collecting_py.main collect-quote AAPL MSFT
python -m collecting_py.main collect-history AAPL 2023-01-01 2023-01-31
python -m collecting_py.main run-scheduler
```

Environment variables `INTRADAY_SYMBOLS` and `QUOTE_SYMBOLS` provide default
symbol lists so the commands can run without positional arguments.

