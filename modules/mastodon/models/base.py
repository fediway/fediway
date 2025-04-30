
from sqlalchemy import event
from sqlmodel import SQLModel

class ReadOnlyModel(SQLModel):
    pass

# def block_writes(mapper, connection, target):
#     raise RuntimeError("Write operations are disabled for this model!")

# event.listen(ReadOnlyModel.__tablename__, "before_insert", block_writes)
# event.listen(ReadOnlyModel.__tablename__, "before_update", block_writes)
# event.listen(ReadOnlyModel.__tablename__, "before_delete", block_writes)