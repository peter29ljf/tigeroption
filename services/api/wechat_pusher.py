from __future__ import annotations

import logging
import time

import httpx

from config.settings import get_settings

logger = logging.getLogger(__name__)

_access_token: str | None = None
_token_expires_at: float = 0.0

WECHAT_TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
WECHAT_TEMPLATE_URL = "https://api.weixin.qq.com/cgi-bin/message/template/send"


async def _refresh_access_token() -> str:
    global _access_token, _token_expires_at

    if _access_token and time.time() < _token_expires_at:
        return _access_token

    settings = get_settings()
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(WECHAT_TOKEN_URL, params={
            "grant_type": "client_credential",
            "appid": settings.wechat_app_id,
            "secret": settings.wechat_app_secret,
        })
        resp.raise_for_status()
        data = resp.json()

    if "access_token" not in data:
        logger.error("Failed to get WeChat access_token: %s", data)
        raise RuntimeError(f"WeChat token error: {data.get('errmsg', 'unknown')}")

    _access_token = data["access_token"]
    _token_expires_at = time.time() + data.get("expires_in", 7200) - 300
    logger.info("WeChat access_token refreshed, expires_in=%s", data.get("expires_in"))
    return _access_token


async def send_wechat_alert(openid: str, flow_data: dict) -> dict:
    token = await _refresh_access_token()
    settings = get_settings()

    premium_usd = flow_data.get("premium", 0) / 100
    premium_cny = premium_usd * settings.usd_cny_rate

    message = {
        "touser": openid,
        "template_id": settings.wechat_template_id,
        "data": {
            "first": {"value": f"🚨 期权大单提醒 - {flow_data.get('symbol', 'N/A')}"},
            "keyword1": {"value": flow_data.get("symbol", "N/A")},
            "keyword2": {"value": flow_data.get("direction", "N/A")},
            "keyword3": {"value": f"${premium_usd:,.0f} (¥{premium_cny:,.0f})"},
            "keyword4": {"value": str(flow_data.get("score", "N/A"))},
            "keyword5": {"value": flow_data.get("ai_note", "")[:200]},
            "remark": {
                "value": f"{'CALL' if flow_data.get('put_call') == 'C' else 'PUT'} "
                         f"{flow_data.get('strike')} @ {flow_data.get('expiry')}"
            },
        },
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            WECHAT_TEMPLATE_URL,
            params={"access_token": token},
            json=message,
        )
        resp.raise_for_status()
        result = resp.json()

    if result.get("errcode") != 0:
        logger.error("WeChat send failed: %s", result)
    else:
        logger.info("WeChat alert sent to %s for %s", openid, flow_data.get("symbol"))

    return result
