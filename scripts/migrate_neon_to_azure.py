"""One-shot data copy from Neon → Azure Postgres.

Schema is created beforehand by `alembic upgrade head` against Azure.
This script copies row data table-by-table in FK-safe order using
asyncpg + executemany. Run once; no-op-safe if target tables are empty.
"""
import asyncio
import os
import sys

import asyncpg
from pgvector.asyncpg import register_vector

NEON_DSN = os.environ["NEON_DSN"]
AZURE_DSN = os.environ["AZURE_DSN"]

# Parent → child order. alembic_version is skipped (already populated by upgrade).
TABLES = [
    "users",
    "products",
    "styles",
    "room_images",
    "design_sessions",
    "messages",
    "cart_items",
    "saved_items",
    "notifications",
]


async def get_columns(conn, table):
    rows = await conn.fetch(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = $1
        ORDER BY ordinal_position
        """,
        table,
    )
    return [r["column_name"] for r in rows]


async def copy_table(src, dst, table):
    cols = await get_columns(src, table)
    cols_q = ", ".join(f'"{c}"' for c in cols)
    placeholders = ", ".join(f"${i+1}" for i in range(len(cols)))
    select_sql = f'SELECT {cols_q} FROM "{table}"'
    insert_sql = f'INSERT INTO "{table}" ({cols_q}) VALUES ({placeholders})'

    rows = await src.fetch(select_sql)
    if not rows:
        print(f"  {table}: 0 rows — skipped")
        return 0

    records = [tuple(r[c] for c in cols) for r in rows]
    async with dst.transaction():
        await dst.executemany(insert_sql, records)
    print(f"  {table}: {len(records)} rows copied")
    return len(records)


async def verify_counts(src, dst, table):
    a = await src.fetchval(f'SELECT count(*) FROM "{table}"')
    b = await dst.fetchval(f'SELECT count(*) FROM "{table}"')
    status = "OK" if a == b else "MISMATCH"
    print(f"  {table}: src={a} dst={b} [{status}]")
    return a == b


async def main():
    src = await asyncpg.connect(NEON_DSN, ssl="require", timeout=90)
    dst = await asyncpg.connect(AZURE_DSN, ssl="require", timeout=30)
    try:
        await register_vector(src)
        await register_vector(dst)

        # Sanity: confirm target tables are empty
        print("Pre-flight: target row counts")
        any_data = False
        for t in TABLES:
            n = await dst.fetchval(f'SELECT count(*) FROM "{t}"')
            print(f"  {t}: {n}")
            if n > 0:
                any_data = True
        if any_data:
            print("ABORT: target has rows in some tables; refusing to copy")
            sys.exit(2)

        print("\nCopying...")
        total = 0
        for t in TABLES:
            total += await copy_table(src, dst, t)
        print(f"\nTotal rows copied: {total}")

        print("\nVerification:")
        all_ok = True
        for t in TABLES:
            if not await verify_counts(src, dst, t):
                all_ok = False
        # alembic_version sanity
        a = await src.fetchval("SELECT version_num FROM alembic_version")
        b = await dst.fetchval("SELECT version_num FROM alembic_version")
        print(f"  alembic_version: src={a} dst={b} [{'OK' if a == b else 'MISMATCH'}]")
        if a != b:
            all_ok = False

        sys.exit(0 if all_ok else 1)
    finally:
        await src.close()
        await dst.close()


if __name__ == "__main__":
    asyncio.run(main())
