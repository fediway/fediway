from celery import Celery
from loguru import logger

import modules.utils as utils
from shared.core.schwarm import driver
from config import config

config.logging.configure_logging()

app = Celery(broker=config.tasks.worker_url)


@app.on_after_configure.connect
def setup_periodic_tasks(sender: Celery, **kwargs):
    sender.add_periodic_task(
        config.tasks.compute_account_ranks_every_n_seconds, compute_account_ranks
    )
    sender.add_periodic_task(
        config.tasks.compute_tag_ranks_every_n_seconds, compute_tag_ranks
    )
    sender.add_periodic_task(
        config.tasks.clean_memgraph_every_n_seconds, clean_memgraph
    )


@app.task(name="schwarm.compute_account_ranks")
def compute_account_ranks():
    from modules.fediway.sources.schwarm import Schwarm

    schwarm = Schwarm(driver)

    logger.info("Start computing account ranks...")
    with utils.duration("Computed account ranks in {:.3f} seconds"):
        schwarm.compute_account_rank()


@app.task(name="schwarm.compute_tag_ranks")
def compute_tag_ranks():
    from modules.fediway.sources.schwarm import Schwarm

    schwarm = Schwarm(driver)

    logger.info("Start computing tag ranks...")
    with utils.duration("Computed tag ranks in {:.3f} seconds"):
        schwarm.compute_tag_rank()


@app.task(name="schwarm.clean_memgraph")
def clean_memgraph():
    from modules.fediway.sources.schwarm import Schwarm

    schwarm = Schwarm(driver)

    logger.info("Purging old statuses...")
    with utils.duration("Purged old statuses in {:.3f} seconds"):
        schwarm.purge_old_statuses(config.fediway.schwarm_max_status_age)
