
from fastapi import Request

from app.modules.sessions import SessionManager, Session
from app.modules.feed import Feed
from config import config

from .location import get_location

session_manager = SessionManager(
    maxsize=config.session.session_max_size,
    max_age_in_seconds=config.session.session_max_age_in_seconds
)

def init_session(request: Request):
    session = Session.from_request(request)

    session['location'] = get_location(session.ipv4_address)

    return session