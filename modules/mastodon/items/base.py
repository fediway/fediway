from pydantic import BaseModel, ConfigDict


class Item(BaseModel):
    model_config = ConfigDict(extra="ignore", use_enum_values=True)
