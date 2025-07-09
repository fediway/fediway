from fastapi import APIRouter

from .fediway import router as fediway_router
from .timelines import router as timelines_router
from .trends import router as trends_router

router = APIRouter(prefix="/v1", tags=["v1"])
router.include_router(fediway_router)
# router.include_router(timelines_router)
router.include_router(trends_router)
