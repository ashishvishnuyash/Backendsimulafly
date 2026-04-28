import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NotificationCreate(BaseModel):
    """Internal — used by other services (delivery, price-watcher, etc.) to
    enqueue a notification for a user. Not exposed in the public router."""

    user_id: uuid.UUID
    kind: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=255)
    summary: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    title: str
    summary: str | None
    unread: bool
    payload: dict[str, Any]
    created_at: datetime


class NotificationsList(BaseModel):
    items: list[NotificationOut]
    item_count: int
    unread_count: int
