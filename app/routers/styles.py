from fastapi import APIRouter, Header, HTTPException, Request, status

from app.core.config import get_settings
from app.models.style import Style
from app.schemas.style import (
    StyleCatalog,
    StyleCategory,
    StyleCreate,
    StyleOut,
    StyleUpdate,
)
from app.services import style_catalog
from app.utils.dependencies import DBSession

router = APIRouter(prefix="/styles", tags=["styles"])


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _image_url(request: Request, filename: str | None) -> str | None:
    if not filename:
        return None
    base = str(request.base_url).rstrip("/")
    return f"{base}/static/styles/{filename}"


def _serialize(request: Request, s: Style) -> StyleOut:
    return StyleOut(
        slug=s.slug,
        name=s.name,
        category=s.category,
        vibe=s.vibe,
        description=s.description,
        image_url=_image_url(request, s.image_filename),
        trending=s.trending,
    )


async def _require_admin(x_admin_key: str | None) -> None:
    settings = get_settings()
    if not settings.ADMIN_API_KEY:
        # No key configured → endpoint disabled.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="admin endpoints disabled (ADMIN_API_KEY unset)",
        )
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing X-Admin-Key",
        )


# ──────────────────────────────────────────────────────────────────────────────
# Public reads
# ──────────────────────────────────────────────────────────────────────────────


@router.get("/", response_model=StyleCatalog)
async def list_styles(request: Request, db: DBSession) -> StyleCatalog:
    items = await style_catalog.list_active(db)
    grouped = style_catalog.group_by_category(items)
    cats = [
        StyleCategory(
            category=cat,
            items=[_serialize(request, s) for s in styles],
        )
        for cat, styles in grouped
    ]
    return StyleCatalog(categories=cats, item_count=len(items))


@router.get("/{slug}", response_model=StyleOut)
async def get_style(slug: str, request: Request, db: DBSession) -> StyleOut:
    s = await style_catalog.get_by_slug(db, slug)
    if s is None or not s.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="style not found"
        )
    return _serialize(request, s)


# ──────────────────────────────────────────────────────────────────────────────
# Admin writes (X-Admin-Key required)
# ──────────────────────────────────────────────────────────────────────────────


@router.post(
    "/",
    response_model=StyleOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_style(
    body: StyleCreate,
    request: Request,
    db: DBSession,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> StyleOut:
    await _require_admin(x_admin_key)

    slug = body.slug or style_catalog.slugify(body.name)
    existing = await style_catalog.get_by_slug(db, slug)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"slug '{slug}' already exists",
        )

    s = Style(
        slug=slug,
        name=body.name,
        category=body.category,
        vibe=body.vibe,
        description=body.description,
        image_filename=body.image_filename,
        trending=body.trending,
        display_order=body.display_order,
        is_active=True,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return _serialize(request, s)


@router.patch("/{slug}", response_model=StyleOut)
async def update_style(
    slug: str,
    body: StyleUpdate,
    request: Request,
    db: DBSession,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> StyleOut:
    await _require_admin(x_admin_key)

    s = await style_catalog.get_by_slug(db, slug)
    if s is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="style not found"
        )

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(s, field, value)
    await db.commit()
    await db.refresh(s)
    return _serialize(request, s)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_style(
    slug: str,
    db: DBSession,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    hard: bool = False,
) -> None:
    """Soft-delete by default (sets is_active=false). Pass `?hard=true` to
    actually drop the row — only do that if no client could still link to it."""
    await _require_admin(x_admin_key)

    s = await style_catalog.get_by_slug(db, slug)
    if s is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="style not found"
        )

    if hard:
        await db.delete(s)
    else:
        s.is_active = False
    await db.commit()
