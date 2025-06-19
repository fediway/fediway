from redis import Redis
from typing import Callable
import functools


def redis_cache(client: Redis | Callable[[], Redis], key: str, ttl: int = 300):
    is_callable = callable(client)

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*pargs, **kwargs):
            redis_client = client() if is_callable else client

            # Use first argument for cache key
            cache_key = key.format(*pargs, **kwargs)

            try:
                cached = redis_client.get(cache_key)
                if cached:
                    return json.loads(cached.decode())
            except:
                pass

            result = func(*pargs, **kwargs)

            try:
                redis_client.setex(cache_key, ttl, json.dumps(result))
            except:
                pass

            return result

        return wrapper

    return decorator
