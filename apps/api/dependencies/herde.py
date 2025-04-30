
from fastapi import Depends
from neo4j import AsyncSession

from app.core.herde import driver
from modules.fediway.sources.herde import Herde

def get_herde():
    return Herde(driver)