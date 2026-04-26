import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Integer, LargeBinary, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RoomImage(Base):
    __tablename__ = "room_images"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    media_type: Mapped[str] = mapped_column(String(64), nullable=False, default="image/jpeg")
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="upload")

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="room_images")

    __table_args__ = (CheckConstraint("byte_size <= 5242880", name="ck_room_images_size_5mb"),)
