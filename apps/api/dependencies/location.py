from fastapi import Request

from apps.api.core.location import get_location as _get_location


def get_location(request: Request) -> str | None:
    return _get_location(request.ipv4_address)
