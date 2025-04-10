
from fastapi import Depends, Request
from sqlmodel import Session as DBSession

from modules.fediway.sources import Source
from app.core.db import get_db_session
from app.modules.sources import (
    NewStatuses, 
    NewStatusesByLanguage
)

from .lang import get_languages

def get_new_statuses_by_language_source(
    languages: list[str] = Depends(get_languages), 
    db: DBSession = Depends(get_db_session)) -> Source:

    return [NewStatusesByLanguage(lang, db=db) for lang in languages]