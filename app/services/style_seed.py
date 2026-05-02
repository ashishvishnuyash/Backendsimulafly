"""Seed the `styles` table from `data/style_templates/templates.json`.

Two entry points:

  * `seed_if_empty(db)` — called from the FastAPI lifespan. No-ops if the
    table already has rows. First-run / fresh-deploy bootstrap.

  * Module-as-script: `python -m app.services.style_seed` — runs the seed
    against the configured DATABASE_URL. Pass `--upsert` to force an
    upsert (re-import + update existing rows by slug); pass `--reset`
    to wipe the table first (DESTRUCTIVE).

Image files referenced by the JSON must already live under
`data/style_templates/images/` — the seed only writes DB rows.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.models.style import Style
from app.services.style_catalog import slugify

log = logging.getLogger(__name__)

_JSON_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "style_templates"
    / "templates.json"
)


def _load_templates() -> list[dict]:
    if not _JSON_PATH.is_file():
        log.warning("style seed JSON missing at %s — nothing to seed", _JSON_PATH)
        return []
    with _JSON_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    return list(data.get("templates", []))


def _normalise(t: dict, used_slugs: set[str], category_first: dict[str, bool]) -> dict:
    """Map a JSON template entry to Style kwargs."""
    name = t["name"]
    category = t["category"]
    slug = slugify(name)
    if slug in used_slugs:
        slug = slugify(f"{name}-{category}")
    used_slugs.add(slug)

    img = t.get("image", "") or ""
    if img.startswith("images/"):
        img = img[len("images/"):]

    # Trending — first style in each category (deterministic, no metadata
    # needed in the JSON).
    trending = category_first.get(category, True)
    category_first[category] = False

    return dict(
        slug=slug,
        name=name,
        category=category,
        vibe=t.get("vibe_check", "") or "",
        description=t.get("description", "") or "",
        image_filename=img or None,
        trending=trending,
        is_active=True,
        display_order=int(t.get("id", 0)) or 0,
    )


async def _table_count(db: AsyncSession) -> int:
    res = await db.execute(select(func.count()).select_from(Style))
    return int(res.scalar() or 0)


async def seed_if_empty(db: AsyncSession) -> int:
    """Insert the JSON catalog only if the table is empty. Returns the
    number of rows inserted (0 if the table was already populated)."""
    count = await _table_count(db)
    if count > 0:
        log.info("styles table has %d rows — skipping initial seed", count)
        return 0
    return await _insert_all(db, upsert=False)


async def _insert_all(db: AsyncSession, *, upsert: bool) -> int:
    templates = _load_templates()
    if not templates:
        return 0

    used_slugs: set[str] = set()
    category_first: dict[str, bool] = {}

    inserted = 0
    updated = 0
    for t in templates:
        kwargs = _normalise(t, used_slugs, category_first)
        existing = (
            await db.execute(select(Style).where(Style.slug == kwargs["slug"]))
        ).scalar_one_or_none()

        if existing is None:
            db.add(Style(**kwargs))
            inserted += 1
        elif upsert:
            for k, v in kwargs.items():
                setattr(existing, k, v)
            updated += 1
        # else: existing row, not upserting — leave it alone.

    await db.commit()
    log.info("style seed: inserted=%d updated=%d", inserted, updated)
    return inserted + updated


async def _wipe(db: AsyncSession) -> None:
    await db.execute(delete(Style))
    await db.commit()


async def _main(args: argparse.Namespace) -> int:
    async with SessionLocal() as db:
        if args.reset:
            print("Wiping styles table…")
            await _wipe(db)
        n = await _insert_all(db, upsert=args.upsert or args.reset)
        print(f"Done — touched {n} rows.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the styles table from templates.json.")
    parser.add_argument(
        "--upsert",
        action="store_true",
        help="Update existing rows by slug (default: skip).",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="WIPE the styles table first, then re-seed (destructive).",
    )
    cli_args = parser.parse_args()
    raise SystemExit(asyncio.run(_main(cli_args)))
