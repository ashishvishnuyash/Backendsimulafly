import uuid

import pytest

from app.models.product import Product


async def _seed_product(db_session, *, asin: str = "B001", price: float = 999.0) -> Product:
    p = Product(asin=asin, title="Test Sofa", category="Sofa", price=price, rating=4.5)
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


@pytest.mark.asyncio
async def test_cart_add_patch_delete(auth_client, db_session):
    product = await _seed_product(db_session)

    r = await auth_client.post(
        "/api/v1/cart/", json={"product_id": str(product.id), "quantity": 2}
    )
    assert r.status_code == 201
    body = r.json()
    assert body["item_count"] == 2
    assert body["estimated_total"] == pytest.approx(product.price * 2)

    item_id = body["items"][0]["id"]

    r = await auth_client.patch(
        f"/api/v1/cart/{item_id}", json={"quantity": 5}
    )
    assert r.status_code == 200
    assert r.json()["quantity"] == 5

    r = await auth_client.get("/api/v1/cart/")
    assert r.json()["item_count"] == 5
    assert r.json()["estimated_total"] == pytest.approx(product.price * 5)

    r = await auth_client.delete(f"/api/v1/cart/{item_id}")
    assert r.status_code == 204
    r = await auth_client.get("/api/v1/cart/")
    assert r.json()["item_count"] == 0


@pytest.mark.asyncio
async def test_cart_quantity_cap(auth_client, db_session):
    product = await _seed_product(db_session, asin="B002")
    r = await auth_client.post(
        "/api/v1/cart/", json={"product_id": str(product.id), "quantity": 15}
    )
    # Either 422 from Pydantic bound or 201 clamped — Pydantic bound is le=10, so 422.
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_cart_missing_product_404(auth_client):
    r = await auth_client.post(
        "/api/v1/cart/", json={"product_id": str(uuid.uuid4()), "quantity": 1}
    )
    assert r.status_code == 404
