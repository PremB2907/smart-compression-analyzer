from fastapi import APIRouter

from app.api.v1 import auth, benchmark, dashboard, uploads

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(uploads.router)
api_router.include_router(dashboard.router)
api_router.include_router(benchmark.router)
