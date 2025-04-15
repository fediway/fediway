
from ..base import Source
from .herde import Herde

class TrendingStatusesByInfluentialUsers(Herde, Source):
    def __init__(self, driver, language: str = 'en'):
        super().__init__(driver)
        self.language = language

    def collect(self, limit: int):
        for result in self.get_relevant_statuses(self.language, limit=limit):
            yield result['status_id']