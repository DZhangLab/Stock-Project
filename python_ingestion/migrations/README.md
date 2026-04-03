# Database Migrations

Standalone scripts that fix schema or data issues in the stock database.
Each migration is idempotent and safe to run multiple times.

## Running a migration

```bash
# Preview what would change (no modifications)
python -m python_ingestion.migrations.001_fix_intraday_precision --dry-run

# Apply the migration
python -m python_ingestion.migrations.001_fix_intraday_precision
```

## Migration log

### 001 — Fix intraday price precision

**Bug:** 27 per-symbol intraday tables (AAPL, MSFT, TSLA, AMZN, etc.) were
created with an older schema that used `INT` columns for price fields.  Every
decimal stock price was silently truncated to a whole number on INSERT
(`$253.14` became `$253`).  These tables also lacked a `UNIQUE KEY` on
`timePoint`, which caused the ingestion system's `ON DUPLICATE KEY UPDATE`
to insert duplicate rows instead of updating existing ones.

**Root cause:** The tables were created manually or by an older version of
the codebase before `db.py:ensure_intraday_table()` was introduced.  The
current `ensure_intraday_table()` correctly uses `DECIMAL(18,4)` and includes
`UNIQUE KEY uq_timepoint`, but `CREATE TABLE IF NOT EXISTS` does not alter
an already-existing table.

**What the migration does:**
1. Converts price columns (`minuteOpen`, `minuteHigh`, `minuteLow`,
   `minuteClose`) from `INT` to `DECIMAL(18,4)`.
2. Converts `minuteVolume` from `INT` to `DOUBLE` where needed.
3. Adds `UNIQUE KEY uq_timepoint (timePoint)` where missing, after
   removing any duplicate rows (keeps the newest row per `timePoint`).

**What the migration does NOT do:**
- It does not restore decimal precision for rows that were already truncated.
  Those integer values are permanently baked into the database.  A data
  re-ingestion is required to replace them with fresh decimal-precision
  values from the API.

**Backfill (manual follow-up):**

After running the migration, re-ingest affected symbols:

```python
from python_ingestion.jobs.intraday import IntradayCollector
c = IntradayCollector()
c.collect_intraday("AAPL")   # repeat for each affected symbol
```

Or run the full ingestion scheduler (`main.py`) and let it cycle through
all symbols automatically.  The `ON DUPLICATE KEY UPDATE` in the insert
SQL will overwrite the old truncated rows with fresh decimal data.

**Self-healing:** The same migration logic now also runs automatically
inside `ensure_intraday_table()` on every call.  This means any future
table that somehow gets created with the wrong schema will be fixed
automatically when the ingestion system next processes that symbol.
