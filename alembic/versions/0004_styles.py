"""editorial style catalog table

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "styles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(96), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("category", sa.String(80), nullable=False, index=True),
        sa.Column("vibe", sa.String(512), nullable=False, server_default=""),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("image_filename", sa.String(255)),
        sa.Column(
            "trending",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "display_order",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("slug", name="uq_styles_slug"),
    )
    op.create_index(
        "ix_styles_category_order",
        "styles",
        ["category", "display_order"],
    )


def downgrade() -> None:
    op.drop_index("ix_styles_category_order", table_name="styles")
    op.drop_table("styles")
