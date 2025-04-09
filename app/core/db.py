
from typing import Annotated, Union
from datetime import datetime
from sqlalchemy import URL
from sqlmodel import Session, create_engine

from app.settings import settings, AppEnvTypes

engine = create_engine(URL.create(
    "postgresql",
    username=settings.db_user,
    password=settings.db_pass,
    host=settings.db_host,
    database=settings.db_name,
))

def get_db_session():
    with Session(engine) as session:
        yield session