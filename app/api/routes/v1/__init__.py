
from fastapi import APIRouter

from .timelines import router as timelines_router

router = APIRouter()
router.include_router(timelines_router, prefix='/timelines')