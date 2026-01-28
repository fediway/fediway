from sqlmodel import Field, SQLModel


class RecommendationSource(SQLModel, table=True):
    __tablename__ = "recommendation_sources"

    recommendation_id: str = Field(primary_key=True)
    sourcing_run_id: str = Field(primary_key=True)
