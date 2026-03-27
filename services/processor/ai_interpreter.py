from __future__ import annotations

import logging

import anthropic

from config.settings import get_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "你是美股期权分析助手。根据以下期权大单数据，用简洁中文给出方向判断和分析。"
    "输出格式：{symbol} | {合约描述} | 到期日 | 评分 | 方向 | 分析。"
    "末尾必须加上：⚠️仅供参考，不构成投资建议"
)


def _build_user_message(flow: dict) -> str:
    premium_usd = int(flow.get("premium", 0)) / 100
    return (
        f"Symbol: {flow.get('symbol')}\n"
        f"Strike: {flow.get('strike')}\n"
        f"Expiry: {flow.get('expiry')}\n"
        f"Put/Call: {flow.get('put_call')}\n"
        f"Side: {flow.get('side')}\n"
        f"Premium: ${premium_usd:,.0f}\n"
        f"Volume: {flow.get('volume')}\n"
        f"OI: {flow.get('oi')}\n"
        f"Is Sweep: {flow.get('is_sweep', False)}\n"
        f"Score: {flow.get('score')}\n"
        f"Direction: {flow.get('direction')}\n"
        f"Stock Price: {flow.get('stock_price')}\n"
        f"DTE: {flow.get('dte')}"
    )


async def interpret(flow: dict) -> str:
    settings = get_settings()
    if not settings.anthropic_api_key:
        logger.warning("Anthropic API key not configured, skipping AI interpretation")
        return ""

    try:
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        message = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_message(flow)}],
        )
        return message.content[0].text
    except Exception:
        logger.exception("AI interpretation failed for %s", flow.get("symbol"))
        return ""
