from fastapi import Request, Depends

import modules.utils as utils
from .location import get_location


def get_language_from_location(location) -> None | str:
    if location is None:
        return

    return location.lower()


def get_languages(
    request: Request, location: str | None = Depends(get_location)
) -> list[str]:
    request_lang = utils.http.parse_accept_language(
        request.headers.get("accept-language", "")
    )
    print("location", location)
    location_lang = get_language_from_location(location)

    languages = [location_lang, request_lang, "en"]

    return [lang for lang in set(languages) if lang is not None]
