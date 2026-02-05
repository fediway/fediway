from redis import ConnectionPool, Redis

from config import config

pool = ConnectionPool(
    host=config.redis.redis_host,
    port=config.redis.redis_port,
    db=config.redis.redis_name,
    password=config.redis.redis_pass,
    socket_timeout=config.redis.redis_socket_timeout,
    socket_connect_timeout=config.redis.redis_socket_connect_timeout,
)


def get_redis():
    return Redis(connection_pool=pool)
