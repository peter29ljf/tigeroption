"""Add iv and backtest return columns

Revision ID: 002
Revises: 001
Create Date: 2026-03-26
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("option_flows", sa.Column("iv", sa.Numeric(8, 4), nullable=True))
    op.add_column("option_flows", sa.Column("d5_return", sa.Numeric(8, 4), nullable=True))
    op.add_column("option_flows", sa.Column("d10_return", sa.Numeric(8, 4), nullable=True))
    op.add_column("option_flows", sa.Column("d30_return", sa.Numeric(8, 4), nullable=True))


def downgrade() -> None:
    op.drop_column("option_flows", "d30_return")
    op.drop_column("option_flows", "d10_return")
    op.drop_column("option_flows", "d5_return")
    op.drop_column("option_flows", "iv")
