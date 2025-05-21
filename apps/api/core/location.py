import os

import maxminddb

from config import config

ipv4_reader: maxminddb.Reader = None
ipv6_reader: maxminddb.Reader = None

if config.geo.ipv4_location_file and os.path.exists(config.geo.ipv4_location_file):
    ipv4_reader = maxminddb.open_database(config.geo.ipv4_location_file)

if config.geo.ipv6_location_file and os.path.exists(config.geo.ipv6_location_file):
    ipv6_reader = maxminddb.open_database(config.geo.ipv6_location_file)


def get_location(ipv4_address: str) -> str | None:
    if ipv4_reader is None:
        return

    result = ipv4_reader.get(ipv4_address)

    if result is not None:
        return result.get("country_code")

    return None
