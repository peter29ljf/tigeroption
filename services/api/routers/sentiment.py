from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from services.api.models.database import get_db
from services.api.models.option_flow import OptionFlow
from services.api.routers.watchlist import get_dynamic_watchlist

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/market", tags=["market"])


class SymbolSentiment(BaseModel):
    symbol: str
    bullish_count: int
    bearish_count: int
    ratio: float | None


class MarketSentiment(BaseModel):
    total_bullish: int
    total_bearish: int
    overall_ratio: float | None
    symbols: list[SymbolSentiment]


@router.get("/sentiment", response_model=MarketSentiment)
async def market_sentiment(
    request: Request,
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
) -> MarketSentiment:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    watchlist = await get_dynamic_watchlist(request.app.state.redis)

    symbols: list[SymbolSentiment] = []
    total_bullish = 0
    total_bearish = 0

    for sym in watchlist:
        base_filter = [
            OptionFlow.symbol == sym,
            OptionFlow.timestamp >= since,
        ]
        bullish = (
            await db.execute(
                select(func.count()).where(*base_filter, OptionFlow.direction == "BULLISH")
            )
        ).scalar() or 0
        bearish = (
            await db.execute(
                select(func.count()).where(*base_filter, OptionFlow.direction == "BEARISH")
            )
        ).scalar() or 0

        total_directional = bullish + bearish
        ratio = round(bullish / total_directional, 4) if total_directional > 0 else None

        symbols.append(SymbolSentiment(
            symbol=sym,
            bullish_count=bullish,
            bearish_count=bearish,
            ratio=ratio,
        ))
        total_bullish += bullish
        total_bearish += bearish

    grand_total = total_bullish + total_bearish
    overall_ratio = round(total_bullish / grand_total, 4) if grand_total > 0 else None

    return MarketSentiment(
        total_bullish=total_bullish,
        total_bearish=total_bearish,
        overall_ratio=overall_ratio,
        symbols=symbols,
    )
