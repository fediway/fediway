
from typing import Annotated, Union
from datetime import datetime

from sqlmodel import Session, create_engine

from app.settings import settings, AppEnvTypes

engine = create_engine(
    str(settings.database_url), 
    echo=settings.app_env == AppEnvTypes.dev
)

def get_db_session():
    with Session(engine) as session:
        yield session