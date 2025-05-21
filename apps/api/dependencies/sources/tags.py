from datetime import timedelta

from fastapi import Depends

from config import config
from modules.fediway.sources import Source
from modules.fediway.sources.tags import InfluentialSource
from shared.core.schwarm import driver as schwarm_driver

from ..lang import get_languages

MAX_AGE = timedelta(days=config.fediway.feed_max_age_in_days)


def get_influential_sources(
    languages: list[str] = Depends(get_languages),
) -> list[Source]:
    return [
        InfluentialSource(
            driver=schwarm_driver,
            language=lang,
            max_age=MAX_AGE,
        )
        for lang in languages
    ]
