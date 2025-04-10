
from typing import Annotated, Union
from datetime import datetime
from sqlalchemy import URL
from sqlmodel import Session, create_engine

from config import config

engine = create_engine(config.db.url)

def get_db_session():
    with Session(engine) as session:
        yield session