from fastapi import APIRouter

from .home import router as home_router

router = APIRouter(prefix="/timelines")
router.include_router(home_router)
