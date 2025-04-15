
from fastapi import Depends
from neo4j import AsyncSession

from app.core.herde import get_herde_session
from modules.fediway.sources.herde import Herde

def get_herde(graph: AsyncSession = Depends(get_herde_session)):
    return Herde(graph)