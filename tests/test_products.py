import pytest

from app.models.product import Product


@pytest.mark.asyncio
async def test_products_filter_by_category_and_price(auth_client, db_session):
    products = [
        Product(asin="A1", title="Cheap Sofa", category="Sofa", price=5000, rating=4.0),
        Product(asin="A2", title="Pricey Sofa", category="Sofa", price=25000, rating=4.5),
        Product(asin="A3", title="Lamp", category="Lamp", price=2000, rating=4.2),
    ]
    for p in products:
        db_session.add(p)
    await db_session.commit()

    r = await auth_client.get("/api/v1/products/?category=Sofa&max_price=10000")
    assert r.status_code == 200
    items = r.json()
    asins = {p["asin"] for p in items}
    assert "A1" in asins
    assert "A2" not in asins
    assert "A3" not in asins


@pytest.mark.asyncio
async def test_product_by_id(auth_client, db_session):
    p = Product(asin="X1", title="Table", category="Table", price=3000, rating=4.3)
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)

    r = await auth_client.get(f"/api/v1/products/{p.id}")
    assert r.status_code == 200
    assert r.json()["asin"] == "X1"
