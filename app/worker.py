
from celery import Celery
from celery.schedules import crontab
from loguru import logger

import app.utils as utils
from .core.herde import driver
from config import config

config.logging.configure_logging()

app = Celery(
    broker=config.tasks.worker_url
)

@app.on_after_configure.connect
def setup_periodic_tasks(sender: Celery, **kwargs):
    sender.add_periodic_task(config.tasks.compute_account_ranks_every_n_seconds, compute_account_ranks)
    sender.add_periodic_task(config.tasks.compute_tag_ranks_every_n_seconds, compute_tag_ranks)

@app.task(name="herde.compute_account_ranks")
def compute_account_ranks():
    from modules.fediway.sources.herde import Herde

    herde = Herde(driver)

    logger.info("Start computing account ranks...")
    with utils.duration("Computed account ranks in {:.3f} seconds"):
        herde.compute_account_rank()

@app.task(name="herde.compute_tag_ranks")
def compute_tag_ranks():
    from modules.fediway.sources.herde import Herde

    herde = Herde(driver)

    logger.info("Start computing tag ranks...")
    with utils.duration("Computed tag ranks in {:.3f} seconds"):
        herde.compute_tag_rank()
    