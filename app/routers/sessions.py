import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.models.session import DesignSession
from app.schemas.session import SessionCreate, SessionOut, SessionUpdate
from app.utils.dependencies import CurrentUser, DBSession

router = APIRouter(prefix="/sessions", tags=["sessions"])


async def _get_owned(db, session_id: uuid.UUID, user_id: uuid.UUID) -> DesignSession:
    res = await db.execute(
        select(DesignSession).where(
            DesignSession.id == session_id, DesignSession.user_id == user_id
        )
    )
    obj = res.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    return obj


@router.post("/", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(body: SessionCreate, user: CurrentUser, db: DBSession) -> DesignSession:
    session = DesignSession(
        user_id=user.id,
        title=body.title,
        room_image_id=body.room_image_id,
        profile_snapshot=user.design_profile or {},
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/", response_model=list[SessionOut])
async def list_sessions(user: CurrentUser, db: DBSession) -> list[DesignSession]:
    res = await db.execute(
        select(DesignSession)
        .where(DesignSession.user_id == user.id)
        .order_by(DesignSession.updated_at.desc())
        .limit(50)
    )
    return list(res.scalars().all())


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(session_id: uuid.UUID, user: CurrentUser, db: DBSession) -> DesignSession:
    return await _get_owned(db, session_id, user.id)


@router.patch("/{session_id}", response_model=SessionOut)
async def patch_session(
    session_id: uuid.UUID, body: SessionUpdate, user: CurrentUser, db: DBSession
) -> DesignSession:
    session = await _get_owned(db, session_id, user.id)
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no fields provided")
    for key, value in updates.items():
        setattr(session, key, value)
    await db.commit()
    await db.refresh(session)
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: uuid.UUID, user: CurrentUser, db: DBSession) -> None:
    session = await _get_owned(db, session_id, user.id)
    await db.delete(session)
    await db.commit()
