"""
Analytics package: pure compute helpers for derived market data.

Modules in this package never call external APIs and never write to the
database directly.  They are imported by jobs in python_ingestion/jobs/
which own the I/O.
"""
