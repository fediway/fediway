
from fastapi import APIRouter, Depends

from app.api.items import StatusItem

router = APIRouter()

@router.get('/tags')
async def tag_trends(
    db: DBSession = Depends(get_db_session),
) -> list[TagItem]:
    feed.init()

    recommendations = feed.get_recommendations(config.fediway.feed_batch_size)
    statuses = db.exec(Status.select_by_ids([r.item for r in recommendations])).all()

    return [StatusItem.from_model(status) for status in statuses]