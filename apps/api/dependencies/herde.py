
from fastapi import Depends
from neo4j import AsyncSession

from shared.core.herde import driver
from modules.herde import Herde

def get_herde():
    return Herde(driver)