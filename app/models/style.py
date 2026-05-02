import uuid
from datetime import datetime

from sqlalchemy import Boolean, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Style(Base):
    """Editorial design-style template.

    Admins add new styles via a protected endpoint or the JSON seed script.
    Slugs are stable client-facing identifiers (used in URLs);
    `image_filename` is relative to the `/static/styles/` mount.
    """

    __tablename__ = "styles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(
        String(96), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    vibe: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    image_filename: Mapped[str | None] = mapped_column(String(255))
    trending: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    # Lower numbers sort first within a category.
    display_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("slug", name="uq_styles_slug"),)
