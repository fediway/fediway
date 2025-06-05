from neo4j import Driver
from redis import Redis

from config import config
import modules.utils as utils
from modules.fediway.sources.statuses import PouplarByInfluentialAccountsSource


class StorePouplarByInfluentialAccountsSourceService:
    def __init__(self, r: Redis, driver: Driver):
        self.r = r
        self.driver = driver

    def _get_languages(self) -> list[str]:
        query = """
        MATCH (s:Status)
        RETURN DISTINCT s.language AS language;
        """
        with self.driver.session() as session:
            return [result['language'] for result in session.run(query) if result['language'] is not None]

    def __call__(self):
        for lang in self._get_languages():
            source = PouplarByInfluentialAccountsSource(
                r=self.r,
                driver=self.driver,
                language=lang,
                decay_rate=config.fediway.feed_decay_rate,
            )

            with utils.duration(
                "Precomputed candidates for " + source.name() + " in {:.3f} seconds."
            ):
                source.store()
