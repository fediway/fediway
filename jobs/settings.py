
from celery.schedules import crontab

SCHEDULE_STATUS_LANGUAGES_EVERY_N_SECONDS = 5
TOPIC_EXTRACTION_LANGUAGES = frozenset([
    'en'
])

MAX_RETRIES = 10

QUEUE_GROUPS = {
    'local': [
        'schedule-status-language-check',
    ],
    'remote': [
        'process-status-language',
    ],
}