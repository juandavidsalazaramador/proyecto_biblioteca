"""CRUD de usuarios (lectores)."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Response, status
from psycopg import errors

from app.database import pool
from app.schemas import UsuarioCreate, UsuarioOut, UsuarioUpdate

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

COLS = "id, nombre, email, telefono, activo"


@router.post("", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
async def crear_usuario(data: UsuarioCreate):
    try:
        async with pool.connection() as conn:
            cur = await conn.execute(
                f"""INSERT INTO usuarios (nombre, email, telefono, activo)
                    VALUES (%s,%s,%s,%s) RETURNING {COLS}""",
                (data.nombre, data.email, data.telefono, data.activo),
            )
            return await cur.fetchone()
    except errors.UniqueViolation:
        raise HTTPException(400, "Ya existe un usuario con ese email")


@router.get("", response_model=list[UsuarioOut])
async def listar_usuarios(
    activo: Optional[bool] = None,
    q: Optional[str] = Query(None, description="Busca en nombre o email"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
):
    where, params = [], []
    if activo is not None:
        where.append("activo = %s")
        params.append(activo)
    if q:
        where.append("(nombre ILIKE %s OR email ILIKE %s)")
        params += [f"%{q}%"] * 2
    w = f"WHERE {' AND '.join(where)}" if where else ""
    async with pool.connection() as conn:
        cur = await conn.execute(
            f"SELECT {COLS} FROM usuarios {w} ORDER BY id LIMIT %s OFFSET %s",
            params + [size, (page - 1) * size],
        )
        return await cur.fetchall()


@router.get("/{usuario_id}", response_model=UsuarioOut)
async def obtener_usuario(usuario_id: int):
    async with pool.connection() as conn:
        cur = await conn.execute(f"SELECT {COLS} FROM usuarios WHERE id=%s", (usuario_id,))
        u = await cur.fetchone()
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    return u


@router.put("/{usuario_id}", response_model=UsuarioOut)
async def actualizar_usuario(usuario_id: int, data: UsuarioUpdate):
    cambios = data.model_dump(exclude_unset=True)
    if not cambios:
        raise HTTPException(400, "No hay campos para actualizar")
    sets = ", ".join(f"{k}=%s" for k in cambios)
    try:
        async with pool.connection() as conn:
            cur = await conn.execute(
                f"UPDATE usuarios SET {sets} WHERE id=%s RETURNING {COLS}",
                [*cambios.values(), usuario_id],
            )
            u = await cur.fetchone()
    except errors.UniqueViolation:
        raise HTTPException(400, "Ya existe un usuario con ese email")
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    return u


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_usuario(usuario_id: int):
    try:
        async with pool.connection() as conn:
            cur = await conn.execute("DELETE FROM usuarios WHERE id=%s", (usuario_id,))
            if cur.rowcount == 0:
                raise HTTPException(404, "Usuario no encontrado")
    except errors.ForeignKeyViolation:
        raise HTTPException(
            400, "No se puede eliminar: el usuario tiene préstamos (desactívalo en su lugar)"
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
