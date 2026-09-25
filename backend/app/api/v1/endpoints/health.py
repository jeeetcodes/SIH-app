from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/health")
def healthcheck() -> dict:
    return {
        "status": "ok",
        "service": "label-police",
        "providers": settings.provider_status(),
    }
