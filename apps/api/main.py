from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from config import config

from .errors.http_error import http_error_handler
from .errors.validation_error import http422_error_handler
from .middlewares.logging_middleware import RequestLoggingMiddleware
from .middlewares.oauth_middleware import OAuthMiddleware
from .routes.api import router as api_router


def get_application() -> FastAPI:
    config.logging.configure_logging()

    application = FastAPI(**config.fastapi_kwargs)

    application.add_middleware(RequestLoggingMiddleware)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors.allow_origins,
        allow_credentials=config.cors.allow_credentials,
        expose_headers=["link"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.add_middleware(BaseHTTPMiddleware, dispatch=OAuthMiddleware())

    application.add_exception_handler(HTTPException, http_error_handler)
    application.add_exception_handler(RequestValidationError, http422_error_handler)

    application.include_router(api_router, prefix=config.api.api_prefix)

    return application


app = get_application()
