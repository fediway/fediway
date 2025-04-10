
from fastapi import Request

from app.utils import parse_accept_language

def get_language_from_location(location) -> None | str:
    if location is None:
        return
    
    return location.lower()

def get_languages(request: Request) -> list[str]:
    request_lang = parse_accept_language(request.headers.get("accept-language", ""))
    location_lang = get_language_from_location(request.state.session.get('location'))

    languages = [location_lang, request_lang, 'en']
    
    return [lang for lang in set(languages) if lang is not None]