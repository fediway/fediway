from redis import ConnectionPool, Redis

from config import config

pool = ConnectionPool(
    host=config.session.redis_host,
    port=config.session.redis_port,
    db=config.session.redis_name,
    password=config.session.redis_pass,
)


def get_redis():
    return Redis(connection_pool=pool)
