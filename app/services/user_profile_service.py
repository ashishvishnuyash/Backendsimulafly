from __future__ import annotations

import uuid
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.models.message import Message
from app.models.user import User
from app.services.llm import get_chat_llm

log = get_logger(__name__)

PROFILE_EXTRACT_PROMPT = """Extract the user's furniture and interior design preferences
from the recent conversation. Return only fields you can clearly justify from the text.
Empty lists are fine. Never guess."""

LIST_FIELDS = {"styles", "dislikes", "materials", "room_types"}
SCALAR_FIELDS = {"budget_tier", "notes"}


class DesignProfileExtract(BaseModel):
    styles: list[str] = Field(default_factory=list)
    dislikes: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    room_types: list[str] = Field(default_factory=list)
    budget_tier: str | None = None
    notes: str | None = None


async def extract_and_update_profile(user_id: uuid.UUID, session_id: uuid.UUID) -> None:
    """Background task — non-blocking, runs after chat response is returned."""
    try:
        async with SessionLocal() as db:
            history = await _load_recent_messages(db, session_id)
            if len(history) < 2:
                return
            extracted = await _call_extractor(history)
            if not extracted:
                return
            await _merge_into_user(db, user_id, extracted)
            await db.commit()
    except Exception as e:
        log.exception("profile_update_failed", user_id=str(user_id), error=str(e))


async def _load_recent_messages(db: AsyncSession, session_id: uuid.UUID) -> list[Message]:
    res = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(6)
    )
    return list(reversed(res.scalars().all()))


async def _call_extractor(history: list[Message]) -> dict[str, Any] | None:
    transcript = "\n".join(f"{m.role}: {m.content}" for m in history)
    llm = get_chat_llm(temperature=0.0, max_tokens=400).with_structured_output(DesignProfileExtract)
    try:
        result: DesignProfileExtract = await llm.ainvoke(
            [
                SystemMessage(content=PROFILE_EXTRACT_PROMPT),
                HumanMessage(content=transcript),
            ]
        )
        return result.model_dump()
    except Exception as e:
        log.warning("profile_extractor_failed", error=str(e))
        return None


async def _merge_into_user(db: AsyncSession, user_id: uuid.UUID, extracted: dict[str, Any]) -> None:
    user = await db.get(User, user_id)
    if not user:
        return
    current = dict(user.design_profile or {})
    for key in LIST_FIELDS:
        incoming = extracted.get(key) or []
        existing = current.get(key) or []
        if isinstance(incoming, list) and isinstance(existing, list):
            merged = list({str(v).strip().lower() for v in existing + incoming if v})
            current[key] = sorted(merged)
    for key in SCALAR_FIELDS:
        if extracted.get(key):
            current[key] = extracted[key]
    user.design_profile = current
