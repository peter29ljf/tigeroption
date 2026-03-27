"""Add is_abnormal and abnormal_reason columns

Revision ID: 003
Revises: 002
Create Date: 2026-03-26
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "option_flows",
        sa.Column("is_abnormal", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "option_flows",
        sa.Column("abnormal_reason", sa.String(64), nullable=True),
    )
    op.create_index("ix_option_flows_is_abnormal", "option_flows", ["is_abnormal"])


def downgrade() -> None:
    op.drop_index("ix_option_flows_is_abnormal", table_name="option_flows")
    op.drop_column("option_flows", "abnormal_reason")
    op.drop_column("option_flows", "is_abnormal")
