from fastapi import APIRouter

from .v1 import router as v1_router
from .v2 import router as v2_router

router = APIRouter()
router.include_router(v1_router)
router.include_router(v2_router)
