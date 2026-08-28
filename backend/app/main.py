from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import get_settings
from app.database import Base, engine
from app.logging_config import setup_logging

settings = get_settings()
setup_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    description="Compression. OCR. Integrity. All Verified.",
    version="1.0.0",
    lifespan=lifespan,
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url=f"{settings.api_v1_prefix}/docs",
    redoc_url=f"{settings.api_v1_prefix}/redoc",
)

from fastapi.staticfiles import StaticFiles
from pathlib import Path

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

local_storage_path = Path(__file__).resolve().parents[2] / "uploads" / "_local_storage"
local_storage_path.mkdir(parents=True, exist_ok=True)
app.mount("/dev-storage", StaticFiles(directory=str(local_storage_path)), name="dev-storage")

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name}
