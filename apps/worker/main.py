from celery import Celery

from config import config

from .config import Config

config.logging.configure_logging()

BEAT_SCHEDULE = {
    # --- queue: sources ---
    "viral-statuses-source": {
        "task": "sources.viral_statuses",
        "schedule": 60,  # every 60 seconds
        "options": {"queue": "sources"},
    },
    # "popular-by-influential-accounts": {
    #     "task": "sources.popular_by_influential_accounts",
    #     "schedule": 60,  # every 60 seconds
    #     "options": {"queue": "sources"},
    # },
    # --- queue: schwarm ---
    "clearn-memgraph": {
        "task": "schwarm.clean_memgraph",
        "schedule": 60 * 5,  # every 5 minutes
        "options": {"queue": "schwarm"},
    },
}


def create_app():
    """Factory function to create Celery app"""
    app = Celery(
        include=[
            "apps.worker.tasks.sources",
            "apps.worker.tasks.schwarm",
        ]
    )

    app.config_from_object(Config)
    app.conf.beat_schedule = BEAT_SCHEDULE

    return app


app = create_app()
