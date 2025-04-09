
from fastapi import Request
import maxminddb
import os

from ..settings import settings

ipv4_reader: maxminddb.Reader = None
ipv6_reader: maxminddb.Reader = None

if settings.ipv4_location_file and os.path.exists(settings.ipv4_location_file):
    ipv4_reader = maxminddb.open_database(settings.ipv4_location_file)

if settings.ipv6_location_file and os.path.exists(settings.ipv6_location_file):
    ipv6_reader = maxminddb.open_database(settings.ipv6_location_file)

def estimate_user_agent_location(user_agent: str):
    return None

def get_location(ipv4_address: str, user_agent = None, fallback = 'DE') -> str | None:
    if ipv4_reader is None:
        return
        
    result = ipv4_reader.get(ipv4_address)

    if result is not None:
        return result.get('country_code')

    location = None
    
    if user_agent:
        location = estimate_user_agent_location(user_agent)
    
    return location or fallback