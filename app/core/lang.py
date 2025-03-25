
from app.modules.session import Session

def get_languages(session: Session) -> list[str]:
    return list(set([session.get('location', 'EN').lower(), 'en']))