from fastapi import APIRouter
from app.dynamodb_service import update_guest_list_in_dynamodb
from app.s3_service import generate_upload_url
import uuid

router = APIRouter()


@router.get("/{event_id}/submit-guest-url")
def get_guest_submission_url(event_id: str):
    guest_id = str(uuid.uuid4())
    folder = f"guest-submissions/{event_id}/"
    file_name = f"{guest_id}/photo.jpg"
    upload_url = generate_upload_url(folder, file_name)
    return {"guest_id": guest_id, "upload_url": upload_url}
