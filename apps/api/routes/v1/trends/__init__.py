from fastapi import APIRouter

from .statuses import router as statuses_router
from .tags import router as tags_router

router = APIRouter(prefix="/trends")
router.include_router(statuses_router)
router.include_router(tags_router)
