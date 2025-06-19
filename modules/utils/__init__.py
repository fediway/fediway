import logging
import time
from contextlib import contextmanager

from loguru import logger

from .db import *
from .dd import *
from .http import *
from .redis import *


@contextmanager
def duration(message, level=logging.INFO):
    start_time = time.time()
    yield
    end_time = time.time()
    elapsed_time = end_time - start_time

    if callable(message):
        message = message(elapsed_time)

    logger.log(level, message.format(elapsed_time))


def flatten(arr):
    return reduce(operator.add, arr)
