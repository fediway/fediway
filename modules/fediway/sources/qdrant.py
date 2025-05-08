
from datetime import timedelta, datetime

from .base import Source

class SimilarToFavourited(Source):
    def __init__(self, driver, account_id: int, language: str = 'en', max_age = timedelta(days=3)):
        self.driver = driver
        self.account_id = account_id
        self.language = language
        self.max_age = max_age

    def collect(self, limit: int):
        pass