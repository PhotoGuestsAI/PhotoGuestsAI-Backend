from fastapi import APIRouter
from app.s3_service import create_event_folder, generate_presigned_url
from app.models import Event
import uuid

router = APIRouter()

@router.post("/")
def create_event(event: Event):
    event_id = str(uuid.uuid4())
    folder = create_event_folder(event_id)
    upload_url = generate_presigned_url(f"{folder}photo.jpg")
    return {"event_id": event_id, "upload_url": upload_url}
