
from typing import Annotated, Union
from datetime import datetime
from sqlalchemy import URL
from sqlmodel import Session, create_engine

from app.settings import settings, AppEnvTypes

engine = create_engine(settings.get_database_url())

def get_db_session():
    with Session(engine) as session:
        yield session