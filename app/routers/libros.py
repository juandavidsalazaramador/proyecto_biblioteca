"""CRUD de libros."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Response, status
from psycopg import errors

from app.database import pool
from app.schemas import LibroCreate, LibroOut, LibroPage, LibroUpdate

router = APIRouter(prefix="/libros", tags=["Libros"])

COLS = "id, titulo, autor, isbn, categoria, stock_total, stock_disponible"


@router.post("", response_model=LibroOut, status_code=status.HTTP_201_CREATED)
async def crear_libro(data: LibroCreate):
    disp = data.stock_total if data.stock_disponible is None else data.stock_disponible
    if disp > data.stock_total:
        raise HTTPException(400, "stock_disponible no puede superar stock_total")
    try:
        async with pool.connection() as conn:
            cur = await conn.execute(
                f"""INSERT INTO libros (titulo, autor, isbn, categoria, stock_total, stock_disponible)
                    VALUES (%s,%s,%s,%s,%s,%s) RETURNING {COLS}""",
                (data.titulo, data.autor, data.isbn, data.categoria, data.stock_total, disp),
            )
            return await cur.fetchone()
    except errors.UniqueViolation:
        raise HTTPException(400, "Ya existe un libro con ese ISBN")


@router.get("", response_model=LibroPage)
async def listar_libros(
    q: Optional[str] = Query(None, description="Busca en título o autor"),
    categoria: Optional[str] = None,
    disponible: Optional[bool] = Query(None, description="Solo con stock disponible"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
):
    where, params = [], []
    if q:
        where.append("(titulo ILIKE %s OR autor ILIKE %s)")
        params += [f"%{q}%"] * 2
    if categoria:
        where.append("categoria ILIKE %s")
        params.append(categoria)
    if disponible is True:
        where.append("stock_disponible > 0")
    elif disponible is False:
        where.append("stock_disponible = 0")
    w = f"WHERE {' AND '.join(where)}" if where else ""

    async with pool.connection() as conn:
        cur = await conn.execute(f"SELECT count(*) AS n FROM libros {w}", params)
        total = (await cur.fetchone())["n"]
        cur = await conn.execute(
            f"SELECT {COLS} FROM libros {w} ORDER BY id LIMIT %s OFFSET %s",
            params + [size, (page - 1) * size],
        )
        items = await cur.fetchall()
    return {"total": total, "page": page, "size": size, "items": items}


@router.get("/{libro_id}", response_model=LibroOut)
async def obtener_libro(libro_id: int):
    async with pool.connection() as conn:
        cur = await conn.execute(f"SELECT {COLS} FROM libros WHERE id=%s", (libro_id,))
        libro = await cur.fetchone()
    if not libro:
        raise HTTPException(404, "Libro no encontrado")
    return libro


@router.put("/{libro_id}", response_model=LibroOut)
async def actualizar_libro(libro_id: int, data: LibroUpdate):
    cambios = data.model_dump(exclude_unset=True)
    if not cambios:
        raise HTTPException(400, "No hay campos para actualizar")
    try:
        async with pool.connection() as conn:
            cur = await conn.execute(
                f"SELECT {COLS} FROM libros WHERE id=%s FOR UPDATE", (libro_id,)
            )
            actual = await cur.fetchone()
            if not actual:
                raise HTTPException(404, "Libro no encontrado")
            # Si cambia stock_total, se ajusta stock_disponible en la misma diferencia
            if "stock_total" in cambios and cambios["stock_total"] is not None:
                nuevo_disp = actual["stock_disponible"] + (
                    cambios["stock_total"] - actual["stock_total"]
                )
                if nuevo_disp < 0:
                    raise HTTPException(
                        400, "stock_total menor a los ejemplares actualmente prestados"
                    )
                cambios["stock_disponible"] = nuevo_disp
            sets = ", ".join(f"{k}=%s" for k in cambios)
            cur = await conn.execute(
                f"UPDATE libros SET {sets} WHERE id=%s RETURNING {COLS}",
                [*cambios.values(), libro_id],
            )
            return await cur.fetchone()
    except errors.UniqueViolation:
        raise HTTPException(400, "Ya existe un libro con ese ISBN")


@router.delete("/{libro_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_libro(libro_id: int):
    try:
        async with pool.connection() as conn:
            cur = await conn.execute("DELETE FROM libros WHERE id=%s", (libro_id,))
            if cur.rowcount == 0:
                raise HTTPException(404, "Libro no encontrado")
    except errors.ForeignKeyViolation:
        raise HTTPException(400, "No se puede eliminar: el libro tiene préstamos asociados")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
