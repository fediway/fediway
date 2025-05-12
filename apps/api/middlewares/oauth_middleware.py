
from fastapi import Request, Response
from sqlmodel import select

from shared.core.db import db_session
from modules.mastodon.models import AccessToken, User, Account

class OAuthMiddleware():
    async def __call__(self, request: Request, call_next: callable):
        auth_header: str = request.headers.get("Authorization") or ""
        scheme, _, token = auth_header.partition(" ")

        if scheme.lower() != "bearer" or not token:
            return await call_next(request)

        with db_session() as db:
            query = (
                select(AccessToken)
                .where(AccessToken.token == token)
                .where(AccessToken.revoked_at.is_(None))
            )

            token = db.exec(query).one_or_none()

        if token is None:
            return await call_next(request)

        request.state.token = token
        
        with db_session() as db:
            query = (
                select(Account)
                .join(User, (User.account_id == Account.id) & (User.id == token.resource_owner_id))
            )
            
            account = db.exec(query).one_or_none()

        if account:
            request.state.account = account
        
        return await call_next(request)
