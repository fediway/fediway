from fastapi import Depends

from modules.fediway.sources import Source
from modules.fediway.sources.follows import RecentlyPopularSource
from modules.mastodon.models import Account

from shared.core.schwarm import driver as schwarm_driver

from ..lang import get_languages
from ..auth import get_authenticated_account_or_fail


def get_recently_popular_sources(
    account: Account = Depends(get_authenticated_account_or_fail),
    languages: list[str] = Depends(get_languages),
) -> list[Source]:
    return [
        RecentlyPopularSource(
            driver=schwarm_driver,
            account_id=account.id,
            language=lang,
        )
        for lang in languages
    ]
