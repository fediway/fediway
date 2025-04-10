
from fastapi import Request

def get_languages(request: Request) -> list[str]:
    return list(set([request.state.session.get('location', 'EN').lower(), 'en']))