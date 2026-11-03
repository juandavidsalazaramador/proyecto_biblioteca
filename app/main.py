"""Punto de entrada: uvicorn app.main:app --reload"""
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from app.database import close_pool, open_pool  # noqa: E402
from app.routers import libros, prestamos, usuarios  # noqa: E402

log = logging.getLogger("biblioteca-13")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await open_pool()
    yield
    await close_pool()


app = FastAPI(title="biblioteca-13", version="1.0.0", lifespan=lifespan)

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials="*" not in origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def error_500(request: Request, exc: Exception):
    log.exception("Error no controlado")
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})


app.include_router(libros.router)
app.include_router(usuarios.router)
app.include_router(prestamos.router)


@app.get("/", tags=["Health"])
async def health():
    return {"status": "ok", "app": "biblioteca-13"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
