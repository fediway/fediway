
from typing import Annotated, Union
from datetime import datetime
from sqlalchemy import URL
from sqlmodel import Session, create_engine
from contextlib import contextmanager

from config import config

engine = create_engine(config.db.rw_url)

def get_rw_session():
    with Session(engine) as session:
        yield session

@contextmanager
def rw_session():
    with Session(engine) as session:
        yield session 