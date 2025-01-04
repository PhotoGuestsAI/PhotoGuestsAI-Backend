from datetime import date
from fastapi import APIRouter
from pydantic import BaseModel

from app.dynamodb_service import save_event
from app.s3_service import create_event_folder
import uuid

router = APIRouter()


# Request model for creating an event
class EventRequest(BaseModel):
    event_name: str
    event_date: date  # Ensure the date is validated
    photographer_name: str
    email: str
    phone: str  # Photographer's phone number


@router.post("/")
def create_event(request: EventRequest):
    """
    Creates an event, saves details in DynamoDB, and creates an S3 folder structure.

    Args:
        request (EventRequest): The event details from the photographer.

    Returns:
        dict: Information about the created event and S3 folder.
    """
    event_id = str(uuid.uuid4())  # Generate a unique event ID

    # Create the event folder in S3
    folder = create_event_folder(request.event_date, request.event_name)

    # Save event details in DynamoDB
    save_event(
        event_id=event_id,
        event_name=request.event_name,
        event_date=str(request.event_date),
        photographer_name=request.photographer_name,
        email=request.email,
        phone=request.phone,
        upload_url=None,  # No upload URL at this step
        folder=folder,
    )

    # Return the event ID and folder path to the photographer
    return {
        "event_id": event_id,
        "folder": folder,
        "message": "Event folder created successfully. Share this event ID with the photographer.",
    }
