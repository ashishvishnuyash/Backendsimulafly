"""saved items (wishlist) table

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "saved_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("note", sa.String(280)),
        sa.Column(
            "room_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("design_sessions.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "added_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("user_id", "product_id", name="uq_saved_user_product"),
    )
    op.create_index(
        "ix_saved_user_added", "saved_items", ["user_id", "added_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_saved_user_added", table_name="saved_items")
    op.drop_table("saved_items")
