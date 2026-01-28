import logging
import sys
from types import FrameType
from typing import cast

from loguru import logger

from .base import BaseConfig


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        """
        Map the record's level to Loguru's level and log the message.
        """
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:  # noqa: WPS609
            frame = cast(FrameType, frame.f_back)
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


class LoggingConfig(BaseConfig):
    logging_level: int = logging.INFO
    loggers: tuple[str, str] = ("uvicorn.asgi", "uvicorn.access")

    def configure_logging(self) -> None:
        """
        Configure the logging system to route messages from the standard library into the desired logger.
        """
        logging.getLogger().handlers = [InterceptHandler()]

        for logger_name in self.loggers:
            target_logger = logging.getLogger(logger_name)
            target_logger.handlers = [InterceptHandler(level=self.logging_level)]

        logger.configure(handlers=[{"sink": sys.stderr, "level": self.logging_level}])
