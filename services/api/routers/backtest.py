from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from services.api.models.database import get_db
from services.api.models.option_flow import OptionFlow
from services.api.schemas.flow import FlowOut
from services.collector.tiger_client import get_tiger_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/backtest", tags=["backtest"])


class BacktestReturns(BaseModel):
    d5: float | None
    d10: float | None
    d30: float | None


class BacktestResult(BaseModel):
    flow: FlowOut
    price_at_signal: float | None
    bars: list[dict]      # [{time, close}]
    returns: BacktestReturns


class SignalStats(BaseModel):
    total: int
    d5_win_rate: Optional[float]
    d10_win_rate: Optional[float]
    d30_win_rate: Optional[float]
    d5_avg_return: Optional[float]
    d10_avg_return: Optional[float]
    d30_avg_return: Optional[float]


def _nth_close(bars: list[dict], n: int) -> float | None:
    """Return close price of the n-th bar (0-indexed)."""
    if n < len(bars):
        return bars[n]["close"]
    if bars:
        return bars[-1]["close"]
    return None


# IMPORTANT: /stats must be declared before /{flow_id} to avoid route conflict
@router.get("/stats", response_model=SignalStats)
async def backtest_stats(
    direction: Optional[str] = None,
    min_score: int = 60,
    symbol: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> SignalStats:
    """Aggregate win-rate stats across signals that have been backtested."""
    stmt = select(OptionFlow).where(OptionFlow.d5_return.is_not(None))
    if direction:
        stmt = stmt.where(OptionFlow.direction == direction.upper())
    if min_score:
        stmt = stmt.where(OptionFlow.score >= min_score)
    if symbol:
        stmt = stmt.where(OptionFlow.symbol == symbol.upper())

    result = await db.execute(stmt)
    rows = result.scalars().all()

    if not rows:
        return SignalStats(
            total=0,
            d5_win_rate=None, d10_win_rate=None, d30_win_rate=None,
            d5_avg_return=None, d10_avg_return=None, d30_avg_return=None,
        )

    def win_rate(values: list[float]) -> float | None:
        if not values:
            return None
        return round(sum(1 for v in values if v > 0) / len(values) * 100, 1)

    def avg_return(values: list[float]) -> float | None:
        if not values:
            return None
        return round(sum(values) / len(values), 2)

    d5s = [float(r.d5_return) for r in rows if r.d5_return is not None]
    d10s = [float(r.d10_return) for r in rows if r.d10_return is not None]
    d30s = [float(r.d30_return) for r in rows if r.d30_return is not None]

    return SignalStats(
        total=len(rows),
        d5_win_rate=win_rate(d5s),
        d10_win_rate=win_rate(d10s),
        d30_win_rate=win_rate(d30s),
        d5_avg_return=avg_return(d5s),
        d10_avg_return=avg_return(d10s),
        d30_avg_return=avg_return(d30s),
    )


@router.get("/{flow_id}", response_model=BacktestResult)
async def backtest_flow(
    flow_id: int,
    db: AsyncSession = Depends(get_db),
) -> BacktestResult:
    stmt = select(OptionFlow).where(OptionFlow.id == flow_id)
    result = await db.execute(stmt)
    flow_row = result.scalars().first()
    if not flow_row:
        raise HTTPException(status_code=404, detail="Flow not found")

    flow_out = FlowOut.model_validate(flow_row)
    symbol = flow_out.symbol
    signal_date = flow_out.timestamp.strftime("%Y-%m-%d") if flow_out.timestamp else None

    bars: list[dict] = []
    price_at_signal: float | None = float(flow_out.stock_price) if flow_out.stock_price else None

    try:
        client = get_tiger_client()
        raw_bars = await asyncio.to_thread(client.get_kline, symbol, "day", 90)
        # Filter to bars on/after signal date
        if signal_date and raw_bars:
            bars = [b for b in raw_bars if b["time"] >= signal_date]
            if bars and price_at_signal is None:
                price_at_signal = bars[0]["close"]
    except Exception:
        logger.exception("Failed to fetch kline for backtest %s", symbol)

    d5 = d10 = d30 = None
    if price_at_signal and price_at_signal > 0 and bars:
        def pct(close: float | None) -> float | None:
            if close is None:
                return None
            return round((close - price_at_signal) / price_at_signal * 100, 2)  # type: ignore[operator]

        d5 = pct(_nth_close(bars, 5))
        d10 = pct(_nth_close(bars, 10))
        d30 = pct(_nth_close(bars, 30))

    # Cache returns back to DB for win-rate statistics
    if d5 is not None or d10 is not None or d30 is not None:
        try:
            await db.execute(
                update(OptionFlow)
                .where(OptionFlow.id == flow_id)
                .values(d5_return=d5, d10_return=d10, d30_return=d30)
            )
            await db.commit()
        except Exception:
            logger.exception("Failed to cache returns for flow %s", flow_id)

    # Return only first 35 bars to keep response small
    return BacktestResult(
        flow=flow_out,
        price_at_signal=price_at_signal,
        bars=bars[:35],
        returns=BacktestReturns(d5=d5, d10=d10, d30=d30),
    )
