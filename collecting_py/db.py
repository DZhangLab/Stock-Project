"""Database helpers and table definitions for the collectors."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Dict, Iterable, Iterator, Optional

from sqlalchemy import Column, DateTime, Integer, MetaData, Numeric, String, Table, UniqueConstraint, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.sql import insert
from sqlalchemy.dialects import mysql

from .config import Settings, get_settings
from .utils import normalise_symbol


metadata = MetaData()


class Base(DeclarativeBase):
    metadata = metadata


class DailyQuote(Base):
    """ORM model capturing the fields inserted by the quote collector."""

    __tablename__ = "daily_quotes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(32), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    exchange = Column(String(64), nullable=True)
    currency = Column(String(16), nullable=True)
    datetime = Column(DateTime(timezone=True), nullable=False)
    open = Column(Numeric(18, 6), nullable=True)
    high = Column(Numeric(18, 6), nullable=True)
    low = Column(Numeric(18, 6), nullable=True)
    close = Column(Numeric(18, 6), nullable=True)
    previous_close = Column(Numeric(18, 6), nullable=True)
    change = Column(Numeric(18, 6), nullable=True)
    percent_change = Column(Numeric(18, 6), nullable=True)
    fifty_two_week_high = Column(Numeric(18, 6), nullable=True)
    fifty_two_week_low = Column(Numeric(18, 6), nullable=True)

    __table_args__ = (
        UniqueConstraint("symbol", "datetime", name="uq_daily_quotes_symbol_dt"),
    )


_engine: Optional[Engine] = None
_Session: Optional[sessionmaker] = None
_intraday_tables: Dict[str, Table] = {}


def get_engine(settings: Optional[Settings] = None) -> Engine:
    """Return a lazily created SQLAlchemy engine using *settings*."""

    global _engine
    if _engine is None:
        settings = settings or get_settings()
        _engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
        metadata.create_all(_engine)
    return _engine


def get_session(settings: Optional[Settings] = None) -> Session:
    """Return a SQLAlchemy ORM session bound to the global engine."""

    global _Session
    if _Session is None:
        engine = get_engine(settings)
        _Session = sessionmaker(engine, expire_on_commit=False)
    return _Session()


@contextmanager
def session_scope(settings: Optional[Settings] = None) -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""

    session = get_session(settings)
    try:
        yield session
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise
    finally:
        session.close()


def get_intraday_table(symbol: str) -> Table:
    """Return (creating if necessary) the intraday table for *symbol*."""

    table_name = normalise_symbol(symbol)
    if table_name not in _intraday_tables:
        table = Table(
            table_name,
            metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("timestamp", DateTime(timezone=True), nullable=False, index=True),
            Column("open", Numeric(18, 6), nullable=False),
            Column("high", Numeric(18, 6), nullable=False),
            Column("low", Numeric(18, 6), nullable=False),
            Column("close", Numeric(18, 6), nullable=False),
            Column("volume", Numeric(18, 6), nullable=False),
            UniqueConstraint("timestamp", name=f"uq_{table_name}_timestamp"),
        )
        _intraday_tables[table_name] = table
    return _intraday_tables[table_name]


def ensure_intraday_table(engine: Engine, symbol: str) -> Table:
    """Ensure the intraday table for *symbol* exists in the database."""

    table = get_intraday_table(symbol)
    table.create(bind=engine, checkfirst=True)
    return table


def bulk_upsert_intraday(engine: Engine, table: Table, rows: Iterable[dict]) -> int:
    """Insert or update *rows* in *table*, returning the number of processed rows."""

    rows = list(rows)
    if not rows:
        return 0

    with engine.begin() as connection:
        if connection.dialect.name == "mysql":
            stmt = mysql.insert(table).values(rows)
            update_cols = {
                col.name: stmt.inserted[col.name]
                for col in table.columns
                if col.name not in {"id"}
            }
            stmt = stmt.on_duplicate_key_update(**update_cols)
            connection.execute(stmt)
        else:
            stmt = insert(table).values(rows)
            connection.execute(stmt)
    return len(rows)


def bulk_upsert_quotes(session: Session, rows: Iterable[dict]) -> int:
    """Insert quote rows with ON CONFLICT/duplicate handling."""

    rows = list(rows)
    if not rows:
        return 0

    engine = session.get_bind()
    if engine.dialect.name == "mysql":
        stmt = mysql.insert(DailyQuote.__table__).values(rows)
        update_cols = {
            col.name: stmt.inserted[col.name]
            for col in DailyQuote.__table__.columns
            if col.name not in {"id"}
        }
        stmt = stmt.on_duplicate_key_update(**update_cols)
        session.execute(stmt)
    else:
        stmt = insert(DailyQuote).values(rows)
        session.execute(stmt)
    session.flush()
    return len(rows)

