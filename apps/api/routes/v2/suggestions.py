from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def suggestions():
    # TODO
    return True
