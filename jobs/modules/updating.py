
from sqlmodel import select, desc, exists, text
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from app.core.db import get_session
from app.modules.models.status import Status
from app.modules.models.topic import Topic, StatusTopic

def update_status_topics(status_id: int, 
                         topics: dict, 
                         language: str, 
                         created_at: str):
    session = next(get_session())

    for name, display_name in topics.items():
        topic_id = session.scalar(select(Topic.id).where(
            func.lower(Topic.name) == name
        ))

        status_topic_exists = False
        if not topic_id:
            query = text(f"""
            INSERT INTO {Topic.__tablename__} (name, display_name, language, created_at, updated_at)
            VALUES (:name, :display_name, :language, :created_at, :updated_at)
            ON CONFLICT (name) DO NOTHING
            RETURNING id
            """)
            result = session.execute(query, {
                'name': name.lower(), 
                'display_name': display_name, 
                'language': language,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
            })
            session.commit()
            topic_id = result.fetchone()[0]
        else:
            status_topic_exists == session.scalar(exists().where(
                StatusTopic.topic_id == topic_id,
                StatusTopic.status_id == status_id,
            ).select())

        # print(f"created_at{type(created_at)}")
        
        if not status_topic_exists:
            query = text(f"""
            INSERT INTO {StatusTopic.__tablename__} (topic_id, status_id, created_at)
            VALUES (:topic_id, :status_id, :created_at)
            ON CONFLICT (topic_id, status_id) DO NOTHING
            """)
            
            session.execute(query, {
                'topic_id': topic_id,
                'status_id': status_id,
                'created_at': created_at,
            })

            try:
                session.commit()
            except IntegrityError:
                continue

    session.close()
