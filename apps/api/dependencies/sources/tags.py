from fastapi import Depends
from redis import Redis
from sqlmodel import Session as RWSession

from apps.api.sources.tags import TrendingTagsSource
from config.algorithm import algorithm_config
from modules.fediway.sources import Source
from shared.core.redis import get_redis
from shared.core.rw import get_rw_session


def get_trending_tags_source(
    r: Redis = Depends(get_redis),
    rw: RWSession = Depends(get_rw_session),
) -> list[tuple[Source, int]]:
    cfg = algorithm_config.trends.tags
    return [
        (
            TrendingTagsSource(
                r=r,
                rw=rw,
                window_hours=cfg.settings.window_hours,
                min_posts=cfg.settings.min_posts,
                min_accounts=cfg.settings.min_accounts,
                local_only=cfg.settings.local_only,
                weight_posts=cfg.scoring.weight_posts,
                weight_accounts=cfg.scoring.weight_accounts,
                velocity_boost=cfg.scoring.velocity_boost,
                blocked_tags=cfg.filters.blocked_tags,
            ),
            100,
        )
    ]


def get_trending_tags_sources(
    trending: list[tuple[Source, int]] = Depends(get_trending_tags_source),
) -> dict[str, list[tuple[Source, int]]]:
    return {"trending": trending}
