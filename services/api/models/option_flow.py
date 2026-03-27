from __future__ import annotations

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
)

from services.api.models.database import Base


class OptionFlow(Base):
    __tablename__ = "option_flows"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    strike = Column(Numeric(10, 2), nullable=False)
    expiry = Column(Date, nullable=False)
    put_call = Column(String(1), nullable=False)
    side = Column(String(10), nullable=False)
    premium = Column(BigInteger, nullable=False)
    volume = Column(Integer, nullable=False)
    oi = Column(Integer, nullable=False)
    bid_price = Column(Numeric(10, 4))
    ask_price = Column(Numeric(10, 4))
    is_sweep = Column(Boolean, default=False)
    is_dark_pool = Column(Boolean, default=False)
    score = Column(SmallInteger)
    direction = Column(String(10))
    ai_note = Column(Text)
    stock_price = Column(Numeric(10, 2))
    raw_identifier = Column(String(64))
    iv = Column(Numeric(8, 4), nullable=True)
    d5_return = Column(Numeric(8, 4), nullable=True)
    d10_return = Column(Numeric(8, 4), nullable=True)
    d30_return = Column(Numeric(8, 4), nullable=True)
    is_abnormal = Column(Boolean, nullable=False, default=False)
    abnormal_reason = Column(String(64), nullable=True)
