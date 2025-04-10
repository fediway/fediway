
from celery import Celery

from config import config

app = Celery(
    'tasks', 
    broker=str(config.jobs.broker_url),
    backend='rpc://',
)

# pickle supports datetime parsing
app.conf.update(
    task_serializer='pickle',
    accept_content=['pickle', 'json'],
    result_serializer='pickle'
)