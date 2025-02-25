import io
import os
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Header
from pydantic import BaseModel
from starlette.responses import JSONResponse, StreamingResponse

from .auth import get_current_user
from .events import generate_event_folder_path
from ..dynamodb_service import get_event_by_id, update_event_status
from ..enums.event_status import EventStatus
from ..faceRecognitionIntegrationService import create_and_upload_personalized_albums
from ..s3_service import upload_file_to_s3, download_file_as_bytes, get_guest_list_from_s3, s3_client

BUCKET_NAME = "photo-guests-events"

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


class PersonalizedAlbumRequest(BaseModel):
    event_prefix: str
    phone_number: str


@router.post('/personalized_albums')
async def create_personalized_albums(request: PersonalizedAlbumRequest, authorization: str = Header(None)
                                     ) -> dict:  # We run it manually
    """
    Should have a specific authorization token to run this API
    """
    # Validate Authorization Token
    REQUIRED_TOKEN = os.getenv("TOKEN_FOR_EXPENSIVE_REQUESTS")
    if authorization != REQUIRED_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        result_path = create_and_upload_personalized_albums(
            request.event_prefix,
            phone_number=request.phone_number
        )

        return {"message": "Processing completed", "personalized_album_s3_path": result_path}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get-personalized-album/{event_id}/{phone_number}/{guest_uuid}", response_class=StreamingResponse)
async def get_personalized_album(event_id: str, phone_number: str, guest_uuid: str):
    """
    Retrieve the personalized album ZIP file for a guest from S3.

    Args:
        event_id (str): The event ID for the album.
        phone_number (str): The guest's phone number.
        guest_uuid (str): The guest UUID of the personalized album.

    Returns:
        StreamingResponse: The personalized album ZIP file.
    """

    event = get_event_by_id(event_id)
    event_folder_path = generate_event_folder_path(event)

    guests = get_guest_list_from_s3(event_folder_path)
    if not guests:
        raise HTTPException(status_code=404, detail="No guests found for this event.")

    matching_guest = next(
        (
            g for g in guests
            if g.get("phone") == phone_number
               and os.path.splitext(g.get("photo_url", "").split("/")[-1].split("_")[-1])[0] == guest_uuid
        ),
        None
    )

    if not matching_guest:
        raise HTTPException(status_code=403, detail="Guest not authorized or not found.")

    album_filename = f"{phone_number}.zip"
    s3_key = f"{event_folder_path}personalized-albums/{album_filename}"

    try:
        file_data = download_file_as_bytes(s3_key)
        if not file_data:
            raise HTTPException(status_code=404, detail="Album not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving album: {str(e)}")

    return StreamingResponse(
        io.BytesIO(file_data),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={guest_uuid}.zip"}
    )


@router.get("/get-personalized-album-photos/{event_id}/{phone_number}/{guest_uuid}")
async def get_personalized_album_photos(event_id: str, phone_number: str, guest_uuid: str):
    """
    Retrieve a list of personalized album photo URLs for a guest.

    Args:
        event_id (str): The event ID.
        phone_number (str): The guest's phone number.
        guest_uuid (str): The guest UUID.

    Returns:
        dict: A JSON response containing an array of image URLs.
    """

    event = get_event_by_id(event_id)
    event_folder_path = generate_event_folder_path(event)

    s3_prefix = f"{event_folder_path}personalized-albums/{phone_number}/"

    # List all images in the guest's folder
    try:
        response = s3_client.list_objects_v2(Bucket="photo-guests-events", Prefix=s3_prefix)
        if "Contents" not in response:
            raise HTTPException(status_code=404, detail="No images found.")

        # Generate pre-signed URLs for each image
        photos = [
            generate_presigned_url(obj["Key"])
            for obj in response["Contents"]
            if obj["Key"].endswith((".jpg", ".jpeg", ".png"))
        ]

        return {"photos": photos}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving photos: {str(e)}")


def generate_presigned_url(object_key: str, expiration: int = 60 * 24 * 14) -> Any | None:
    """
    Generate a pre-signed URL for accessing a private file in S3.
    """
    try:
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET_NAME, "Key": object_key},
            ExpiresIn=expiration,
        )
        return url
    except Exception as e:
        print(f"❌ Error generating pre-signed URL: {e}")
        return None
