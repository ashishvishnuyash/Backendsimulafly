import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.product import ProductOut


class ChatAnalyzeRequest(BaseModel):
    session_id: uuid.UUID
    image_base64: str = Field(min_length=10)
    media_type: str = Field(default="image/jpeg", max_length=64)


class ChatRequest(BaseModel):
    session_id: uuid.UUID
    content: str = Field(min_length=1, max_length=4000)


class ProductCarouselPayload(BaseModel):
    type: Literal["product_carousel"] = "product_carousel"
    products: list[ProductOut]


class RoomPreviewPayload(BaseModel):
    type: Literal["room_preview"] = "room_preview"
    image_id: uuid.UUID
    product_id: uuid.UUID


UIPayload = ProductCarouselPayload | RoomPreviewPayload


class ChatResponse(BaseModel):
    message_id: uuid.UUID
    content: str
    ui_payload: dict[str, Any] | None = None
    created_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    ui_payload: dict[str, Any] | None
    image_id: uuid.UUID | None
    created_at: datetime
