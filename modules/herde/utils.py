from datetime import datetime


def parse_datetime(dt: datetime | int):
    return dt if type(dt) == int else int(dt.timestamp() * 1000)
