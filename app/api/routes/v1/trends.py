
import random
from sqlmodel import select, Session as DBSession
from fastapi import APIRouter, Depends

from app.core.db import get_db_session
from app.modules.models import Tag
from app.api.dependencies import get_trending_tags_sources
from app.api.items import TagItem

router = APIRouter()

@router.get('/tags')
async def tag_trends(
    sources = Depends(get_trending_tags_sources),
    db: DBSession = Depends(get_db_session),
) -> list[TagItem]:
    
    candidates = []
    for source in sources:
        for candidate in source.collect(10):
            candidates.append(candidate)
    
    random.shuffle(candidates)
    candidates = candidates[:10]

    tags = db.exec(select(Tag).where(Tag.id.in_(candidates))).all()

    return [TagItem(
        name=tag.name,
        url="",
    ) for tag in tags]