
from fastapi import Request, Response
from uuid import uuid4

from app.modules.sessions import Session
from app.modules.feed import Feed
from app.core.sessions import session_manager, init_session
from app.settings import settings

class SessionMiddleware():

    async def __call__(self, request: Request, call_next: callable):
        session_id = request.cookies.get(settings.session_cookie_name)
        session = None

        if session_id is not None:
            session = session_manager.get_session(session_id)

        if session is None:
            session = init_session(request)
            session_manager.create_session(session.id, session)

        request.state.session = session
        request.state.session_id = session.id

        response = await call_next(request)

        session_manager.update(session.id, session)

        response.set_cookie(
            key=settings.session_cookie_name,
            value=request.state.session_id,
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=86400
        )

        return response