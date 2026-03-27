from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.models.database import get_db
from services.api.models.option_flow import OptionFlow
from services.api.schemas.flow import FlowOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["analysis"])


class SymbolAnalysis(BaseModel):
    symbol: str
    flow_count: int
    avg_score: float | None
    sentiment_ratio: float | None
    top_flows: list[FlowOut]


@router.get("/{symbol}", response_model=SymbolAnalysis)
async def analyze_symbol(
    symbol: str,
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
) -> SymbolAnalysis:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    upper_symbol = symbol.upper()

    base_filter = [
        OptionFlow.symbol == upper_symbol,
        OptionFlow.timestamp >= since,
    ]

    count_stmt = select(func.count()).where(*base_filter)
    avg_stmt = select(func.avg(OptionFlow.score)).where(*base_filter)
    bullish_stmt = select(func.count()).where(*base_filter, OptionFlow.direction == "bullish")
    bearish_stmt = select(func.count()).where(*base_filter, OptionFlow.direction == "bearish")
    top_stmt = (
        select(OptionFlow)
        .where(*base_filter)
        .order_by(OptionFlow.premium.desc())
        .limit(10)
    )

    flow_count = (await db.execute(count_stmt)).scalar() or 0
    avg_score = (await db.execute(avg_stmt)).scalar()
    bullish = (await db.execute(bullish_stmt)).scalar() or 0
    bearish = (await db.execute(bearish_stmt)).scalar() or 0
    top_result = await db.execute(top_stmt)
    top_flows = [FlowOut.model_validate(row) for row in top_result.scalars().all()]

    total_directional = bullish + bearish
    sentiment_ratio = round(bullish / total_directional, 4) if total_directional > 0 else None

    return SymbolAnalysis(
        symbol=upper_symbol,
        flow_count=flow_count,
        avg_score=round(avg_score, 2) if avg_score is not None else None,
        sentiment_ratio=sentiment_ratio,
        top_flows=top_flows,
    )
