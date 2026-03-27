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
from services.collector.tiger_client import get_tiger_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["analysis"])


class SymbolAnalysis(BaseModel):
    symbol: str
    flow_count: int
    avg_score: float | None
    sentiment_ratio: float | None
    bullish_count: int
    bearish_count: int
    current_price: float | None
    top_flows: list[FlowOut]


class CandleBar(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class ChainSnapshotRow(BaseModel):
    strike: float
    expiry: str
    call_volume: int
    put_volume: int
    call_premium: int
    put_premium: int


class ChainSnapshot(BaseModel):
    symbol: str
    rows: list[ChainSnapshotRow]


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
    bullish_stmt = select(func.count()).where(*base_filter, OptionFlow.direction == "BULLISH")
    bearish_stmt = select(func.count()).where(*base_filter, OptionFlow.direction == "BEARISH")
    top_stmt = (
        select(OptionFlow)
        .where(*base_filter)
        .order_by(OptionFlow.premium.desc())
        .limit(10)
    )
    price_stmt = (
        select(OptionFlow.stock_price)
        .where(OptionFlow.symbol == upper_symbol, OptionFlow.stock_price.isnot(None))
        .order_by(OptionFlow.timestamp.desc())
        .limit(1)
    )

    flow_count = (await db.execute(count_stmt)).scalar() or 0
    avg_score = (await db.execute(avg_stmt)).scalar()
    bullish = (await db.execute(bullish_stmt)).scalar() or 0
    bearish = (await db.execute(bearish_stmt)).scalar() or 0
    top_result = await db.execute(top_stmt)
    top_flows = [FlowOut.model_validate(row) for row in top_result.scalars().all()]
    current_price_row = (await db.execute(price_stmt)).scalar()
    current_price = float(current_price_row) if current_price_row is not None else None

    total_directional = bullish + bearish
    sentiment_ratio = round(bullish / total_directional, 4) if total_directional > 0 else None

    return SymbolAnalysis(
        symbol=upper_symbol,
        flow_count=flow_count,
        avg_score=round(avg_score, 2) if avg_score is not None else None,
        sentiment_ratio=sentiment_ratio,
        bullish_count=bullish,
        bearish_count=bearish,
        current_price=current_price,
        top_flows=top_flows,
    )


@router.get("/{symbol}/prices", response_model=list[CandleBar])
async def symbol_prices(
    symbol: str,
    days: int = Query(60, ge=5, le=365),
) -> list[CandleBar]:
    """Return OHLCV daily bars from Tiger API for charting."""
    try:
        client = get_tiger_client()
        bars = await __import__("asyncio").to_thread(
            client.get_kline, symbol.upper(), "day", days
        )
        return [CandleBar(**b) for b in bars]
    except Exception:
        logger.exception("Failed to fetch kline for %s", symbol)
        return []


class GEXStrike(BaseModel):
    strike: float
    call_gex: float
    put_gex: float
    net_gex: float


class GEXData(BaseModel):
    symbol: str
    strikes: list[GEXStrike]
    max_gex_strike: float | None
    stock_price: float | None


@router.get("/{symbol}/gex", response_model=GEXData)
async def gamma_exposure(
    symbol: str,
    db: AsyncSession = Depends(get_db),
) -> GEXData:
    """Calculate Gamma Exposure (GEX) per strike from option chain data.
    GEX = delta × OI × 100 × stock_price  (Call positive, Put negative)
    Since we don't store delta in flows, we fetch live option chain from Tiger.
    """
    upper_symbol = symbol.upper()

    # Get latest stock price from DB
    price_stmt = (
        select(OptionFlow.stock_price)
        .where(OptionFlow.symbol == upper_symbol, OptionFlow.stock_price.isnot(None))
        .order_by(OptionFlow.timestamp.desc())
        .limit(1)
    )
    stock_price_row = (await db.execute(price_stmt)).scalar()
    stock_price = float(stock_price_row) if stock_price_row else None

    strikes_map: dict[float, dict] = {}

    try:
        client = get_tiger_client()
        expiries = await __import__("asyncio").to_thread(
            client.get_option_expirations, upper_symbol
        )
        # Use nearest 2 expirations only (rate-limit safe)
        for expiry in expiries[:2]:
            chain = await __import__("asyncio").to_thread(
                client.get_option_chain, upper_symbol, expiry
            )
            sp = stock_price or 1.0
            for row in chain:
                strike = float(row.get("strike", 0) or 0)
                if strike == 0:
                    continue
                delta = float(row.get("delta", 0) or 0)
                oi = int(row.get("open_interest", 0) or 0)
                pc = str(row.get("put_call", "") or "").upper()
                gex = abs(delta) * oi * 100 * sp
                if strike not in strikes_map:
                    strikes_map[strike] = {"call_gex": 0.0, "put_gex": 0.0}
                if pc in ("CALL", "C"):
                    strikes_map[strike]["call_gex"] += gex
                elif pc in ("PUT", "P"):
                    strikes_map[strike]["put_gex"] += gex
    except Exception:
        logger.exception("Failed to fetch option chain for GEX %s", upper_symbol)

    gex_list = []
    for strike, v in sorted(strikes_map.items()):
        net = v["call_gex"] - v["put_gex"]
        gex_list.append(GEXStrike(
            strike=strike,
            call_gex=round(v["call_gex"], 0),
            put_gex=round(v["put_gex"], 0),
            net_gex=round(net, 0),
        ))

    max_strike = None
    if gex_list:
        max_strike = max(gex_list, key=lambda x: abs(x.net_gex)).strike

    return GEXData(
        symbol=upper_symbol,
        strikes=gex_list,
        max_gex_strike=max_strike,
        stock_price=stock_price,
    )


@router.get("/{symbol}/chain-snapshot", response_model=ChainSnapshot)
async def chain_snapshot(
    symbol: str,
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
) -> ChainSnapshot:
    """Aggregate option chain volume by (strike, expiry, put_call) from recent flows."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    upper_symbol = symbol.upper()

    stmt = select(
        OptionFlow.strike,
        OptionFlow.expiry,
        OptionFlow.put_call,
        func.sum(OptionFlow.volume).label("total_volume"),
        func.sum(OptionFlow.premium).label("total_premium"),
    ).where(
        OptionFlow.symbol == upper_symbol,
        OptionFlow.timestamp >= since,
    ).group_by(
        OptionFlow.strike, OptionFlow.expiry, OptionFlow.put_call
    ).order_by(OptionFlow.strike)

    result = await db.execute(stmt)
    rows_raw = result.all()

    # Group by (strike, expiry) combining CALL and PUT
    grouped: dict[tuple, dict] = {}
    for row in rows_raw:
        key = (float(row.strike), str(row.expiry))
        if key not in grouped:
            grouped[key] = {"strike": float(row.strike), "expiry": str(row.expiry),
                            "call_volume": 0, "put_volume": 0,
                            "call_premium": 0, "put_premium": 0}
        pc = (row.put_call or "").upper()
        if pc in ("C", "CALL"):
            grouped[key]["call_volume"] += int(row.total_volume or 0)
            grouped[key]["call_premium"] += int(row.total_premium or 0)
        elif pc in ("P", "PUT"):
            grouped[key]["put_volume"] += int(row.total_volume or 0)
            grouped[key]["put_premium"] += int(row.total_premium or 0)

    rows = [ChainSnapshotRow(**v) for v in grouped.values()]
    return ChainSnapshot(symbol=upper_symbol, rows=rows)
