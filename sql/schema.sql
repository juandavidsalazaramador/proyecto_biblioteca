-- Crear BD:  CREATE DATABASE biblioteca_13;
-- Ejecutar:  psql -U postgres -d biblioteca_13 -f sql/schema.sql

CREATE TABLE IF NOT EXISTS libros (
    id               SERIAL PRIMARY KEY,
    titulo           VARCHAR(200) NOT NULL,
    autor            VARCHAR(150) NOT NULL,
    isbn             VARCHAR(20)  NOT NULL UNIQUE,
    categoria        VARCHAR(80),
    stock_total      INTEGER NOT NULL DEFAULT 1 CHECK (stock_total >= 0),
    stock_disponible INTEGER NOT NULL DEFAULT 1,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_stock CHECK (stock_disponible BETWEEN 0 AND stock_total)
);

CREATE TABLE IF NOT EXISTS usuarios (
    id         SERIAL PRIMARY KEY,
    nombre     VARCHAR(150) NOT NULL,
    email      VARCHAR(150) NOT NULL UNIQUE,
    telefono   VARCHAR(30),
    activo     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS prestamos (
    id               SERIAL PRIMARY KEY,
    usuario_id       INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    libro_id         INTEGER NOT NULL REFERENCES libros(id)   ON DELETE RESTRICT,
    fecha_prestamo   TIMESTAMPTZ NOT NULL DEFAULT now(),
    fecha_limite     TIMESTAMPTZ NOT NULL,
    fecha_devolucion TIMESTAMPTZ,
    CONSTRAINT chk_fechas CHECK (fecha_limite >= fecha_prestamo)
);

CREATE INDEX IF NOT EXISTS idx_libros_categoria ON libros(categoria);
CREATE INDEX IF NOT EXISTS idx_prestamos_usuario ON prestamos(usuario_id);
CREATE INDEX IF NOT EXISTS idx_prestamos_libro   ON prestamos(libro_id);
CREATE INDEX IF NOT EXISTS idx_prestamos_activos
    ON prestamos(fecha_limite) WHERE fecha_devolucion IS NULL;
