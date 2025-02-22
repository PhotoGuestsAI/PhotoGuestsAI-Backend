from typing import Dict

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel
from starlette.responses import JSONResponse

from .auth import get_current_user
from .events import generate_event_folder_path
from ..dynamodb_service import get_event_by_id, update_event_status
from ..enums.event_status import EventStatus
from ..faceRecognitionIntegrationService import create_and_upload_personalized_albums
from ..s3_service import upload_file_to_s3

router = APIRouter()


@router.post("/{event_id}/upload-event-album")
async def upload_event_album(event_id: str, album: UploadFile = File(...),
                             current_user: str = Depends(get_current_user)):
    """
    Handle the upload of album ZIP file and save it to S3 under the event's folder.

    Args:
        current_user:
        event_id (str): The event ID for the album.
        album (UploadFile): The album zip file.

    Returns:
        dict: Success message if the file was uploaded successfully.
    """
    try:
        event = get_event_by_id(event_id)
        if not event:
            raise HTTPException(404, "Event not found")

        if event["email"] != current_user:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to access this event"
            )

        event_folder_path = generate_event_folder_path(event)
        s3_key = f"{event_folder_path}album/{album.filename}"

        upload_success = upload_file_to_s3(album.file, s3_key, album.content_type)

        if upload_success:
            update_event_status(event_id, EventStatus.ALBUM_UPLOADED)
            return JSONResponse(content={"message": "Album uploaded successfully!"}, status_code=200)
        else:
            raise HTTPException(status_code=500, detail="Failed to upload the album")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


class AlbumProcessingRequest(BaseModel):
    username: str
    event_date: str
    event_name: str
    event_id: str
    relative_guest_photo_path: str
    phone_number: str


@router.post('/personalized_albums')
async def create_personalized_albums(request: AlbumProcessingRequest) -> Dict[str, str]:
    """
    Should have a specific authorization token to run this API
    """
    try:
        result_path = create_and_upload_personalized_albums(
            username=request.username,
            event_date=request.event_date,
            event_name=request.event_name,
            event_id=request.event_id,
            relative_guest_photo_path=request.relative_guest_photo_path,
            phone_number=request.phone_number
        )

        return {"message": "Processing completed", "personalized_album_s3_path": result_path}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{event_id}/get-personalized-album")
async def get_personalized_album(event_id: str, password: str):
    """
    Handle the upload of album ZIP file and save it to S3 under the event's folder.

    Args:
        current_user:
        event_id (str): The event ID for the album.
        album (UploadFile): The album zip file.

    Returns:
        dict: Success message if the file was uploaded successfully.
    """
    try:
        event = get_event_by_id(event_id)
        if not event:
            raise HTTPException(404, "Event not found")

        if event["email"] != current_user:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to access this event"
            )

        event_folder_path = generate_event_folder_path(event)
        s3_key = f"{event_folder_path}album/{album.filename}"

        upload_success = upload_file_to_s3(album.file, s3_key, album.content_type)

        if upload_success:
            update_event_status(event_id, EventStatus.ALBUM_UPLOADED)
            return JSONResponse(content={"message": "Album uploaded successfully!"}, status_code=200)
        else:
            raise HTTPException(status_code=500, detail="Failed to upload the album")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")
