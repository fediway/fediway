
from loguru import logger
from datetime import datetime

from app.modules.models.status import Status

from .settings import SCHEDULE_STATUS_LANGUAGES_EVERY_N_SECONDS, MAX_RETRIES, TOPIC_EXTRACTION_LANGUAGES
from .app import app

def reschedule_task(self, func, queue, countdown):
    try:
        func(app)
    except Exception as e:
        logger.error(e)
        raise self.retry(exc=e, queue=queue, countdown=countdown)
    finally:
        self.apply_async(queue=queue, countdown=countdown)

@app.task(name='schedule-status-processing')
def schedule_status_processing():
    from .modules.scheduling import schedule_status_processing

    schedule_status_processing(app)
    # reschedule_task(
    #     self, 
    #     func=schedule_status_languages, 
    #     queue='local', 
    #     countdown=SCHEDULE_STATUS_LANGUAGES_EVERY_N_SECONDS
    # )

@app.task(name='update-status-topics')
def update_status_topics_task(status_id: int, topics: object, language:str, created_at: str):
    from .modules.updating import update_status_topics

    update_status_topics(status_id, topics, language, created_at)

@app.task(name='process-status-topics')
def process_status_topics(status_id: int, text: str, language: str, created_at: datetime):
    from .modules.topic_extraction import get_topics
    from .utils import strip_html

    if language not in TOPIC_EXTRACTION_LANGUAGES:
        return

    topics = get_topics(strip_html(text), language)

    print(topics)

    if len(topics) == 0:
        return
    
    app.send_task(
        'update-status-topics', 
        args=[status_id, topics, language, created_at],
        queue='local'
    )

# start first tasks
schedule_status_processing.apply_async(queue='local')