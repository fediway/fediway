
from fastapi import Request

def get_languages(request: Request) -> list[str]:
    location = request.state.session.get('location', 'EN')

    if location is None:
        return ['en']
    
    return list(set([location.lower(), 'en']))