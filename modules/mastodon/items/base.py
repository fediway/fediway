from pydantic import BaseModel


class Item(BaseModel):
    class Config:
        extra = "ignore"
        use_enum_values = True
