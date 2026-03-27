from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config.settings import get_settings

logger = logging.getLogger(__name__)

_engine = None
_session_factory = None

COLUMN_MAP = {
    "timestamp": "timestamp",
    "symbol": "symbol",
    "strike": "strike",
    "expiry": "expiry",
    "put_call": "put_call",
    "side": "side",
    "premium": "premium",
    "volume": "volume",
    "oi": "oi",
    "bid_price": "bid_price",
    "ask_price": "ask_price",
    "is_sweep": "is_sweep",
    "is_dark_pool": "is_dark_pool",
    "score": "score",
    "direction": "direction",
    "ai_note": "ai_note",
    "stock_price": "stock_price",
    "raw_identifier": "raw_identifier",
    "iv": "iv",
    "is_abnormal": "is_abnormal",
    "abnormal_reason": "abnormal_reason",
}


class Base(DeclarativeBase):
    pass


class OptionFlow(Base):
    __tablename__ = "option_flows"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, primary_key=True)
    symbol = Column(String(10), nullable=False)
    strike = Column(Numeric(10, 2))
    expiry = Column(Date)
    put_call = Column(String(1))
    side = Column(String(10))
    premium = Column(BigInteger)
    volume = Column(Integer)
    oi = Column(Integer)
    bid_price = Column(Numeric(10, 4))
    ask_price = Column(Numeric(10, 4))
    is_sweep = Column(Boolean, default=False)
    is_dark_pool = Column(Boolean, default=False)
    score = Column(SmallInteger)
    direction = Column(String(10))
    ai_note = Column(Text)
    stock_price = Column(Numeric(10, 2))
    raw_identifier = Column(String(64))
    iv = Column(Numeric(8, 4))
    d5_return = Column(Numeric(8, 4))
    d10_return = Column(Numeric(8, 4))
    d30_return = Column(Numeric(8, 4))
    is_abnormal = Column(Boolean, default=False)
    abnormal_reason = Column(String(64))


def _get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, pool_size=10, max_overflow=20)
    return _engine


def _get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(_get_engine(), class_=AsyncSession, expire_on_commit=False)
    return _session_factory


def _flow_to_row(flow: dict) -> dict:
    row = {}
    for src_key, col_name in COLUMN_MAP.items():
        if src_key in flow:
            row[col_name] = flow[src_key]
    if "timestamp" not in row:
        row["timestamp"] = datetime.utcnow()
    return row


async def write_flow(flow: dict) -> None:
    session_factory = _get_session_factory()
    row = _flow_to_row(flow)
    cols = ", ".join(row.keys())
    placeholders = ", ".join(f":{k}" for k in row.keys())
    stmt = text(f"INSERT INTO option_flows ({cols}) VALUES ({placeholders})")

    async with session_factory() as session:
        async with session.begin():
            await session.execute(stmt, row)


async def write_flows_batch(flows: list[dict]) -> None:
    if not flows:
        return
    session_factory = _get_session_factory()
    rows = [_flow_to_row(f) for f in flows]
    cols = ", ".join(rows[0].keys())
    placeholders = ", ".join(f":{k}" for k in rows[0].keys())
    stmt = text(f"INSERT INTO option_flows ({cols}) VALUES ({placeholders})")

    async with session_factory() as session:
        async with session.begin():
            await session.execute(stmt, rows)
