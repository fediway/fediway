from config import config


class Config:
    # Broker settings
    BROKER_URL = config.tasks.worker_url

    # Task settings
    TASK_SERIALIZER = "json"
    RESULT_SERIALIZER = "json"
    ACCEPT_CONTENT = ["json"]
    TIMEZONE = "UTC"
    ENABLE_UTC = True

    # Worker settings
    WORKER_PREFETCH_MULTIPLIER = 1
    WORKER_MAX_TASKS_PER_CHILD = 1000

    # Queue routing
    TASK_ROUTES = {
        "apps.worker.tasks.sources.*": {"queue": "sources"},
    }
