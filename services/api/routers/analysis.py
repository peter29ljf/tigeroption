from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
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

    # Get live price from kline (most recent close); fall back to DB stock_price
    current_price: float | None = None
    try:
        client = get_tiger_client()
        bars = await __import__("asyncio").to_thread(
            client.get_kline, upper_symbol, "day", 1
        )
        if bars:
            current_price = float(bars[-1]["close"])
    except Exception:
        logger.warning("kline price fetch failed for %s, falling back to DB", upper_symbol)
    if not current_price:
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

    # Get live stock price from kline; fall back to DB
    stock_price: float | None = None
    try:
        _client = get_tiger_client()
        _bars = await __import__("asyncio").to_thread(_client.get_kline, upper_symbol, "day", 1)
        if _bars:
            stock_price = float(_bars[-1]["close"])
    except Exception:
        pass
    if not stock_price:
        _price_stmt = (
            select(OptionFlow.stock_price)
            .where(OptionFlow.symbol == upper_symbol, OptionFlow.stock_price.isnot(None))
            .order_by(OptionFlow.timestamp.desc())
            .limit(1)
        )
        _row = (await db.execute(_price_stmt)).scalar()
        stock_price = float(_row) if _row else None

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


class OIStrike(BaseModel):
    strike: float
    call_oi: int
    put_oi: int
    net_oi: int


class OIDistribution(BaseModel):
    symbol: str
    put_call_oi_ratio: float | None
    total_call_oi: int
    total_put_oi: int
    strikes: list[OIStrike]
    top_oi_strikes: list[dict]


@router.get("/{symbol}/oi-distribution", response_model=OIDistribution)
async def oi_distribution(
    symbol: str,
    expiry_count: int = Query(2, ge=1, le=5),
) -> OIDistribution:
    """Return Open Interest distribution per strike from live Tiger option chain.
    Calculates put/call OI ratio as a market sentiment indicator.
    """
    upper_symbol = symbol.upper()
    strikes_map: dict[float, dict] = {}

    try:
        client = get_tiger_client()
        expiries = await __import__("asyncio").to_thread(
            client.get_option_expirations, upper_symbol
        )
        for expiry in expiries[:expiry_count]:
            chain = await __import__("asyncio").to_thread(
                client.get_option_chain, upper_symbol, expiry
            )
            for row in chain:
                strike = float(row.get("strike", 0) or 0)
                if strike == 0:
                    continue
                oi = int(row.get("open_interest", 0) or 0)
                pc = str(row.get("put_call", "") or "").upper()
                if strike not in strikes_map:
                    strikes_map[strike] = {"call_oi": 0, "put_oi": 0}
                if pc in ("CALL", "C"):
                    strikes_map[strike]["call_oi"] += oi
                elif pc in ("PUT", "P"):
                    strikes_map[strike]["put_oi"] += oi
    except Exception:
        logger.exception("Failed to fetch option chain for OI %s", upper_symbol)

    oi_list = []
    total_call_oi = 0
    total_put_oi = 0
    for strike, v in sorted(strikes_map.items()):
        call_oi = v["call_oi"]
        put_oi = v["put_oi"]
        total_call_oi += call_oi
        total_put_oi += put_oi
        oi_list.append(OIStrike(
            strike=strike,
            call_oi=call_oi,
            put_oi=put_oi,
            net_oi=call_oi - put_oi,
        ))

    pc_ratio = round(total_put_oi / total_call_oi, 4) if total_call_oi > 0 else None

    # Top 5 strikes by total OI (institutional concentration zones)
    top_oi = sorted(
        [{"strike": s.strike, "total_oi": s.call_oi + s.put_oi} for s in oi_list],
        key=lambda x: x["total_oi"],
        reverse=True,
    )[:5]

    return OIDistribution(
        symbol=upper_symbol,
        put_call_oi_ratio=pc_ratio,
        total_call_oi=total_call_oi,
        total_put_oi=total_put_oi,
        strikes=oi_list,
        top_oi_strikes=top_oi,
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


# ── AI Comprehensive Analysis ─────────────────────────────────────────────────

class AIInsightRequest(BaseModel):
    api_key: str | None = None  # user-provided key; falls back to server ANTHROPIC_API_KEY


class AIInsightResponse(BaseModel):
    insight: str


_AI_SYSTEM = (
    "你是一位专业的美股期权分析师，擅长结合 Gamma 曝露（GEX）、未平仓量（OI）、"
    "大单流向和市场情绪进行综合判断。用简洁专业的中文输出分析报告。"
    "末尾必须附上：⚠️ 以上分析仅供参考，不构成任何投资建议。"
)


def _itm_otm_label(stock_px: float | None, strike: float, put_call: str) -> str:
    if not stock_px:
        return "N/A"
    pct = abs(stock_px - strike) / stock_px * 100
    is_call = put_call.upper() in ("CALL", "C")
    if is_call:
        return f"价内ITM-{pct:.1f}%" if stock_px > strike else f"价外OTM+{pct:.1f}%"
    else:
        return f"价内ITM-{pct:.1f}%" if stock_px < strike else f"价外OTM+{pct:.1f}%"


def _build_insight_prompt(
    symbol: str,
    price: float | None,
    bullish: int,
    bearish: int,
    avg_score: float | None,
    top_flows: list,
    max_gex_strike: float | None,
    top_call_gex: list[dict],
    pc_ratio: float | None,
    top_oi_strikes: list[dict],
) -> str:
    sentiment = f"{bullish}多 / {bearish}空"
    ratio_str = f"{pc_ratio:.2f}" if pc_ratio is not None else "N/A"
    ratio_note = ""
    if pc_ratio is not None:
        if pc_ratio > 1.5:
            ratio_note = "（偏空）"
        elif pc_ratio < 0.7:
            ratio_note = "（偏多）"
        else:
            ratio_note = "（中性）"

    flows_lines = []
    for f in top_flows[:5]:
        strike = float(f.strike)
        pc = f.put_call
        direction = f.direction or "N/A"
        premium_usd = f.premium / 100
        score = f.score or 0
        side = f.side or "N/A"
        trade_px = float(f.stock_price) if f.stock_price else None
        trade_px_str = f"${trade_px:.2f}" if trade_px else "N/A"
        curr_px_str = f"${price:.2f}" if price else "N/A"
        moneyness_at_trade = _itm_otm_label(trade_px, strike, pc)
        moneyness_now = _itm_otm_label(price, strike, pc)
        iv_str = f"{float(f.iv):.1f}%" if f.iv else "N/A"
        vol_oi_str = f"{f.volume / f.oi:.1f}x" if f.oi and f.oi > 0 else "N/A"
        flows_lines.append(
            f"  {symbol} {strike:.0f}{pc} | {side} | {direction} | "
            f"成交时股价{trade_px_str}({moneyness_at_trade}) | 当前{curr_px_str}({moneyness_now}) | "
            f"IV:{iv_str} | Vol/OI:{vol_oi_str} | 溢价${premium_usd:,.0f} | 评分{score}"
        )

    top_oi_str = " / ".join(
        f"${s['strike']}({s['total_oi']:,})" for s in top_oi_strikes[:5]
    )
    top_gex_str = " / ".join(
        f"${s['strike']}({s['net_gex']:,.0f})" for s in top_call_gex[:3]
    ) if top_call_gex else "N/A"

    price_str = f"${price:.2f}" if price else "N/A"
    score_str = f"{avg_score:.1f}/100" if avg_score else "N/A"
    total_dir = bullish + bearish
    ratio_pct = f"{bullish/total_dir:.1%}" if total_dir > 0 else "N/A"
    flows_block = "\n".join(flows_lines) if flows_lines else "  暂无大单数据"
    max_gex_str = f"${max_gex_strike}" if max_gex_strike else "N/A"

    return (
        f"你是一位美股期权专业分析师。以下是 {symbol} 当前市场数据：\n\n"
        f"【当前价格】{price_str}\n"
        f"【市场情绪】过去7天 {sentiment}（多头占比 {ratio_pct}）\n"
        f"【平均信号评分】{score_str}\n\n"
        f"【GEX Gamma曝露】\n"
        f"- 最大GEX行权价（价格磁铁）：{max_gex_str}\n"
        f"- 正GEX最强前3区（做市商净多Gamma）：{top_gex_str}\n\n"
        f"【未平仓量(OI)分析】\n"
        f"- Put/Call OI 比率：{ratio_str}{ratio_note}\n"
        f"- 机构重仓前5行权价（按总OI排序）：{top_oi_str}\n\n"
        f"【近期大单（Top 5，按溢价排序）】\n"
        f"{flows_block}\n\n"
        f"请基于以上数据进行综合分析，输出以下内容：\n"
        f"1. **整体市场情绪判断**（强多/弱多/中性/弱空/强空）及核心理由\n"
        f"2. **关键支撑/阻力位**（结合GEX磁铁区和OI高度集中区分析）\n"
        f"3. **主要风险点**（需要关注的潜在反转信号）\n"
        f"4. **短期操作建议**（方向性参考，非具体仓位建议）\n"
    )


@router.post("/{symbol}/ai-insight", response_model=AIInsightResponse)
async def ai_insight(
    symbol: str,
    body: AIInsightRequest,
    db: AsyncSession = Depends(get_db),
) -> AIInsightResponse:
    """Aggregate all market data for symbol and run Claude AI comprehensive analysis."""
    upper_symbol = symbol.upper()
    settings = get_settings()

    # Resolve API key
    api_key = (body.api_key or "").strip() or settings.anthropic_api_key
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="请提供 Anthropic API Key（在面板输入框填入，或在服务器配置 ANTHROPIC_API_KEY）",
        )

    # ── 1. Gather data from DB ────────────────────────────────────────────────
    since_7d = datetime.now(timezone.utc) - timedelta(days=7)
    base_filter = [OptionFlow.symbol == upper_symbol, OptionFlow.timestamp >= since_7d]

    bullish = (await db.execute(
        select(func.count()).where(*base_filter, OptionFlow.direction == "BULLISH")
    )).scalar() or 0
    bearish = (await db.execute(
        select(func.count()).where(*base_filter, OptionFlow.direction == "BEARISH")
    )).scalar() or 0
    avg_score_row = (await db.execute(
        select(func.avg(OptionFlow.score)).where(*base_filter)
    )).scalar()
    top_flows_result = await db.execute(
        select(OptionFlow).where(*base_filter).order_by(OptionFlow.premium.desc()).limit(5)
    )
    top_flows = list(top_flows_result.scalars().all())

    # ── 2. Live price ─────────────────────────────────────────────────────────
    price: float | None = None
    try:
        client = get_tiger_client()
        bars = await __import__("asyncio").to_thread(client.get_kline, upper_symbol, "day", 1)
        if bars:
            price = float(bars[-1]["close"])
    except Exception:
        logger.warning("kline failed for %s in ai-insight", upper_symbol)

    # ── 3. GEX & OI from Tiger option chain ───────────────────────────────────
    max_gex_strike: float | None = None
    top_call_gex: list[dict] = []
    pc_ratio: float | None = None
    top_oi_strikes: list[dict] = []

    try:
        expiries = await __import__("asyncio").to_thread(
            client.get_option_expirations, upper_symbol
        )
        sp = price or 1.0
        gex_map: dict[float, dict] = {}
        oi_map: dict[float, dict] = {}

        for expiry in expiries[:2]:
            chain = await __import__("asyncio").to_thread(
                client.get_option_chain, upper_symbol, expiry
            )
            for row in chain:
                strike = float(row.get("strike", 0) or 0)
                if not strike:
                    continue
                delta = float(row.get("delta", 0) or 0)
                oi = int(row.get("open_interest", 0) or 0)
                pc = str(row.get("put_call", "") or "").upper()
                gex_val = abs(delta) * oi * 100 * sp

                if strike not in gex_map:
                    gex_map[strike] = {"call_gex": 0.0, "put_gex": 0.0}
                if strike not in oi_map:
                    oi_map[strike] = {"call_oi": 0, "put_oi": 0}

                if pc in ("CALL", "C"):
                    gex_map[strike]["call_gex"] += gex_val
                    oi_map[strike]["call_oi"] += oi
                elif pc in ("PUT", "P"):
                    gex_map[strike]["put_gex"] += gex_val
                    oi_map[strike]["put_oi"] += oi

        # GEX summary
        gex_list = [
            {"strike": s, "net_gex": v["call_gex"] - v["put_gex"]}
            for s, v in gex_map.items()
        ]
        if gex_list:
            gex_list.sort(key=lambda x: abs(x["net_gex"]), reverse=True)
            max_gex_strike = max(gex_list, key=lambda x: abs(x["net_gex"]))["strike"]
            top_call_gex = [g for g in gex_list if g["net_gex"] > 0][:3]

        # OI summary
        total_call_oi = sum(v["call_oi"] for v in oi_map.values())
        total_put_oi = sum(v["put_oi"] for v in oi_map.values())
        pc_ratio = round(total_put_oi / total_call_oi, 4) if total_call_oi > 0 else None
        oi_sorted = sorted(
            [{"strike": s, "total_oi": v["call_oi"] + v["put_oi"]} for s, v in oi_map.items()],
            key=lambda x: x["total_oi"], reverse=True
        )
        top_oi_strikes = oi_sorted[:5]

    except Exception:
        logger.warning("Tiger option chain fetch failed for ai-insight %s", upper_symbol)

    # ── 4. Build prompt & call Claude ─────────────────────────────────────────
    prompt = _build_insight_prompt(
        symbol=upper_symbol,
        price=price,
        bullish=bullish,
        bearish=bearish,
        avg_score=float(avg_score_row) if avg_score_row is not None else None,
        top_flows=top_flows,
        max_gex_strike=max_gex_strike,
        top_call_gex=top_call_gex,
        pc_ratio=pc_ratio,
        top_oi_strikes=top_oi_strikes,
    )

    try:
        ai_client = anthropic.AsyncAnthropic(api_key=api_key)
        message = await ai_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=_AI_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        insight = message.content[0].text
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=401, detail="API Key 无效，请检查后重试")
    except Exception as exc:
        logger.exception("Claude AI insight failed for %s", upper_symbol)
        raise HTTPException(status_code=502, detail=f"AI 分析调用失败: {exc}")

    return AIInsightResponse(insight=insight)
