
from celery import Celery
from sqlmodel import select, desc
from datetime import datetime

from app.core.db import get_session
from app.modules.models.status import Status
from ..settings import TOPIC_EXTRACTION_LANGUAGES

def schedule_status_processing(app: Celery):
    session = next(get_session())

    page_size = 10
    min_id = None
    while True:
        q = (
            select(Status)
                .where(Status.last_processed_at == None)
                .where(Status.created_at != None)
                .where(Status.text != '')
                .order_by(Status.id)
                .limit(page_size)
        )

        if min_id is not None:
            q.where(Status.id > min_id)
        
        statuses = session.exec(q).all()

        if len(statuses) == 0:
            break
        
        status_ids = [status.id for status in statuses]
        min_id = min(status_ids)

        session.query(Status).where(Status.id.in_(status_ids)).update({
            'last_processed_at': datetime.utcnow()
        })

        for status in statuses:
            if status.language in TOPIC_EXTRACTION_LANGUAGES:
                print(f"send{status.id}")
                app.send_task(
                    'process-status-topics', 
                    args=[status.id, status.text, status.language, status.created_at],
                    queue='topics',
                )
        
        session.commit()

    session.close()