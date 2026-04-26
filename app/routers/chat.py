import base64
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response, status
from langchain_core.messages import HumanMessage
from sqlalchemy import select

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.models.message import Message
from app.models.session import DesignSession
from app.schemas.chat import ChatAnalyzeRequest, ChatRequest, ChatResponse, MessageOut
from app.schemas.product import ProductOut
from app.services.image_service import persist_base64
from app.services.llm import get_chat_llm
from app.services.rag_service import run_rag_turn
from app.services.user_profile_service import extract_and_update_profile
from app.utils.dependencies import CurrentUser, DBSession

router = APIRouter(prefix="/chat", tags=["chat"])
settings = get_settings()


async def _owned_session(db, session_id: uuid.UUID, user_id: uuid.UUID) -> DesignSession:
    res = await db.execute(
        select(DesignSession).where(
            DesignSession.id == session_id, DesignSession.user_id == user_id
        )
    )
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    return session


@router.post("/analyze", response_model=ChatResponse)
@limiter.limit(f"{settings.CHAT_RATE_LIMIT_PER_MINUTE}/minute")
async def analyze(
    request: Request,
    response: Response,
    body: ChatAnalyzeRequest,
    user: CurrentUser,
    db: DBSession,
) -> ChatResponse:
    session = await _owned_session(db, body.session_id, user.id)
    image = await persist_base64(
        db,
        owner_id=user.id,
        image_base64=body.image_base64,
        media_type=body.media_type,
        source="upload",
    )
    if not session.room_image_id:
        session.room_image_id = image.id

    prompt = (
        "You are Sumi, an interior designer. Describe this room in 2-3 sentences "
        "(style, lighting, key pieces, empty space). Then ask the user ONE concrete "
        "clarifying question about what they want to add or change. Keep it warm and brief."
    )
    image_b64 = base64.b64encode(image.data).decode()
    vision_message = HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:{image.media_type};base64,{image_b64}"},
            },
        ]
    )
    llm = get_chat_llm(temperature=0.4, max_tokens=512)
    response = await llm.ainvoke([vision_message])
    reply = response.content if isinstance(response.content, str) else str(response.content)

    session.context_summary = reply
    user_msg = Message(session_id=session.id, role="user", content="[room scan attached]", image_id=image.id)
    assistant_msg = Message(session_id=session.id, role="assistant", content=reply)
    db.add_all([user_msg, assistant_msg])
    await db.commit()
    await db.refresh(assistant_msg)

    return ChatResponse(
        message_id=assistant_msg.id,
        content=assistant_msg.content,
        ui_payload=None,
        created_at=assistant_msg.created_at,
    )


@router.post("/", response_model=ChatResponse)
@limiter.limit(f"{settings.CHAT_RATE_LIMIT_PER_MINUTE}/minute")
async def chat(
    request: Request,
    response: Response,
    body: ChatRequest,
    user: CurrentUser,
    db: DBSession,
    background: BackgroundTasks,
) -> ChatResponse:
    session = await _owned_session(db, body.session_id, user.id)

    user_msg = Message(session_id=session.id, role="user", content=body.content)
    db.add(user_msg)
    await db.flush()

    result = await run_rag_turn(
        db,
        session_id=session.id,
        user_message=body.content,
        context_summary=session.context_summary,
        design_profile=user.design_profile or {},
    )

    ui_payload = None
    if result.products:
        ui_payload = {
            "type": "product_carousel",
            "products": [ProductOut.model_validate(p).model_dump(mode="json") for p in result.products],
        }
    elif result.preview_product_ids:
        # Multi-product composite preview (different categories selected together)
        ui_payload = {
            "type": "preview_request",
            "product_ids": [str(pid) for pid in result.preview_product_ids],
        }
    elif result.preview_product_id:
        # Single-product preview
        ui_payload = {"type": "preview_request", "product_id": str(result.preview_product_id)}

    assistant_msg = Message(
        session_id=session.id,
        role="assistant",
        content=result.assistant_text,
        ui_payload=ui_payload,
    )
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)

    background.add_task(extract_and_update_profile, user.id, session.id)

    return ChatResponse(
        message_id=assistant_msg.id,
        content=assistant_msg.content,
        ui_payload=assistant_msg.ui_payload,
        created_at=assistant_msg.created_at,
    )


@router.get("/{session_id}/messages", response_model=list[MessageOut])
async def get_messages(
    session_id: uuid.UUID, user: CurrentUser, db: DBSession
) -> list[Message]:
    await _owned_session(db, session_id, user.id)
    res = await db.execute(
        select(Message).where(Message.session_id == session_id).order_by(Message.created_at.asc())
    )
    return list(res.scalars().all())
