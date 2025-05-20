
from fastapi import APIRouter

from .suggestions import router as suggestions_router

router = APIRouter()
router.include_router(suggestions_router)