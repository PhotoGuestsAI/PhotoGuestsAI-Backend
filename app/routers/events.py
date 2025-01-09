from datetime import date
from fastapi import APIRouter
from pydantic import BaseModel
from ..dynamodb_service import save_event
from ..s3_service import create_event_folder, generate_event_presigned_urls
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
    """
    Creates an event, saves details in DynamoDB, and generates pre-signed URLs.

    Args:
        request (EventRequest): The event details from the photographer.

    Returns:
        dict: Information about the created event, pre-signed URLs, and S3 folder.
    """
    event_id = str(uuid.uuid4())  # Generate a unique event ID

    # Create the event folder in S3
    folder = create_event_folder(request.event_date, event_id)

    # Generate pre-signed URLs for uploading the guest list and album
    upload_urls = generate_event_presigned_urls(request.event_date, event_id)

    # Save event details in DynamoDB
    save_event(
        event_id=event_id,
        event_name=request.event_name,
        event_date=str(request.event_date),
        photographer_name=request.photographer_name,
        email=request.email,
        phone=request.phone,
        upload_urls=upload_urls,
        folder=folder
    )

    # Return event details along with pre-signed URLs
    return {
        "event_id": event_id,
        "folder": folder,
        "upload_urls": upload_urls,
        "message": "Event created successfully. Share the upload URLs with the photographer."
    }
