import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, update

from app.models.notification import Notification
from app.schemas.notification import NotificationOut, NotificationsList
from app.utils.dependencies import CurrentUser, DBSession

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", response_model=NotificationsList)
async def list_notifications(
    user: CurrentUser,
    db: DBSession,
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
) -> NotificationsList:
    stmt = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(Notification.unread.is_(True))
    stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    items = list(res.scalars().all())

    unread_stmt = select(Notification).where(
        Notification.user_id == user.id, Notification.unread.is_(True)
    )
    unread_res = await db.execute(unread_stmt)
    unread_count = len(list(unread_res.scalars().all()))

    return NotificationsList(
        items=[NotificationOut.model_validate(n) for n in items],
        item_count=len(items),
        unread_count=unread_count,
    )


@router.post("/{item_id}/read", response_model=NotificationOut)
async def mark_read(
    item_id: uuid.UUID, user: CurrentUser, db: DBSession
) -> Notification:
    res = await db.execute(
        select(Notification).where(
            Notification.id == item_id, Notification.user_id == user.id
        )
    )
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="notification not found"
        )
    if item.unread:
        item.unread = False
        await db.commit()
        await db.refresh(item)
    return item


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(user: CurrentUser, db: DBSession) -> None:
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.unread.is_(True))
        .values(unread=False)
    )
    await db.commit()


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    item_id: uuid.UUID, user: CurrentUser, db: DBSession
) -> None:
    res = await db.execute(
        select(Notification).where(
            Notification.id == item_id, Notification.user_id == user.id
        )
    )
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="notification not found"
        )
    await db.delete(item)
    await db.commit()
