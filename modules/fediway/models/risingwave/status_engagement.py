from datetime import datetime

from sqlmodel import Field, SQLModel


class StatusEngagement(SQLModel, table=True):
    __tablename__ = "enriched_status_engagements"

    account_id: int = Field(primary_key=True)
    status_id: int = Field(primary_key=True)
    author_id: int = Field()
    type: str = Field()
    event_time: datetime = Field()
    status_event_time: datetime = Field()
