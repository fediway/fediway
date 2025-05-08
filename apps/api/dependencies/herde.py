
from fastapi import Depends
from neo4j import AsyncSession

from shared.core.schwarm import driver
from modules.schwarm import Schwarm

def get_schwarm():
    return Schwarm(driver)