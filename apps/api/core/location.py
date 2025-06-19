import os

import maxminddb

from config import config
from shared.core.redis import get_redis
import modules.utils as utils

ipv4_reader: maxminddb.Reader = None
ipv6_reader: maxminddb.Reader = None

if config.geo.ipv4_location_file and os.path.exists(config.geo.ipv4_location_file):
    ipv4_reader = maxminddb.open_database(config.geo.ipv4_location_file)

if config.geo.ipv6_location_file and os.path.exists(config.geo.ipv6_location_file):
    ipv6_reader = maxminddb.open_database(config.geo.ipv6_location_file)


@utils.redis.cache(get_redis, "location:{}", ttl=604800)
def get_location(ipv4_address: str) -> str | None:
    if ipv4_reader is None:
        return

    result = ipv4_reader.get(ipv4_address)

    if result is not None:
        return result.get("country_code")

    return None
