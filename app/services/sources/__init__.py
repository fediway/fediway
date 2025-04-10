
from fastapi import Depends
from sqlmodel import Session as DBSession

from modules.fediway.sources import Source

from app.core.db import get_db_session

def get_hot_statuses_in_a_language_source():
    pass

SOURCES = {
    
}

def get_source_provider(source_cls) -> Depends:
    return {
        ''
    }

async def get_sources(source_classes: list[str]) -> list[Source]:
    sources = []

    for source_cls in source_classes:
        source = Depends(get_source_provider(source_cls))
        sources += source if type(source) == list else [source]
        
    return _inject