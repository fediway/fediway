from contextlib import contextmanager
from uuid import uuid4

from sqlmodel import Session, text
from sqlmodel.sql._expression_select_cls import Select, SelectOfScalar


def compile_sql(query, engine):
    """
    Converts a query builder instance into a sql string.
    """
    return str(query.compile(engine, compile_kwargs={"literal_binds": True}))


@contextmanager
def batch_cursor(db: Session, query: Select | SelectOfScalar):
    cursor_name = f"batch_cursor_{uuid4().hex}"
    sql = compile_sql(query)

    try:
        # Declare cursor WITH HOLD to keep it beyond transaction
        db.execute(text(f"DECLARE {cursor_name} CURSOR WITH HOLD FOR {sql}"))
        yield cursor_name
    finally:
        # Ensure cursor cleanup even if errors occur
        db.execute(text(f"CLOSE {cursor_name}"))


def iter_db_batches(db: Session, query: Select | SelectOfScalar, batch_size: int = 100):
    batch = []
    result = db.exec(query)
    if not isinstance(query, SelectOfScalar):
        result = result.mappings()
    for row in result.yield_per(batch_size):
        batch.append(row)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch
    return

    with batch_cursor(db, query) as cursor:
        while True:
            rows = (
                db.exec(text(f"FETCH FORWARD {batch_size} FROM {cursor}"))
                .mappings()
                .fetchall()
            )
            db.commit()
            if not rows:
                break
            yield rows
