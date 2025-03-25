
from fastapi import Request

from app.modules.session import SessionManager, Session
from app.modules.feed import Feed
from app.settings import settings

from .location import get_location

session_manager = SessionManager(
    maxsize=settings.session_max_size,
    max_age_in_seconds=settings.session_max_age_in_seconds
)

def init_session(request: Request):
    session = Session.from_request(request)

    session['location'] = get_location(session.ipv4_address)

    return session