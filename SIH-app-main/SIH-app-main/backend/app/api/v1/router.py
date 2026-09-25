from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, rules, scans

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(scans.router, prefix="/scans", tags=["scans"])
api_router.include_router(rules.router, prefix="/rules", tags=["rules"])
