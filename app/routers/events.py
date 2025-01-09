import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..dynamodb_service import save_event, fetch_events_by_email, get_event_by_id
from ..s3_service import create_event_folder, generate_event_presigned_urls

router = APIRouter()


# Request Model for Event Creation
class EventRequest(BaseModel):
    event_name: str
    event_date: str  # Format: YYYY-MM-DD
    phone: str
    email: str  # Photographer's email
    photographer_name: str  # Photographer's name


@router.get("/")
def get_user_events(email: str):
    """
    Fetch all events for a specific user by email.
    """
    try:
        events = fetch_events_by_email(email)  # Call the service method
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching events: {str(e)}")


@router.post("/")
def create_event(request: EventRequest):
    """
    Creates an event, saves details in DynamoDB, and generates pre-signed URLs.

    Args:
        request (EventRequest): The event details from the photographer.

    Returns:
        dict: Information about the created event, pre-signed URLs, and S3 folder.
    """
    try:
        # Generate a unique event ID
        event_id = str(uuid.uuid4())

        # Parse and validate event_date
        try:
            event_date = datetime.strptime(request.event_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

        # Create the event folder in S3
        folder = create_event_folder(request.photographer_name, event_date, request.event_name)

        # Generate pre-signed URLs for uploads
        upload_urls = generate_event_presigned_urls(request.photographer_name, event_date, request.event_name)

        # Define upload statuses
        upload_statuses = {
            "guest_list_upload_status": "Pending Upload",
            "album_upload_status": "Pending Upload",
        }

        # Save event details in DynamoDB
        event_item = {
            "event_id": event_id,
            "created_at": datetime.utcnow().isoformat(),
            "event_name": request.event_name,
            "event_date": str(event_date),
            "photographer_name": request.photographer_name,
            "email": request.email,
            "phone": request.phone,
            "folder": folder,
            "status": "Pending Upload",
            "guest_list": [],  # Placeholder for guest list
            "upload_urls": upload_urls,
            "upload_statuses": upload_statuses,
        }

        save_event(event_item)

        # Return response with event details and upload URLs
        return {
            "event_id": event_id,
            "folder": folder,
            "upload_urls": upload_urls,
            "upload_statuses": upload_statuses,
            "message": "Event created successfully. Share the upload URLs with the photographer.",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating event: {str(e)}")


@router.get("/{event_id}")
def get_event_details(event_id: str):
    """
    Fetch the details of a specific event by event_id.
    """
    try:
        event = get_event_by_id(event_id)  # Call the service function to fetch event details
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        # Directly return the event with the pre-signed URLs stored in DynamoDB
        return event

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching event: {str(e)}")
