
from fastapi import Request
from loguru import logger

from app.modules.sessions import SessionManager, Session
from app.modules.feed import Feed
from config import config
import app.utils as utils

from .location import get_location

session_manager = SessionManager(
    redis_host=config.session.redis_host,
    redis_port=config.session.redis_port,
    redis_name=config.session.redis_name,
    redis_pass=config.session.redis_pass,
    ttl=config.session.session_ttl
)

async def init_session(request: Request):
    session = Session.from_request(request)
    logger.debug(f"Initialized new session with id {session.id}.")

    with utils.duration("Retrieved request location in {:.3f} seconds"):
        session['location'] = get_location(session.ipv4_address)

    return session