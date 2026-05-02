from pydantic import BaseModel, Field


class StyleOut(BaseModel):
    slug: str
    name: str
    category: str
    vibe: str
    description: str
    image_url: str | None
    trending: bool


class StyleCategory(BaseModel):
    category: str
    items: list[StyleOut]


class StyleCatalog(BaseModel):
    """Top-level shape returned by `GET /styles/`. Categories are ordered
    by first appearance in the DB; clients render them as horizontal rows."""

    categories: list[StyleCategory]
    item_count: int


# ──────────────────────────────────────────────────────────────────────────────
# Admin shapes — used by the protected create/update endpoints. The image
# file itself is uploaded separately (drop into `data/style_templates/images/`
# or use the upload route); admins reference it by filename here.
# ──────────────────────────────────────────────────────────────────────────────


class StyleCreate(BaseModel):
    slug: str | None = Field(default=None, max_length=96)
    name: str = Field(min_length=1, max_length=160)
    category: str = Field(min_length=1, max_length=80)
    vibe: str = Field(default="", max_length=512)
    description: str = Field(default="")
    image_filename: str | None = Field(default=None, max_length=255)
    trending: bool = False
    display_order: int = 0


class StyleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    category: str | None = Field(default=None, min_length=1, max_length=80)
    vibe: str | None = Field(default=None, max_length=512)
    description: str | None = None
    image_filename: str | None = Field(default=None, max_length=255)
    trending: bool | None = None
    is_active: bool | None = None
    display_order: int | None = None
