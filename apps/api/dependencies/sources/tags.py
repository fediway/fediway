from fastapi import Depends
from redis import Redis

from apps.api.sources.tags import TrendingTagsSource
from config import config
from modules.fediway.sources import Source
from shared.core.redis import get_redis

from ..lang import get_languages


def get_trending_tags_source(
    r: Redis = Depends(get_redis),
    languages: list[str] = Depends(get_languages),
) -> list[tuple[Source, int]]:
    if not config.feeds.trends.tags.enabled:
        return []
    return [
        (
            TrendingTagsSource(r=r, language=lang),
            100,
        )
        for lang in languages
    ]


def get_trending_tags_sources(
    trending: list[tuple[Source, int]] = Depends(get_trending_tags_source),
) -> dict[str, list[tuple[Source, int]]]:
    return {"trending": trending}
