"""Préstamos y devoluciones (transaccionales)."""
import os

from fastapi import APIRouter, HTTPException, Query, status

from app.database import pool
from app.schemas import PrestamoCreate, PrestamoOut

router = APIRouter(prefix="/prestamos", tags=["Préstamos"])

COLS = "id, usuario_id, libro_id, fecha_prestamo, fecha_limite, fecha_devolucion"
DIAS_DEFAULT = int(os.getenv("DIAS_PRESTAMO", 14))


@router.post("", response_model=PrestamoOut, status_code=status.HTTP_201_CREATED)
async def registrar_prestamo(data: PrestamoCreate):
    dias = data.dias or DIAS_DEFAULT
    async with pool.connection() as conn:  # una sola transacción
        cur = await conn.execute(
            "SELECT activo FROM usuarios WHERE id=%s", (data.usuario_id,)
        )
        usuario = await cur.fetchone()
        if not usuario:
            raise HTTPException(404, "Usuario no encontrado")
        if not usuario["activo"]:
            raise HTTPException(400, "El usuario está inactivo")

        # Bloquea la fila del libro para evitar sobre-préstamos concurrentes
        cur = await conn.execute(
            "SELECT stock_disponible FROM libros WHERE id=%s FOR UPDATE", (data.libro_id,)
        )
        libro = await cur.fetchone()
        if not libro:
            raise HTTPException(404, "Libro no encontrado")
        if libro["stock_disponible"] < 1:
            raise HTTPException(400, "No hay stock disponible de este libro")

        await conn.execute(
            "UPDATE libros SET stock_disponible = stock_disponible - 1 WHERE id=%s",
            (data.libro_id,),
        )
        cur = await conn.execute(
            f"""INSERT INTO prestamos (usuario_id, libro_id, fecha_limite)
                VALUES (%s, %s, now() + make_interval(days => %s)) RETURNING {COLS}""",
            (data.usuario_id, data.libro_id, dias),
        )
        return await cur.fetchone()


@router.post("/{prestamo_id}/devolucion", response_model=PrestamoOut)
async def registrar_devolucion(prestamo_id: int):
    async with pool.connection() as conn:
        cur = await conn.execute(
            "SELECT libro_id, fecha_devolucion FROM prestamos WHERE id=%s FOR UPDATE",
            (prestamo_id,),
        )
        p = await cur.fetchone()
        if not p:
            raise HTTPException(404, "Préstamo no encontrado")
        if p["fecha_devolucion"] is not None:
            raise HTTPException(400, "El préstamo ya fue devuelto")

        cur = await conn.execute(
            f"UPDATE prestamos SET fecha_devolucion = now() WHERE id=%s RETURNING {COLS}",
            (prestamo_id,),
        )
        devuelto = await cur.fetchone()
        await conn.execute(
            "UPDATE libros SET stock_disponible = stock_disponible + 1 WHERE id=%s",
            (p["libro_id"],),
        )
        return devuelto


async def _listar(condicion: str, page: int, size: int):
    async with pool.connection() as conn:
        cur = await conn.execute(
            f"""SELECT {COLS} FROM prestamos WHERE {condicion}
                ORDER BY fecha_limite LIMIT %s OFFSET %s""",
            (size, (page - 1) * size),
        )
        return await cur.fetchall()


# Rutas estáticas antes de /{prestamo_id}
@router.get("/activos", response_model=list[PrestamoOut])
async def prestamos_activos(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)):
    return await _listar("fecha_devolucion IS NULL", page, size)


@router.get("/retrasados", response_model=list[PrestamoOut])
async def prestamos_retrasados(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)):
    return await _listar("fecha_devolucion IS NULL AND fecha_limite < now()", page, size)


@router.get("/{prestamo_id}", response_model=PrestamoOut)
async def obtener_prestamo(prestamo_id: int):
    async with pool.connection() as conn:
        cur = await conn.execute(f"SELECT {COLS} FROM prestamos WHERE id=%s", (prestamo_id,))
        p = await cur.fetchone()
    if not p:
        raise HTTPException(404, "Préstamo no encontrado")
    return p
