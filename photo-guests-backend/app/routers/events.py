from datetime import date
from fastapi import APIRouter
from pydantic import BaseModel
from app.dynamodb_service import save_event
from app.s3_service import create_event_folder, generate_upload_url
import uuid

router = APIRouter()


class EventRequest(BaseModel):
    event_name: str
    event_date: date
    photographer_name: str
    email: str
    phone: str


@router.post("/")
def create_event(request: EventRequest):
    event_id = str(uuid.uuid4())
    folder = create_event_folder(request.event_date, event_id)
    save_event(
        event_id=event_id,
        event_name=request.event_name,
        event_date=str(request.event_date),
        photographer_name=request.photographer_name,
        email=request.email,
        phone=request.phone,
        folder=folder
    )
    return {
        "event_id": event_id,
        "folder": folder,
        "message": "Event created successfully. Share this folder path with the photographer."
    }


@router.get("/{event_id}/upload-guest-list-url")
def get_guest_list_upload_url(event_id: str):
    folder = f"guest-submissions/{event_id}/"
    upload_url = generate_upload_url(folder, "guest_list.csv")
    return {"message": "Use this URL to upload the guest list CSV.", "upload_url": upload_url}
