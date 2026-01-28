import json
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


def get_class_path(obj):
    cls = obj.__class__
    return f"{cls.__module__}.{cls.__qualname__}"


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            if np.isnan(obj):
                return None
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif type(obj) == tuple:
            return list(obj)
        else:
            return super(JSONEncoder, self).default(obj)
