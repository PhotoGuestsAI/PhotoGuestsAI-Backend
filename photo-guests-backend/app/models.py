from pydantic import BaseModel

class Event(BaseModel):
    event_name: str
    max_guests: int
    max_photos: int

class Guest(BaseModel):
    name: str
    phone: str
