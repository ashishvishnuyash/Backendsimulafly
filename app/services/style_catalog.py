"""Editorial design-style catalog — DB-backed.

Source of truth is the `styles` table. The first time the app runs against
a fresh DB the table is empty; `app.services.style_seed.seed_if_empty()`
populates it from `data/style_templates/templates.json`. After that, admins
add new styles via the protected endpoints (or by re-running the CLI seed
with `--upsert`).

This module exposes async helpers used by `app/routers/styles.py`. They run
plain SELECTs — the catalog is small (≤ a few hundred rows), so we don't
bother with caching.
"""
from __future__ import annotations

import re
import uuid
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.style import Style


def slugify(text: str) -> str:
    s = text.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "style"


# ──────────────────────────────────────────────────────────────────────────────
# Read helpers (used by the public router)
# ──────────────────────────────────────────────────────────────────────────────

async def list_active(db: AsyncSession) -> list[Style]:
    """All visible styles, ordered by `display_order` then name. The seed
    populates `display_order` from the JSON's id, so categories come out in
    the editorial order (Living Room first, etc.) — `group_by_category`
    below preserves first-appearance order. Inactive rows are filtered."""
    res = await db.execute(
        select(Style)
        .where(Style.is_active.is_(True))
        .order_by(Style.display_order, Style.name)
    )
    return list(res.scalars().all())


def group_by_category(items: Iterable[Style]) -> list[tuple[str, list[Style]]]:
    """Stable category order — by first appearance in the input."""
    groups: dict[str, list[Style]] = {}
    for s in items:
        groups.setdefault(s.category, []).append(s)
    return list(groups.items())


async def get_by_slug(db: AsyncSession, slug: str) -> Style | None:
    res = await db.execute(select(Style).where(Style.slug == slug))
    return res.scalar_one_or_none()


async def get_by_id(db: AsyncSession, style_id: uuid.UUID) -> Style | None:
    return await db.get(Style, style_id)
