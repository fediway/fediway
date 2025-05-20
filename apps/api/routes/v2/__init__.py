from fastapi import APIRouter

from .suggestions import router as suggestions_router

router = APIRouter(prefix="/v2", tags=["v2"])
router.include_router(suggestions_router)
