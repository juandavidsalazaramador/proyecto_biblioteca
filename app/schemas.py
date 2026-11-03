"""Esquemas Pydantic v2."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ---------- Libros ----------
class LibroBase(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    autor: str = Field(min_length=1, max_length=150)
    isbn: str = Field(min_length=10, max_length=20)
    categoria: Optional[str] = Field(default=None, max_length=80)


class LibroCreate(LibroBase):
    stock_total: int = Field(default=1, ge=0)
    # Si se omite, será igual a stock_total
    stock_disponible: Optional[int] = Field(default=None, ge=0)


class LibroUpdate(BaseModel):
    titulo: Optional[str] = Field(default=None, min_length=1, max_length=200)
    autor: Optional[str] = Field(default=None, min_length=1, max_length=150)
    isbn: Optional[str] = Field(default=None, min_length=10, max_length=20)
    categoria: Optional[str] = Field(default=None, max_length=80)
    stock_total: Optional[int] = Field(default=None, ge=0)


class LibroOut(LibroBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    stock_total: int
    stock_disponible: int


class LibroPage(BaseModel):
    total: int
    page: int
    size: int
    items: list[LibroOut]


# ---------- Usuarios ----------
class UsuarioBase(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    email: EmailStr
    telefono: Optional[str] = Field(default=None, max_length=30)


class UsuarioCreate(UsuarioBase):
    activo: bool = True


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=1, max_length=150)
    email: Optional[EmailStr] = None
    telefono: Optional[str] = Field(default=None, max_length=30)
    activo: Optional[bool] = None


class UsuarioOut(UsuarioBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    activo: bool


# ---------- Préstamos ----------
class PrestamoCreate(BaseModel):
    usuario_id: int = Field(gt=0)
    libro_id: int = Field(gt=0)
    dias: Optional[int] = Field(default=None, ge=1, le=90, description="Días de préstamo")


class PrestamoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    usuario_id: int
    libro_id: int
    fecha_prestamo: datetime
    fecha_limite: datetime
    fecha_devolucion: Optional[datetime] = None
