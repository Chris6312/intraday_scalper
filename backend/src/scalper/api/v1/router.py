from fastapi import APIRouter

from scalper.api.v1.routes.health import router as health_router
from scalper.api.v1.routes.meta import router as meta_router

router = APIRouter()
router.include_router(health_router)
router.include_router(meta_router)
