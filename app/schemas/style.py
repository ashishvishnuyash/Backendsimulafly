from pydantic import BaseModel


class StyleOut(BaseModel):
    slug: str
    name: str
    category: str
    vibe: str
    image_url: str | None
    trending: bool


class StyleCategory(BaseModel):
    category: str
    items: list[StyleOut]


class StyleCatalog(BaseModel):
    """Top-level shape returned by `GET /styles/`. Categories are ordered
    by the editorial doc; clients render them as horizontal rows."""

    categories: list[StyleCategory]
    item_count: int
