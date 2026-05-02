from fastapi import APIRouter, HTTPException, Request, status

from app.schemas.style import StyleCatalog, StyleCategory, StyleOut
from app.services import style_catalog

router = APIRouter(prefix="/styles", tags=["styles"])


def _image_url(request: Request, filename: str | None) -> str | None:
    if not filename:
        return None
    base = str(request.base_url).rstrip("/")
    return f"{base}/static/styles/{filename}"


def _serialize(request: Request, s: style_catalog.StyleTemplate) -> StyleOut:
    return StyleOut(
        slug=s.slug,
        name=s.name,
        category=s.category,
        vibe=s.vibe,
        image_url=_image_url(request, s.image_filename),
        trending=s.trending,
    )


@router.get("/", response_model=StyleCatalog)
async def list_styles(request: Request) -> StyleCatalog:
    cats = []
    total = 0
    for category in style_catalog.categories():
        items = [
            _serialize(request, s)
            for s in style_catalog.by_category(category)
        ]
        cats.append(StyleCategory(category=category, items=items))
        total += len(items)
    return StyleCatalog(categories=cats, item_count=total)


@router.get("/{slug}", response_model=StyleOut)
async def get_style(slug: str, request: Request) -> StyleOut:
    s = style_catalog.get(slug)
    if s is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="style not found"
        )
    return _serialize(request, s)
