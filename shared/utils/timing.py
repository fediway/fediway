import logging
import time
from contextlib import contextmanager

from loguru import logger


@contextmanager
def duration(message, level=logging.INFO):
    start_time = time.time()
    yield
    end_time = time.time()
    elapsed_time = end_time - start_time

    if callable(message):
        message = message(elapsed_time)

    logger.log(level, message.format(elapsed_time))
