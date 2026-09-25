from fastapi import APIRouter, Depends

from src.core.config import Settings, get_settings


base_router = APIRouter(tags=["health"])


@base_router.get("/health")
async def health(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "app_version": settings.app_version,
    }
