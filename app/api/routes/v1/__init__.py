
from fastapi import APIRouter

from .timelines import router as timelines_router
from .fediway import router as fediway_router

router = APIRouter()
router.include_router(fediway_router, prefix='/fediway')
router.include_router(timelines_router, prefix='/timelines')