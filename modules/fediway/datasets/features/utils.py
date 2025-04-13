
from sqlalchemy.orm.util import _ORMJoin

def is_joined(query, entity):
    for j in query.froms:
        if not isinstance(j, _ORMJoin):
            continue
        if str(j.right) == entity.__tablename__:
            return True
    return False