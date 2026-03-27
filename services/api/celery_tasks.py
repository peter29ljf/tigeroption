from __future__ import annotations

import asyncio
import logging

from celery import Celery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
celery_app = Celery("optionflow", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _push_flow_alert_async(flow_id: int) -> None:
    from services.api.models.database import async_session_factory
    from services.api.models.option_flow import OptionFlow
    from services.api.models.alert_rule import AlertRule
    from services.api.wechat_pusher import send_wechat_alert

    async with async_session_factory() as db:
        result = await db.execute(select(OptionFlow).where(OptionFlow.id == flow_id))
        flow = result.scalar_one_or_none()
        if not flow:
            logger.warning("Flow %s not found, skipping alert push", flow_id)
            return

        flow_data = {
            "symbol": flow.symbol,
            "strike": str(flow.strike),
            "expiry": str(flow.expiry),
            "put_call": flow.put_call,
            "direction": flow.direction,
            "premium": flow.premium,
            "score": flow.score,
            "ai_note": flow.ai_note,
        }

        await _check_rules_and_push(db, flow_data)


async def _check_rules_and_push(db: AsyncSession, flow_data: dict) -> None:
    from services.api.models.alert_rule import AlertRule
    from services.api.wechat_pusher import send_wechat_alert

    stmt = select(AlertRule).where(AlertRule.active.is_(True), AlertRule.push_wechat.is_(True))
    result = await db.execute(stmt)
    rules = result.scalars().all()

    for rule in rules:
        if rule.symbol and rule.symbol != flow_data.get("symbol"):
            continue
        if rule.min_score is not None and (flow_data.get("score") or 0) < rule.min_score:
            continue
        if rule.direction and rule.direction != flow_data.get("direction"):
            continue
        if rule.min_premium is not None and (flow_data.get("premium") or 0) < rule.min_premium:
            continue

        try:
            await send_wechat_alert(rule.user_id, flow_data)
        except Exception:
            logger.exception("Failed to push WeChat alert for rule %s", rule.id)


@celery_app.task(name="push_flow_alert")
def push_flow_alert(flow_id: int) -> None:
    _run_async(_push_flow_alert_async(flow_id))


@celery_app.task(name="check_and_push_alerts")
def check_and_push_alerts(flow_data: dict) -> None:
    async def _run():
        from services.api.models.database import async_session_factory

        async with async_session_factory() as db:
            await _check_rules_and_push(db, flow_data)

    _run_async(_run())
