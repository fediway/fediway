from redis import Redis

from config import config

redis = Redis(
    host=config.session.redis_host,
    port=config.session.redis_port,
    db=config.session.redis_name,
    password=config.session.redis_pass,
    decode_responses=True,
)
