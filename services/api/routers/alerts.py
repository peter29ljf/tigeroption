from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from services.api.models.alert_rule import AlertRule
from services.api.models.database import get_db
from services.api.schemas.alert import AlertRuleCreate, AlertRuleOut, AlertRuleUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/alerts", tags=["alerts"])
security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


@router.get("", response_model=list[AlertRuleOut])
async def list_alerts(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[AlertRuleOut]:
    stmt = select(AlertRule).where(AlertRule.user_id == user_id).order_by(AlertRule.created_at.desc())
    result = await db.execute(stmt)
    return [AlertRuleOut.model_validate(row) for row in result.scalars().all()]


@router.post("", response_model=AlertRuleOut, status_code=status.HTTP_201_CREATED)
async def create_alert(
    body: AlertRuleCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> AlertRuleOut:
    rule = AlertRule(user_id=user_id, **body.model_dump())
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return AlertRuleOut.model_validate(rule)


@router.put("/{rule_id}", response_model=AlertRuleOut)
async def update_alert(
    rule_id: int,
    body: AlertRuleUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> AlertRuleOut:
    stmt = select(AlertRule).where(AlertRule.id == rule_id, AlertRule.user_id == user_id)
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)

    await db.flush()
    await db.refresh(rule)
    return AlertRuleOut.model_validate(rule)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    rule_id: int,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    stmt = select(AlertRule).where(AlertRule.id == rule_id, AlertRule.user_id == user_id)
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found")
    await db.delete(rule)
