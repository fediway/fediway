from modules.fediway.sources.follows import TriangularLoopsSource

from shared.core.herde import db


def triangular_loop(account_id: int, limit: int = 10):
    source = TriangularLoopsSource(db, account_id)

    for account_id in source.collect(limit):
        print(account_id)
