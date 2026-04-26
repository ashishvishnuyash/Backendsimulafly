import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.cart import CartItem
from app.models.product import Product
from app.schemas.cart import CartItemAdd, CartItemOut, CartItemUpdate, CartSummary
from app.utils.dependencies import CurrentUser, DBSession

router = APIRouter(prefix="/cart", tags=["cart"])


async def _load_cart(db, user_id: uuid.UUID) -> list[CartItem]:
    res = await db.execute(
        select(CartItem)
        .options(selectinload(CartItem.product))
        .where(CartItem.user_id == user_id)
        .order_by(CartItem.added_at.desc())
    )
    return list(res.scalars().all())


def _summary(items: list[CartItem]) -> CartSummary:
    total = sum((item.product.price or 0) * item.quantity for item in items)
    return CartSummary(
        items=[CartItemOut.model_validate(i) for i in items],
        estimated_total=round(total, 2),
        item_count=sum(i.quantity for i in items),
    )


@router.get("/", response_model=CartSummary)
async def get_cart(user: CurrentUser, db: DBSession) -> CartSummary:
    items = await _load_cart(db, user.id)
    return _summary(items)


@router.post("/", response_model=CartSummary, status_code=status.HTTP_201_CREATED)
async def add_to_cart(body: CartItemAdd, user: CurrentUser, db: DBSession) -> CartSummary:
    product = await db.get(Product, body.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product not found")

    existing = await db.execute(
        select(CartItem).where(
            CartItem.user_id == user.id, CartItem.product_id == body.product_id
        )
    )
    item = existing.scalar_one_or_none()
    if item:
        item.quantity = min(10, item.quantity + body.quantity)
    else:
        db.add(CartItem(user_id=user.id, product_id=body.product_id, quantity=body.quantity))
    await db.commit()
    items = await _load_cart(db, user.id)
    return _summary(items)


@router.patch("/{item_id}", response_model=CartItemOut)
async def update_quantity(
    item_id: uuid.UUID, body: CartItemUpdate, user: CurrentUser, db: DBSession
) -> CartItem:
    res = await db.execute(
        select(CartItem)
        .options(selectinload(CartItem.product))
        .where(CartItem.id == item_id, CartItem.user_id == user.id)
    )
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="cart item not found")
    item.quantity = body.quantity
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: uuid.UUID, user: CurrentUser, db: DBSession) -> None:
    res = await db.execute(
        select(CartItem).where(CartItem.id == item_id, CartItem.user_id == user.id)
    )
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="cart item not found")
    await db.delete(item)
    await db.commit()


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(user: CurrentUser, db: DBSession) -> None:
    items = await _load_cart(db, user.id)
    for item in items:
        await db.delete(item)
    await db.commit()
