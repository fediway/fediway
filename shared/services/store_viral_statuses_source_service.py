from sqlmodel import Session, text
from redis import Redis

from config import config
import modules.utils as utils
from modules.fediway.sources.statuses import ViralStatusesSource


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

            with utils.duration(
                "Precomputed candidates for " + source.name() + " in {:.3f} seconds."
            ):
                source.store()
