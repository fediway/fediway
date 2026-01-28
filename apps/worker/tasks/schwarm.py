from loguru import logger

import modules.utils as utils
from config import config
from modules.schwarm import Schwarm
from shared.core.schwarm import driver

from ..main import app


@app.task(name="schwarm.clean_memgraph", queue="schwarm")
def clean_memgraph():
    schwarm = Schwarm(driver)

    logger.info("Purging old statuses...")
    with utils.duration("Purged old statuses in {:.3f} seconds"):
        schwarm.purge_old_statuses(config.fediway.schwarm_max_status_age)
