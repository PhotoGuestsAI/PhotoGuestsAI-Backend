import uuid
from fastapi import APIRouter
from ..s3_service import generate_presigned_upload_url

router = APIRouter()

BUCKET_NAME = "photo-guests-events"


@router.get("/{event_id}/submit-guest-url")
def get_guest_submission_url(event_id: str):
    """
    Generate a pre-signed URL for a guest to upload their photo to S3.

    Args:
        event_id (str): The unique identifier for the event.

    Returns:
        dict: Contains the unique guest ID and a pre-signed URL for uploading the photo.
    """
    # Generate a unique guest ID
    guest_id = str(uuid.uuid4())

    # Define the S3 folder and file path
    folder = f"guest-submissions/{event_id}/"
    file_name = f"{guest_id}/photo.jpg"
    key = f"{folder}{file_name}"

    # Generate a pre-signed URL
    upload_url = generate_presigned_upload_url(bucket_name=BUCKET_NAME, key=key, expiration=86400)

    # Return the guest ID and upload URL
    return {
        "guest_id": guest_id,
        "upload_url": upload_url
    }
