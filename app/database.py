"""Pool asíncrono de conexiones PostgreSQL con psycopg 3.

Uso en routers:
    async with pool.connection() as conn:   # commit al salir, rollback si hay excepción
        cur = await conn.execute("SELECT ...", (valor,))
        fila = await cur.fetchone()         # dict (dict_row)
"""
import os
from urllib.parse import quote

from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

load_dotenv()


def _conninfo() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    user = quote(os.getenv("DB_USER", "postgres"), safe="")
    pwd = quote(os.getenv("DB_PASSWORD", ""), safe="")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "biblioteca_13")
    return f"postgresql://{user}:{pwd}@{host}:{port}/{name}"


pool = AsyncConnectionPool(
    conninfo=_conninfo(),
    min_size=int(os.getenv("DB_POOL_MIN", 1)),
    max_size=int(os.getenv("DB_POOL_MAX", 10)),
    kwargs={"row_factory": dict_row},
    open=False,  # se abre en el lifespan de main.py
)


async def open_pool() -> None:
    await pool.open(wait=True, timeout=10)


async def close_pool() -> None:
    await pool.close()
