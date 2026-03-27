"""Initial schema: option_flows and alert_rules

Revision ID: 001
Revises:
Create Date: 2026-03-26
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "option_flows",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(10), nullable=False),
        sa.Column("strike", sa.Numeric(10, 2), nullable=False),
        sa.Column("expiry", sa.Date(), nullable=False),
        sa.Column("put_call", sa.String(1), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("premium", sa.BigInteger(), nullable=False),
        sa.Column("volume", sa.Integer(), nullable=False),
        sa.Column("oi", sa.Integer(), nullable=False),
        sa.Column("bid_price", sa.Numeric(10, 4), nullable=True),
        sa.Column("ask_price", sa.Numeric(10, 4), nullable=True),
        sa.Column("is_sweep", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("is_dark_pool", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("score", sa.SmallInteger(), nullable=True),
        sa.Column("direction", sa.String(10), nullable=True),
        sa.Column("ai_note", sa.Text(), nullable=True),
        sa.Column("stock_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("raw_identifier", sa.String(64), nullable=True),
        sa.PrimaryKeyConstraint("id", "timestamp"),
    )
    op.create_index("ix_option_flows_symbol", "option_flows", ["symbol"])
    op.create_index("ix_option_flows_symbol_timestamp", "option_flows", ["symbol", sa.text("timestamp DESC")])
    op.create_index("ix_option_flows_score_timestamp", "option_flows", [sa.text("score DESC"), sa.text("timestamp DESC")])

    op.create_table(
        "alert_rules",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("symbol", sa.String(10), nullable=True),
        sa.Column("min_score", sa.Integer(), nullable=True),
        sa.Column("direction", sa.String(10), nullable=True),
        sa.Column("min_premium", sa.BigInteger(), nullable=True),
        sa.Column("push_wechat", sa.Boolean(), server_default=sa.text("true"), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_rules_user_id", "alert_rules", ["user_id"])


def downgrade() -> None:
    op.drop_table("alert_rules")
    op.drop_index("ix_option_flows_score_timestamp", "option_flows")
    op.drop_index("ix_option_flows_symbol_timestamp", "option_flows")
    op.drop_index("ix_option_flows_symbol", "option_flows")
    op.drop_table("option_flows")
