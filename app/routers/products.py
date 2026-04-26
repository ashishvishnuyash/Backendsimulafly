import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, text

from app.models.product import Product
from app.schemas.product import ProductOut
from app.services.llm import get_embeddings
from app.services.rag_service import _vector_literal
from app.utils.dependencies import CurrentUser, DBSession

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/search", response_model=list[ProductOut])
async def search(
    user: CurrentUser,
    db: DBSession,
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[Product]:
    embedding = await get_embeddings().aembed_query(q)
    sql = text(
        "SELECT id FROM products WHERE embedding IS NOT NULL "
        "ORDER BY embedding <=> CAST(:q AS vector) LIMIT :k"
    )
    res = await db.execute(sql, {"q": _vector_literal(embedding), "k": limit})
    ids = [row[0] for row in res.fetchall()]
    if not ids:
        return []
    rows = await db.execute(select(Product).where(Product.id.in_(ids)))
    by_id = {p.id: p for p in rows.scalars().all()}
    return [by_id[i] for i in ids if i in by_id]


@router.get("/", response_model=list[ProductOut])
async def list_products(
    user: CurrentUser,
    db: DBSession,
    category: str | None = Query(default=None, max_length=255),
    max_price: float | None = Query(default=None, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[Product]:
    stmt = select(Product)
    if category:
        stmt = stmt.where(Product.category.ilike(f"%{category}%"))
    if max_price is not None:
        stmt = stmt.where(Product.price <= max_price)
    stmt = stmt.order_by(Product.rating.desc().nullslast(), Product.price.asc()).offset(offset).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: uuid.UUID, user: CurrentUser, db: DBSession) -> Product:
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product not found")
    return product
