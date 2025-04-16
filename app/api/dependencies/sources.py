
from fastapi import Depends, Request
from sqlmodel import Session as DBSession
from neo4j import AsyncSession
from datetime import timedelta

from modules.fediway.sources import Source
from modules.fediway.sources.herde import Herde, TrendingStatusesByInfluentialUsers
from app.core.herde import driver
from app.core.db import get_long_living_db_session
from app.modules.sources import (
    HotStatusesByLanguage, 
    NewStatusesByLanguage,
)

from config import config

from .lang import get_languages

def get_hot_statuses_by_language_source(
    languages: list[str] = Depends(get_languages), 
    db: DBSession = Depends(get_long_living_db_session)) -> Source:

    return [HotStatusesByLanguage(
        lang, 
        db=db, 
        max_age=timedelta(days=config.fediway.feed_max_age_in_days)
    ) for lang in languages]

def get_new_statuses_by_language_source(
    languages: list[str] = Depends(get_languages), 
    db: DBSession = Depends(get_long_living_db_session)) -> list[Source]:

    return [NewStatusesByLanguage(
        lang, 
        db=db,
        max_age=timedelta(days=config.fediway.feed_max_age_in_days)
    ) for lang in languages]

def get_trending_statuses_by_influential_accounts_source(
    languages: list[str] = Depends(get_languages)):

    return [TrendingStatusesByInfluentialUsers(driver, lang) for lang in languages]