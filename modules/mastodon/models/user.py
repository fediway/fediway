from sqlmodel import Field, Relationship, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int = Field(primary_key=True)
    account_id: int = Field(foreign_key="accounts.id")

    account: "Account" = Relationship(back_populates="user")
