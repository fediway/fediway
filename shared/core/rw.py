from contextlib import contextmanager

from sqlmodel import Session, create_engine

from config import config

engine = create_engine(config.risingwave.url)


def get_rw_session():
    with Session(engine) as session:
        yield session


@contextmanager
def rw_session():
    with Session(engine) as session:
        yield session
