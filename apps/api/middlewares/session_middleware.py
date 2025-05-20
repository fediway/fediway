from fastapi import Request, Response
from loguru import logger
from uuid import uuid4

from ..modules.sessions import Session
from ..core.session import session_manager, init_session
from config import config


class SessionMiddleware:
    async def __call__(self, request: Request, call_next: callable):
        session = await session_manager.get(request)

        if session is None:
            session = await init_session(request)

        request.state.session = session
        request.state.session_id = session.id

        response = await call_next(request)

        await session_manager.update(session)

        response.set_cookie(
            key=config.session.session_cookie_name,
            value=request.state.session_id,
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=86400,
        )

        return response
