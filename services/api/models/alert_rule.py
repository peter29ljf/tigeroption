from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String, func

from services.api.models.database import Base


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)
    symbol = Column(String(10))
    min_score = Column(Integer)
    direction = Column(String(10))
    min_premium = Column(BigInteger)
    push_wechat = Column(Boolean, default=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
