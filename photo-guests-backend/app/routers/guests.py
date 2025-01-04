from fastapi import APIRouter
from app.dynamodb_service import add_guest
from app.models import Guest

router = APIRouter()

@router.post("/{event_id}")
def add_guest_to_event(event_id: str, guest: Guest):
    result = add_guest(event_id, guest.name, guest.phone)
    return {"message": "Guest added successfully", "guest": result}
