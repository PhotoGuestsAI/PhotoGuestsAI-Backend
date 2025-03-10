import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pydantic import BaseModel

from .auth import get_current_user
from ..dynamodb_service import save_event, fetch_events_by_email, get_event_by_id
# from ..keyspaces_service import save_event, fetch_events_by_email, get_event_by_id
from ..enums.event_status import EventStatus
from ..s3_service import create_event_folder, upload_file_to_s3, append_to_guest_list_in_s3

router = APIRouter()


# Request Model for Event Creation
class EventRequest(BaseModel):
    name: str
    date: str  # Format: YYYY-MM-DD
    phone: str
    email: str
    username: str
    num_guests: int
    num_images: int
    price: int


# Smaller Event Model (for listing events)
class EventSummary(BaseModel):
    event_id: str
    name: str
    date: str
    status: str
    email: str


@router.get("/", response_model=List[EventSummary])
def get_user_events(current_user: str = Depends(get_current_user)):
    """
    Fetch all events for the logged-in user based on the token.
    """
    try:
        events = fetch_events_by_email(current_user)

        return [
            EventSummary(
                event_id=event["event_id"],
                name=event["name"],
                date=event["date"],
                status=event["status"],
                email=event["email"],
            )
            for event in events
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching events: {str(e)}")


@router.post("/")
def create_event(request: EventRequest, current_user: str = Depends(get_current_user)):
    """
    Creates an event & saves details in DynamoDB.

    Args:
        request (EventRequest): The event details from the photographer.

    Returns:
        dict: A success message.
    """
    try:
        event_id = str(uuid.uuid4())
        try:
            event_date = datetime.strptime(request.date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD.")

        create_event_folder(request.username, str(event_date), request.name, event_id)

        event_item = {
            "event_id": event_id,
            "created_at": datetime.utcnow().isoformat(),
            "name": request.name,
            "date": str(event_date),
            "username": request.username,
            "email": request.email,
            "phone": request.phone,
            "status": EventStatus.PENDING_UPLOAD,
            "num_guests": request.num_guests,
            "num_images": request.num_images,
            "price": request.price
        }

        save_event(event_item)

        return {
            "message": "Event created successfully.",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating event: {str(e)}")


@router.get("/{event_id}", response_model=EventSummary)
async def get_event_details(event_id: str, current_user: str = Depends(get_current_user)):
    """
    Fetch the details of a specific event by event_id and return only a summarized version.
    """
    try:
        event = get_event_by_id(event_id)
        if not event:
            raise HTTPException(404, "Event not found")

        # Authorization check: ensure the logged-in user is the event creator
        if event["email"] != current_user:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to access this event"
            )

        event_summary = {
            "event_id": event["event_id"],
            "name": event["name"],
            "date": event["date"],
            "status": event["status"],
            "email": event["email"],
        }

        return EventSummary(**event_summary)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching event: {str(e)}")


def generate_event_folder_path(event: dict) -> str:
    """
    Generate the folder path for an event based on the event details.

    Args:
        event (dict): A dictionary containing event details such as 'username', 'date', 'name', and 'id'.

    Returns:
        str: The folder path for the event.
    """
    if not all(key in event for key in ["username", "date", "name", "event_id"]):
        raise ValueError("Event details are incomplete. 'username', 'date', 'name', and 'event_id' are required.")

    return f"{event['username']}/{event['date']}/{event['name']}/{event['event_id']}/"
