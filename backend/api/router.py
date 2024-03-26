from fastapi import APIRouter

from api.v1.healthcheck import router as healthcheck_router

router = APIRouter(prefix="/api/v1")
router.include_router(healthcheck_router)
