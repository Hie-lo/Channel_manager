"""add per-platform channel phone numbers

Revision ID: 20260903_phone
Revises:
"""

from alembic import op
import sqlalchemy as sa


revision = "20260903_phone"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("channels", sa.Column("phone_telegram", sa.String(length=30), nullable=True))
    op.add_column("channels", sa.Column("phone_bale", sa.String(length=30), nullable=True))
    op.add_column("channels", sa.Column("phone_eitaa", sa.String(length=30), nullable=True))


def downgrade() -> None:
    op.drop_column("channels", "phone_eitaa")
    op.drop_column("channels", "phone_bale")
    op.drop_column("channels", "phone_telegram")