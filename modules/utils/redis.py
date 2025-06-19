from redis import Redis


def cache(client: Redis, key: str, ttl: int = 300):
    """
    Simpler version that uses first argument as key suffix
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*pargs, **kwargs):
            # Use first argument for cache key
            cache_key = key.format(*pargs, **kwargs)

            try:
                cached = await redis_client.get(cache_key)
                if cached:
                    return json.loads(cached.decode())
            except:
                pass

            result = await func(*pargs, **kwargs)

            try:
                await redis_client.setex(cache_key, ttl, json.dumps(result))
            except:
                pass

            return result

        return wrapper

    return decorator
