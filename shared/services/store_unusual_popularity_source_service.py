from sqlmodel import Session, text
from redis import Redis

from config import config
import modules.utils as utils
from modules.fediway.sources.statuses import UnusualPopularitySource


class StoreUnusualPopularitySourceService:
    def __init__(self, r: Redis, db: Session):
        self.r = r
        self.db = db

    def _get_languages(self) -> list[str]:
        query = """
        SELECT DISTINCT s.language 
        FROM status_scores sc
        JOIN statuses s 
        ON s.id = sc.status_id
        AND s.language IS NOT NULL;
        """

        return [result[0] for result in self.db.exec(text(query)).fetchall()]

    def __call__(self):
        for lang in self._get_languages():
            source = UnusualPopularitySource(
                r=self.r,
                rw=self.db,
                language=lang,
                decay_rate=config.fediway.feed_decay_rate,
            )

            with utils.duration(
                "Precomputed candidates for " + source.name() + " in {:.3f} seconds."
            ):
                source.store()
