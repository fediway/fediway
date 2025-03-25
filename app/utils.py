


def sql_string(query):
    '''
    Converts a query builder instance into a sql string.
    '''
    from .core.db import engine
    return str(query.compile(engine, compile_kwargs={"literal_binds": True}))
