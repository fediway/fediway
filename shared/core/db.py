from contextlib import contextmanager

from sqlmodel import Session, create_engine

from config import config

engine = create_engine(config.db.url)


def get_db_session():
    with Session(engine) as session:
        yield session


@contextmanager
def db_session():
    with Session(engine) as session:
        yield session


def get_long_living_db_session():
    return Session(engine)
