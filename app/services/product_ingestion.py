"""CSV → Postgres + pgvector ingestion script.

Run: `python -m app.services.product_ingestion`

Loads data/amazon_data.csv, embeds via Azure (text-embedding-3-large → 3072d),
bulk-upserts into `products`, then builds the IVFFlat index. Idempotent —
safe to rerun.
"""

from __future__ import annotations

import asyncio
import math
import re
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

from app.core.database import SessionLocal, engine
from app.core.logging import configure_logging, get_logger
from app.models.product import Product
from app.services.llm import get_embeddings

log = get_logger(__name__)

CSV_PATH = Path("data/amazon_data.csv")
BATCH_SIZE = 64  # embedding API chunk size — 64 balances throughput and retry cost


# --------------------------- CSV → normalized row ---------------------------

# Raw CSV columns (from amazon_data.csv):
#   Search Query, Title, Price, Rating, Brand, Color, Material, Size/Dimensions,
#   About This Item, Image URL, All Specifications, URL, ASIN

_PRICE_RE = re.compile(r"[^\d.]+")


def _is_na(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and value.strip().lower() in {"", "n/a", "na", "none"}:
        return True
    return False


def _clean(value: object) -> str | None:
    if _is_na(value):
        return None
    return str(value).strip()


def _parse_price(raw: object) -> float | None:
    """Convert '₹8,299.00' / '₹ 12,999' / '8299.00' → 8299.0."""
    if _is_na(raw):
        return None
    s = _PRICE_RE.sub("", str(raw))
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _parse_rating(raw: object) -> float | None:
    if _is_na(raw):
        return None
    try:
        return float(str(raw).strip().split()[0])
    except (ValueError, IndexError):
        return None


def _embedding_text(row: pd.Series) -> str:
    """Compose a dense description used for the embedding input."""
    bits: list[str] = []
    title = _clean(row.get("Title"))
    if title:
        bits.append(title)
    category = _clean(row.get("Search Query"))
    if category:
        bits.append(f"Category: {category}")
    brand = _clean(row.get("Brand"))
    if brand:
        bits.append(f"Brand: {brand}")
    color = _clean(row.get("Color"))
    if color:
        bits.append(f"Color: {color}")
    material = _clean(row.get("Material"))
    if material:
        bits.append(f"Material: {material}")
    dims = _clean(row.get("Size/Dimensions"))
    if dims:
        bits.append(f"Dimensions: {dims}")
    about = _clean(row.get("About This Item"))
    if about:
        # trim — "About This Item" fields are often very long bullet lists
        bits.append(about[:1200])
    return ". ".join(bits)[:3000]


def _build_metadata(row: pd.Series) -> dict:
    keys = {
        "brand": "Brand",
        "color": "Color",
        "material": "Material",
        "dimensions": "Size/Dimensions",
        "description": "About This Item",
        "specifications": "All Specifications",
    }
    out: dict = {}
    for dest, src in keys.items():
        v = _clean(row.get(src))
        if v:
            # keep metadata values bounded so row reads stay cheap
            out[dest] = v[:1500]
    return out


def _row_to_record(row: pd.Series, embedding: list[float]) -> dict:
    asin = _clean(row.get("ASIN"))
    title = _clean(row.get("Title"))
    if not asin or not title:
        return {}
    category = _clean(row.get("Search Query"))
    return {
        "asin": asin[:32],
        "title": title[:2000],
        "category": category[:255] if category else None,
        "price": _parse_price(row.get("Price")),
        "image_url": _clean(row.get("Image URL")),
        "product_url": _clean(row.get("URL")),
        "rating": _parse_rating(row.get("Rating")),
        "metadata": _build_metadata(row),
        "embedding": embedding,
    }


# ------------------------------ ingestion loop ------------------------------


async def ingest(csv_path: Path = CSV_PATH) -> None:
    configure_logging()
    if not csv_path.exists():
        log.error("csv_missing", path=str(csv_path))
        sys.exit(1)

    df = pd.read_csv(csv_path)
    df = df.dropna(subset=["ASIN", "Title"]).drop_duplicates(subset=["ASIN"]).reset_index(drop=True)
    log.info("csv_loaded", rows=len(df))

    embedder = get_embeddings()
    total = 0
    failed = 0
    async with SessionLocal() as db:
        for start in range(0, len(df), BATCH_SIZE):
            batch = df.iloc[start : start + BATCH_SIZE]
            texts = [_embedding_text(row) for _, row in batch.iterrows()]
            try:
                embeddings = await embedder.aembed_documents(texts)
            except Exception as e:
                log.exception("embedding_batch_failed", start=start, error=str(e))
                failed += len(batch)
                continue

            records: list[dict] = []
            for (_, row), emb in zip(batch.iterrows(), embeddings):
                rec = _row_to_record(row, emb)
                if rec:
                    records.append(rec)
            if not records:
                continue

            # Insert into the underlying Table (not the mapped class) so dict keys use
            # raw DB column names — avoids the ORM's reserved "metadata" attribute clash.
            stmt = insert(Product.__table__).values(records)
            update_cols = {
                c.name: stmt.excluded[c.name]
                for c in Product.__table__.columns
                if c.name not in {"id", "asin", "created_at"}
            }
            stmt = stmt.on_conflict_do_update(index_elements=["asin"], set_=update_cols)
            try:
                await db.execute(stmt)
                await db.commit()
            except Exception as e:
                log.exception("upsert_batch_failed", start=start, error=str(e))
                await db.rollback()
                failed += len(records)
                continue
            total += len(records)
            log.info("batch_done", ingested=total, failed=failed)

    # Index strategy: IVFFlat/HNSW on `vector` type cap at 2000 dims; text-embedding-3-large
    # is 3072 dims. Try halfvec-cast HNSW first (works up to 4000 dims, halved storage).
    # If the pgvector version on the server is too old, skip indexing — sequential scan
    # on ~3k rows is still <100ms.
    halfvec_hnsw = (
        "CREATE INDEX IF NOT EXISTS products_embedding_idx "
        "ON products USING hnsw ((embedding::halfvec(3072)) halfvec_cosine_ops)"
    )
    try:
        async with engine.begin() as conn:
            await conn.execute(text(halfvec_hnsw))
            await conn.execute(text("ANALYZE products"))
        log.info("index_created", kind="hnsw_halfvec")
    except Exception as e:
        log.warning("index_skipped", reason=str(e)[:200])
    log.info("ingestion_complete", total=total, failed=failed)


def main() -> None:
    asyncio.run(ingest())


if __name__ == "__main__":
    main()
