import uuid

import pytest

from app.models.notification import Notification


async def _seed(db_session, user_id, *, title="Order shipped", unread=True):
    n = Notification(
        user_id=user_id,
        kind="delivery",
        title=title,
        summary="Your order is on its way.",
        unread=unread,
        payload={"tracking": "ABC123"},
    )
    db_session.add(n)
    await db_session.commit()
    await db_session.refresh(n)
    return n


@pytest.mark.asyncio
async def test_notifications_list_and_read(auth_client, db_session, test_user):
    n1 = await _seed(db_session, test_user.id, title="One")
    n2 = await _seed(db_session, test_user.id, title="Two", unread=False)

    r = await auth_client.get("/api/v1/notifications/")
    assert r.status_code == 200
    body = r.json()
    assert body["item_count"] == 2
    assert body["unread_count"] == 1
    titles = [i["title"] for i in body["items"]]
    assert {"One", "Two"} == set(titles)

    # Mark n1 read
    r = await auth_client.post(f"/api/v1/notifications/{n1.id}/read")
    assert r.status_code == 200
    assert r.json()["unread"] is False

    r = await auth_client.get("/api/v1/notifications/?unread_only=true")
    assert r.json()["item_count"] == 0

    # Use n2 to silence unused-warning
    assert n2.id is not None


@pytest.mark.asyncio
async def test_notifications_read_all_and_delete(
    auth_client, db_session, test_user
):
    n = await _seed(db_session, test_user.id)

    r = await auth_client.post("/api/v1/notifications/read-all")
    assert r.status_code == 204

    r = await auth_client.get("/api/v1/notifications/")
    assert r.json()["unread_count"] == 0

    r = await auth_client.delete(f"/api/v1/notifications/{n.id}")
    assert r.status_code == 204
    r = await auth_client.get("/api/v1/notifications/")
    assert r.json()["item_count"] == 0


@pytest.mark.asyncio
async def test_notifications_404(auth_client):
    bogus = uuid.uuid4()
    r = await auth_client.post(f"/api/v1/notifications/{bogus}/read")
    assert r.status_code == 404
    r = await auth_client.delete(f"/api/v1/notifications/{bogus}")
    assert r.status_code == 404
