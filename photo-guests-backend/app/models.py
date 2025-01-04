from pydantic import BaseModel


class Guest(BaseModel):
    name: str
    phone: str
