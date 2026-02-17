from redis import Redis
from sqlmodel import Session, text

from apps.api.sources.tags import TrendingTagsSource
from config import config
from shared.utils.logging import Timer, log_debug


class StoreTrendingTagsSourceService:
    def __init__(self, r: Redis, db: Session):
        self.r = r
        self.db = db

    def _get_languages(self) -> list[str]:
        query = """
        SELECT ts.language
        FROM trending_tag_stats ts
        WHERE ts.language IS NOT NULL
        GROUP BY ts.language;
        """

        return [result[0] for result in self.db.exec(text(query)).fetchall()]

    def __call__(self):
        cfg = config.feeds.trends.tags

        for lang in self._get_languages():
            source = TrendingTagsSource(
                r=self.r,
                rw=self.db,
                language=lang,
                min_posts=cfg.settings.min_posts,
                min_accounts=cfg.settings.min_accounts,
                blocked_tags=cfg.filters.blocked_tags,
            )

            with Timer() as t:
                source.store()

            log_debug(
                "Precomputed candidates",
                module="trending_tags",
                source=source.id,
                language=lang,
                duration_ms=round(t.elapsed_ms, 2),
            )
