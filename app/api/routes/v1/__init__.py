
from fastapi import APIRouter

from .timelines import router as timelines_router
from .fediway import router as fediway_router
from .trends import router as trends_router

router = APIRouter()
router.include_router(fediway_router, prefix='/fediway')
router.include_router(timelines_router, prefix='/timelines')
router.include_router(trends_router, prefix='/trends')