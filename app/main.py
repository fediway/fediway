from fastapi import FastAPI, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPBearer

from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .api.middlewares.session_middleware import SessionMiddleware
from .api.errors.http_error import http_error_handler
from .api.errors.validation_error import http422_error_handler
from .api.routes.api import router as api_router
from .settings import get_app_settings

def get_application() -> FastAPI:
    settings = get_app_settings()

    settings.configure_logging()

    application = FastAPI(**settings.fastapi_kwargs)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_hosts,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    application.add_middleware(BaseHTTPMiddleware, dispatch=SessionMiddleware())

    application.add_exception_handler(HTTPException, http_error_handler)
    application.add_exception_handler(RequestValidationError, http422_error_handler)

    application.include_router(api_router, prefix=settings.api_prefix)

    return application

app = get_application()