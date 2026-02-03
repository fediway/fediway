from redis import Redis
from sqlmodel import Session, text

from modules.fediway.sources.statuses import ViralStatusesSource
from shared.utils.logging import Timer, log_debug


class StoreViralStatusesSourceService:
    def __init__(self, r: Redis, db: Session):
        self.r = r
        self.db = db

    def _get_languages(self) -> list[str]:
        query = """
        SELECT s.language
        FROM status_virality_score_languages s
        WHERE s.language IS NOT NULL
        GROUP BY s.language;
        """

        return [result[0] for result in self.db.exec(text(query)).fetchall()]

    def __call__(self):
        for lang in self._get_languages():
            source = ViralStatusesSource(
                r=self.r,
                rw=self.db,
                language=lang,
            )

            with Timer() as t:
                source.store()

            log_debug(
                "Precomputed candidates",
                module="viral_statuses",
                source=source.id,
                language=lang,
                duration_ms=round(t.elapsed_ms, 2),
            )
