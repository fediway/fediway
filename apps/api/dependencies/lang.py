from fastapi import Depends, Request

from apps.api.utils import parse_accept_language

from .location import get_location


def get_language_from_location(location) -> None | str:
    if location is None:
        return

    return location.lower()


def get_languages(request: Request, location: str | None = Depends(get_location)) -> list[str]:
    request_lang = parse_accept_language(request.headers.get("accept-language", ""))

    location_lang = get_language_from_location(location)

    print("location_lang", location_lang, "| request_lang", request_lang)

    languages = [location_lang, request_lang, "en"]

    return [lang for lang in set(languages) if lang is not None]
