import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pydantic import BaseModel
from starlette.responses import JSONResponse

from .auth import get_current_user

# Local imports
from ..dynamodb_service import save_event, fetch_events_by_email, get_event_by_id, update_event_status
from ..enums.event_status import EventStatus
from ..s3_service import create_event_folder, upload_file_to_s3, \
    append_to_guest_list_in_s3

router = APIRouter()

# Constants
ALBUM_SUBFOLDER = "album/"
BUCKET_NAME = "photo-guests-events"


# Request Model for Event Creation
class EventRequest(BaseModel):
    event_name: str
    event_date: str  # Format: YYYY-MM-DD
    phone: str
    email: str  # Photographer's email
    photographer_name: str  # Photographer's name


# Full Event Model
class Event(BaseModel):
    event_id: str
    event_name: str
    event_date: str
    status: str
    photographer_name: str
    email: str
    phone: str
    folder: str


# Smaller Event Model (for listing events)
class EventSummary(BaseModel):
    event_id: str
    event_name: str
    event_date: str
    status: str
    email: str


def raise_http_exception(status_code: int, detail: str):
    """
    Helper function to raise HTTPException.
    """
    raise HTTPException(status_code=status_code, detail=detail)


@router.get("/", response_model=List[EventSummary])
def get_user_events(current_user: str = Depends(get_current_user)):
    """
    Fetch all events for the logged-in user based on the token.
    """
    try:
        # Use the email of the authenticated user
        events = fetch_events_by_email(current_user)

        # Map events to EventSummary format
        return [
            EventSummary(
                event_id=event["event_id"],
                event_name=event["event_name"],
                event_date=event["event_date"],
                status=event["status"],
                email=event["email"],
            )
            for event in events
        ]
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
            raise_http_exception(400, "Invalid date format. Use YYYY-MM-DD.")

        # Create the event folder in S3
        folder = create_event_folder(request.photographer_name, event_date, request.event_name, event_id)

        # Save event details in DynamoDB with separate upload URLs and statuses
        event_item = {
            "event_id": event_id,
            "created_at": datetime.utcnow().isoformat(),
            "event_name": request.event_name,
            "event_date": str(event_date),
            "photographer_name": request.photographer_name,
            "email": request.email,
            "phone": request.phone,
            "folder": folder,
            "status": EventStatus.PENDING_UPLOAD,
        }

        save_event(event_item)

        return {
            "event_id": event_id,
            "folder": folder,
            "message": "Event created successfully. Share the upload URLs with the photographer.",
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
            raise_http_exception(404, "Event not found")

        # Authorization check: ensure the logged-in user is the event creator
        if event["email"] != current_user:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to access this event"
            )

        # Return the event summary
        event_summary = {
            "event_id": event["event_id"],
            "event_name": event["event_name"],
            "event_date": event["event_date"],
            "status": event["status"],
            "email": event["email"],
        }

        return EventSummary(**event_summary)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching event: {str(e)}")


@router.post("/{event_id}/upload-event-album")
async def upload_event_album(event_id: str, album: UploadFile = File(...)):
    """
    Handle the upload of album ZIP file and save it to S3 under the event's folder.

    Args:
        event_id (str): The event ID for the album.
        album (UploadFile): The album zip file.

    Returns:
        dict: Success message if the file was uploaded successfully.
    """
    try:
        # Fetch the event to get the folder path
        event = get_event_by_id(event_id)
        if not event:
            raise_http_exception(404, "Event not found")

        # Define the S3 key (path) for the album file
        s3_key = f"{event['folder']}{ALBUM_SUBFOLDER}{album.filename}"

        # Upload the album file to S3 using the helper function
        upload_success = upload_file_to_s3(album.file, s3_key, album.content_type)

        if upload_success:
            # Update the event status to reflect the album upload status
            update_event_status(event_id, EventStatus.ALBUM_UPLOADED)
            return JSONResponse(content={"message": "Album uploaded successfully!"}, status_code=200)
        else:
            raise HTTPException(status_code=500, detail="Failed to upload the album to S3")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


@router.post("/{event_id}/submit-guest")
async def submit_guest(
        event_id: str,
        name: str = Form(...),
        phone: str = Form(...),
        photo: UploadFile = File(...)
):
    """ Handle the submission of a guest's details (name, phone, photo) and upload it to S3. """
    try:
        # Fetch the event to get the folder path
        event = get_event_by_id(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        # Define the S3 key for the guest's photo
        s3_key = f"{event['folder']}guest-submissions/{name}_{uuid.uuid4()}.jpg"

        # Upload the guest's photo to S3
        upload_success = upload_file_to_s3(photo.file, s3_key, photo.content_type)

        if not upload_success:
            raise HTTPException(status_code=500, detail="Failed to upload the photo to S3")

        # Prepare guest submission data (name, phone, photo URL)
        guest_submission = {
            "name": name,
            "phone": phone,
            "photo_url": f"https://{BUCKET_NAME}.s3.amazonaws.com/{s3_key}",
        }

        # S3 key for guest list
        guest_file_key = f"{event['folder']}guest-submissions/guest_list.json"

        # Append the new guest to the S3 file
        append_to_guest_list_in_s3(guest_file_key, guest_submission)

        return {"message": "Guest submitted successfully!"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting guest: {str(e)}")
