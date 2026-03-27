from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.models.database import get_db
from services.api.models.option_flow import OptionFlow
from services.api.schemas.flow import FlowFilter, FlowOut, FlowStats

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/flows", tags=["flows"])


@router.get("", response_model=list[FlowOut])
async def list_flows(
    symbol: str | None = Query(None),
    min_premium: int | None = Query(None),
    direction: str | None = Query(None),
    min_score: int | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[FlowOut]:
    filters = FlowFilter(
        symbol=symbol,
        min_premium=min_premium,
        direction=direction,
        min_score=min_score,
        limit=limit,
        offset=offset,
    )
    stmt = select(OptionFlow).order_by(OptionFlow.timestamp.desc())

    if filters.symbol:
        stmt = stmt.where(OptionFlow.symbol == filters.symbol.upper())
    if filters.min_premium is not None:
        stmt = stmt.where(OptionFlow.premium >= filters.min_premium)
    if filters.direction:
        stmt = stmt.where(OptionFlow.direction == filters.direction)
    if filters.min_score is not None:
        stmt = stmt.where(OptionFlow.score >= filters.min_score)

    stmt = stmt.offset(filters.offset).limit(filters.limit)
    result = await db.execute(stmt)
    return [FlowOut.model_validate(row) for row in result.scalars().all()]


@router.get("/latest", response_model=list[FlowOut])
async def latest_flows(db: AsyncSession = Depends(get_db)) -> list[FlowOut]:
    stmt = select(OptionFlow).order_by(OptionFlow.timestamp.desc()).limit(20)
    result = await db.execute(stmt)
    return [FlowOut.model_validate(row) for row in result.scalars().all()]


@router.get("/stats", response_model=FlowStats)
async def flow_stats(db: AsyncSession = Depends(get_db)) -> FlowStats:
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    base = select(OptionFlow).where(OptionFlow.timestamp >= one_hour_ago)

    count_stmt = select(func.count()).select_from(base.subquery())
    avg_stmt = select(func.avg(OptionFlow.score)).where(OptionFlow.timestamp >= one_hour_ago)
    bullish_stmt = select(func.count()).where(
        OptionFlow.timestamp >= one_hour_ago,
        OptionFlow.direction == "BULLISH",
    )
    bearish_stmt = select(func.count()).where(
        OptionFlow.timestamp >= one_hour_ago,
        OptionFlow.direction == "BEARISH",
    )

    total = (await db.execute(count_stmt)).scalar() or 0
    avg_score = (await db.execute(avg_stmt)).scalar()
    bullish = (await db.execute(bullish_stmt)).scalar() or 0
    bearish = (await db.execute(bearish_stmt)).scalar() or 0

    return FlowStats(
        total_count=total,
        avg_score=round(avg_score, 2) if avg_score is not None else None,
        bullish_count=bullish,
        bearish_count=bearish,
    )
