from fastapi import APIRouter

router = APIRouter(prefix="/fediway")


@router.get("/health")
async def health() -> bool:
    return True
