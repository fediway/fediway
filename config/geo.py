
from .base import BaseConfig

class GeoLocationConfig(BaseConfig):
    ipv4_location_file: str | None = None
    ipv6_location_file: str | None = None