from fastapi import APIRouter
from app.dynamodb_service import add_guest, update_guest_list
from app.s3_service import generate_guest_submission_url
from app.models import Guest
import uuid

router = APIRouter()


@router.post("/{event_id}")
def add_guest_to_event(event_id: str, guest: Guest):
    """
    Adds a guest's details to the event's guest list in the database.

    Args:
        event_id (str): The unique identifier for the event.
        guest (Guest): The guest details (name, phone).

    Returns:
        dict: A message and the added guest's details.
    """
    # Add the guest details to DynamoDB
    result = add_guest(event_id, guest.name, guest.phone)
    return {"message": "Guest added successfully", "guest": result}


@router.post("/{event_id}/upload-guest-list")
def upload_guest_list(event_id: str, guest_list: list[Guest]):
    """
    Updates the guest list for an event in the database.

    Args:
        event_id (str): The unique identifier for the event.
        guest_list (list[Guest]): A list of guest details.

    Returns:
        dict: A success message.
    """
    # Convert the list of Guest objects into dictionaries
    formatted_guest_list = [{"name": g.name, "phone": g.phone} for g in guest_list]

    # Update the guest list in the database
    update_guest_list(event_id, formatted_guest_list)

    return {"message": "Guest list uploaded successfully"}


@router.get("/{event_id}/submit-guest-url")
def get_guest_submission_url(event_id: str):
    """
    Generates a pre-signed URL for a guest to upload their photo to S3.

    Args:
        event_id (str): The unique identifier for the event.

    Returns:
        dict: A dictionary containing the guest ID and the pre-signed URL.
    """
    guest_id = str(uuid.uuid4())  # Generate a unique ID for the guest
    upload_url = generate_guest_submission_url(event_id, guest_id)  # Generate the pre-signed URL
    return {"guest_id": guest_id, "upload_url": upload_url}
