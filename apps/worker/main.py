from celery import Celery

from config import config

from .config import Config

config.logging.configure_logging()

BEAT_SCHEDULE = {
    # --- queue: sources ---
    "trending-statuses-source": {
        "task": "sources.trending_statuses",
        "schedule": 60,  # every 60 seconds
        "options": {"queue": "sources"},
    },
}


def create_app():
    """Factory function to create Celery app"""
    app = Celery(
        include=[
            "apps.worker.tasks.sources",
        ]
    )

    app.config_from_object(Config)
    app.conf.beat_schedule = BEAT_SCHEDULE

    return app


app = create_app()
