from __future__ import annotations

import logging
from collections import Counter
from typing import Optional

import anthropic
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from services.api.models.database import get_db
from services.api.models.option_flow import OptionFlow
from services.api.schemas.flow import FlowOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/abnormal", tags=["abnormal"])

# Simple symbol → sector mapping for AI context
SECTOR_MAP: dict[str, str] = {
    "NVDA": "半导体", "AMD": "半导体", "INTC": "半导体", "TSM": "半导体",
    "AVGO": "半导体", "MU": "半导体", "QCOM": "半导体", "AMAT": "半导体",
    "AAPL": "科技", "MSFT": "科技", "GOOGL": "科技", "GOOG": "科技",
    "META": "科技", "AMZN": "科技", "NFLX": "科技", "CRM": "科技",
    "TSLA": "电动车/科技", "RIVN": "电动车", "NIO": "电动车", "LCID": "电动车",
    "SPY": "指数ETF", "QQQ": "指数ETF", "IWM": "指数ETF", "DIA": "指数ETF",
    "SOXL": "半导体ETF", "TQQQ": "指数ETF",
    "XOM": "能源", "CVX": "能源", "OXY": "能源", "SLB": "能源",
    "JPM": "金融", "GS": "金融", "BAC": "金融", "MS": "金融", "C": "金融",
    "MRNA": "生物医药", "PFE": "生物医药", "LLY": "生物医药",
    "ABBV": "生物医药", "JNJ": "生物医药", "BIIB": "生物医药",
    "COST": "消费零售", "WMT": "消费零售", "TGT": "消费零售",
}

_AI_SYSTEM = (
    "你是一位专业的美股期权分析师，专注于识别大资金行为规律。"
    "你需要从机构视角分析一批异常大单，找出隐藏的规律和意图。"
    "用简洁专业的中文输出分析报告，条理清晰，重点突出。"
    "末尾必须附上：⚠️ 以上分析仅供参考，不构成任何投资建议。"
)


class ClearResult(BaseModel):
    cleared: int


class AIAnalysisRequest(BaseModel):
    api_key: Optional[str] = None


class AIAnalysisResponse(BaseModel):
    analysis: str


@router.get("", response_model=list[FlowOut])
async def list_abnormal_flows(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[FlowOut]:
    """Return all flows marked as abnormal, ordered by score desc then timestamp desc."""
    stmt = (
        select(OptionFlow)
        .where(OptionFlow.is_abnormal.is_(True))
        .order_by(OptionFlow.score.desc(), OptionFlow.timestamp.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return [FlowOut.model_validate(row) for row in result.scalars().all()]


@router.delete("", response_model=ClearResult)
async def clear_abnormal_flows(
    db: AsyncSession = Depends(get_db),
) -> ClearResult:
    """Unmark all abnormal flows (sets is_abnormal=False). Data is preserved."""
    # Count first
    count_stmt = select(func.count()).where(OptionFlow.is_abnormal.is_(True))
    count = (await db.execute(count_stmt)).scalar() or 0

    await db.execute(
        update(OptionFlow)
        .where(OptionFlow.is_abnormal.is_(True))
        .values(is_abnormal=False)
    )
    await db.commit()
    logger.info("Cleared %d abnormal flow flags", count)
    return ClearResult(cleared=count)


@router.post("/ai-analysis", response_model=AIAnalysisResponse)
async def ai_analysis(
    body: AIAnalysisRequest,
    db: AsyncSession = Depends(get_db),
) -> AIAnalysisResponse:
    """Aggregate all abnormal flows and ask Claude to identify patterns."""
    stmt = (
        select(OptionFlow)
        .where(OptionFlow.is_abnormal.is_(True))
        .order_by(OptionFlow.score.desc())
        .limit(200)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    if not rows:
        return AIAnalysisResponse(analysis="当前暂无异常大单数据，请等待系统采集后再试。")

    # Build aggregated context
    flows = [FlowOut.model_validate(r) for r in rows]
    total = len(flows)
    bullish = sum(1 for f in flows if f.direction == "BULLISH")
    bearish = sum(1 for f in flows if f.direction == "BEARISH")
    sweeps = sum(1 for f in flows if f.is_sweep)
    dark_pools = sum(1 for f in flows if f.is_dark_pool)
    avg_score = round(sum(f.score or 0 for f in flows) / total, 1)
    avg_premium = round(sum(f.premium_usd for f in flows) / total)
    total_premium = round(sum(f.premium_usd for f in flows))

    # Symbol distribution
    symbol_counts = Counter(f.symbol for f in flows)
    top_symbols = symbol_counts.most_common(10)

    # Sector distribution
    sector_counts: Counter = Counter()
    for sym, cnt in symbol_counts.items():
        sector = SECTOR_MAP.get(sym, "其他")
        sector_counts[sector] += cnt

    # Expiry concentration
    expiry_counts = Counter(str(f.expiry) for f in flows)
    top_expiries = expiry_counts.most_common(5)

    # Direction per symbol (top 5 symbols)
    sym_direction: dict[str, dict[str, int]] = {}
    for f in flows:
        if f.symbol not in sym_direction:
            sym_direction[f.symbol] = {"BULLISH": 0, "BEARISH": 0, "NEUTRAL": 0}
        sym_direction[f.symbol][f.direction or "NEUTRAL"] += 1

    # Build prompt
    symbol_lines = "\n".join(
        f"  {sym}（{SECTOR_MAP.get(sym, '其他')}）: {cnt}笔，"
        f"多{sym_direction.get(sym, {}).get('BULLISH', 0)}/空{sym_direction.get(sym, {}).get('BEARISH', 0)}"
        for sym, cnt in top_symbols
    )
    sector_lines = " / ".join(f"{s}:{c}笔" for s, c in sector_counts.most_common())
    expiry_lines = " / ".join(f"{e}({c}笔)" for e, c in top_expiries)

    # Per-flow detail lines (up to 30)
    flow_detail_lines = []
    for f in flows[:30]:
        sp = float(f.stock_price) if f.stock_price else None
        sk = float(f.strike)
        is_call = f.put_call.upper() in ("CALL", "C")
        if sp:
            pct = abs(sp - sk) / sp * 100
            if is_call:
                moneyness = f"价内ITM-{pct:.1f}%" if sp > sk else f"价外OTM+{pct:.1f}%"
            else:
                moneyness = f"价内ITM-{pct:.1f}%" if sp < sk else f"价外OTM+{pct:.1f}%"
            price_str = f"股价${sp:.1f}→行权${sk:.1f} | {moneyness}"
        else:
            price_str = f"行权${sk:.1f} | 股价N/A"

        iv_str = f"{float(f.iv):.1f}%" if f.iv else "N/A"
        vol_oi_str = f"{f.volume / f.oi:.1f}x" if f.oi and f.oi > 0 else "N/A"
        premium_wan = f.premium_usd / 10000
        trade_type = "扫单" if f.is_sweep else ("暗池" if f.is_dark_pool else "普通")
        pc_label = "C" if is_call else "P"
        flow_detail_lines.append(
            f"  {f.symbol} {sk:.0f}{pc_label} 到期{f.expiry} | {price_str} | "
            f"IV:{iv_str} | 溢价${premium_wan:.0f}万 | Vol/OI={vol_oi_str} | "
            f"评分{f.score or 0} | {trade_type} | {f.direction or 'N/A'}"
        )
    flow_detail_block = "\n".join(flow_detail_lines)

    prompt = (
        f"以下是从实时期权大单流中检测到的 {total} 笔异常大单数据汇总：\n\n"
        f"【总体概况】\n"
        f"  总笔数：{total}笔 | 合计溢价：${total_premium:,} | 平均溢价：${avg_premium:,}\n"
        f"  平均评分：{avg_score}/100\n"
        f"  方向：看涨{bullish}笔 / 看跌{bearish}笔（多头占比{bullish/total:.1%}）\n"
        f"  扫单：{sweeps}笔 / 暗池大单：{dark_pools}笔\n\n"
        f"【板块分布】\n  {sector_lines}\n\n"
        f"【标的分布（前10）】\n{symbol_lines}\n\n"
        f"【到期日集中度（前5）】\n  {expiry_lines}\n\n"
        f"【大单明细（最多30笔，格式：标的 行权价C/P 到期日 | 股价→行权 | 价内外 | IV | 溢价 | Vol/OI | 评分 | 类型 | 方向）】\n"
        f"{flow_detail_block}\n\n"
        f"请分析这批异常大单是否存在规律：\n"
        f"1. 板块集中度——是否集中在某一板块或主题？\n"
        f"2. 策略一致性——扫单 vs 暗池大单的比例，反映的交易风格？\n"
        f"3. 方向判断——整体偏多还是偏空？各主要标的方向是否一致？\n"
        f"4. 时间布局——到期日集中在哪个时间窗口？是否有事件驱动（如财报、宏观数据）？\n"
        f"5. 综合结论——这是否像同一批机构资金的协同布局？整体给出大资金意图判断。\n"
        f"6. 期权结构——这些大单整体是价内还是价外？IV 是否偏高（暗示预期大波动）？Vol/OI 高的大单反映了什么？"
    )

    settings = get_settings()
    api_key = body.api_key or settings.anthropic_api_key
    if not api_key:
        return AIAnalysisResponse(analysis="未配置 Anthropic API Key，请在设置中填写或在请求中传入 api_key。")

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=_AI_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        analysis = message.content[0].text
    except Exception:
        logger.exception("AI analysis failed for abnormal flows")
        analysis = "AI 分析暂时不可用，请稍后重试。"

    return AIAnalysisResponse(analysis=analysis)
