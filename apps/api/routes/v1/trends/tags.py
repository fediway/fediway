import random

from apps.api.dependencies.sources.tags import get_influential_sources
from fastapi import APIRouter, Depends
from sqlmodel import Session as DBSession
from sqlmodel import select

from modules.mastodon.items import TagItem
from modules.mastodon.models import Tag
from shared.core.db import get_db_session

router = APIRouter()


@router.get("/tags")
async def tag_trends(
    sources=Depends(get_influential_sources),
    db: DBSession = Depends(get_db_session),
) -> list[TagItem]:
    candidates = []
    for source in sources:
        for candidate in source.collect(10):
            candidates.append(candidate)

    random.shuffle(candidates)
    candidates = candidates[:10]

    tags = db.exec(select(Tag).where(Tag.id.in_(candidates))).all()

    return [
        TagItem(
            name=tag.name,
            url="",
        )
        for tag in tags
    ]
