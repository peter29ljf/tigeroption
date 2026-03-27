from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AlertRuleCreate(BaseModel):
    symbol: Optional[str] = None
    min_score: Optional[int] = None
    direction: Optional[str] = None
    min_premium: Optional[int] = None
    push_wechat: bool = True


class AlertRuleUpdate(BaseModel):
    symbol: Optional[str] = None
    min_score: Optional[int] = None
    direction: Optional[str] = None
    min_premium: Optional[int] = None
    push_wechat: Optional[bool] = None
    active: Optional[bool] = None


class AlertRuleOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    user_id: str
    symbol: Optional[str] = None
    min_score: Optional[int] = None
    direction: Optional[str] = None
    min_premium: Optional[int] = None
    push_wechat: bool
    active: bool
    created_at: datetime
