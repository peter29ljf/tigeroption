from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, computed_field

from config.settings import get_settings


class FlowOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    timestamp: datetime
    symbol: str
    strike: Decimal
    expiry: date
    put_call: str
    side: str
    premium: int
    volume: int
    oi: int
    bid_price: Optional[Decimal] = None
    ask_price: Optional[Decimal] = None
    is_sweep: bool = False
    is_dark_pool: bool = False
    score: Optional[int] = None
    direction: Optional[str] = None
    ai_note: Optional[str] = None
    stock_price: Optional[Decimal] = None
    raw_identifier: Optional[str] = None

    @computed_field
    @property
    def premium_usd(self) -> float:
        return self.premium / 100

    @computed_field
    @property
    def premium_cny(self) -> float:
        settings = get_settings()
        return self.premium / 100 * settings.usd_cny_rate


class FlowFilter(BaseModel):
    symbol: Optional[str] = None
    min_premium: Optional[int] = None
    direction: Optional[str] = None
    min_score: Optional[int] = None
    limit: int = 50
    offset: int = 0


class FlowStats(BaseModel):
    total_count: int
    avg_score: Optional[float] = None
    bullish_count: int
    bearish_count: int
