
from celery import Celery

from app.settings import settings

app = Celery(
    'tasks', 
    broker=str(settings.broker_url),
    backend='rpc://',
)

# pickle supports datetime parsing
app.conf.update(
    task_serializer='pickle',
    accept_content=['pickle', 'json'],
    result_serializer='pickle'
)