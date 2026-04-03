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

After running the migration, re-ingest affected symbols using the
dedicated backfill script:

```bash
# Scan for tables that still have integer-only prices
python -m python_ingestion.maintenance.backfill_intraday_precision --scan-only

# Preview what would be backfilled (no API calls or writes)
python -m python_ingestion.maintenance.backfill_intraday_precision --dry-run

# Backfill all affected symbols (last 10 days by default)
python -m python_ingestion.maintenance.backfill_intraday_precision

# Backfill specific symbols only
python -m python_ingestion.maintenance.backfill_intraday_precision --symbol MSFT --symbol GOOGL
```

The script auto-detects which tables still contain truncated integer data,
fetches fresh minute bars from the API, and upserts them via
`ON DUPLICATE KEY UPDATE`.

**Self-healing:** The same migration logic now also runs automatically
inside `ensure_intraday_table()` on every call.  This means any future
table that somehow gets created with the wrong schema will be fixed
automatically when the ingestion system next processes that symbol.

### 002 — Fix daily quote duplicates

**Bug:** The `everydayAfterClose` table used a plain `INSERT` with no
unique constraint on `(symbol, datetime)`.  Every scheduler cycle that
processed the same symbol on the same day created a duplicate row.
As of this migration, 309 duplicate rows existed across 258 groups.

**Root cause:** The quote collector (`quotes.py`) was designed as a
real-time ticker (runs every 9 seconds) but its output table had no
deduplication mechanism.

**What the migration does:**
1. Removes duplicate rows, keeping the newest (highest `id`) per
   `(symbol, datetime)` group.
2. Adds `UNIQUE KEY uq_symbol_datetime (symbol, datetime)` to prevent
   future duplicates.

**Schema tradeoff:** The ideal semantic key would be `(symbol, trade_date)`
on a proper `DATE` column.  The current `datetime` column is `VARCHAR(50)`
storing ISO date strings like `"2025-11-10"`.  Since these values are
consistently formatted and lexicographically sortable, the `UNIQUE KEY`
on the existing columns is safe and sufficient.  A future migration can
introduce a dedicated `daily_bars` table with a `DATE` column if needed.

**Companion change:** The `INSERT` in `quotes.py` was converted to
`INSERT ... ON DUPLICATE KEY UPDATE` so that the scheduler is now
idempotent — re-runs update existing rows instead of creating duplicates.
