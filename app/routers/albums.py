import io
import os
import zipfile

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from starlette.responses import JSONResponse, StreamingResponse

from .auth import get_current_user
from .events import generate_event_folder_path
from .guests import validate_guest_by_uuid_and_phone_number
from ..dynamodb_service import get_event_by_id, update_event_status
from ..s3_service import upload_file_to_s3, download_file_as_bytes, s3_client, \
    generate_presigned_url

BUCKET_NAME = "photoguests-events"

router = APIRouter()


@router.post("/{event_id}/upload-event-album")
async def upload_event_album(event_id: str, album: UploadFile = File(...),
                             current_user: str = Depends(get_current_user)):
    """
    Extracts images from a ZIP file, renames them sequentially, and uploads them to S3 one-by-one.

    Args:
        event_id (str): The event ID.
        album (UploadFile): The uploaded ZIP file.
        current_user (str): The authenticated user email.

    Returns:
        dict: Success message if all images are uploaded successfully.
    """
    try:
        event = get_event_by_id(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        if event["email"] != current_user:
            raise HTTPException(status_code=403, detail="You are not authorized to upload to this event")

        # Block re-upload if an album is already uploaded
        if event.get("status") == "אלבום הועלה":
            raise HTTPException(status_code=400, detail="An album has already been uploaded for this event.")

        # Read ZIP file
        zip_file = await album.read()
        with zipfile.ZipFile(io.BytesIO(zip_file), "r") as zip_ref:
            # Exclude unnecessary files and folders
            ignored_files = ["__MACOSX/", ".DS_Store", "Thumbs.db", "desktop.ini"]
            image_files = [file for file in zip_ref.namelist()
                           if not any(file.startswith(ignore) for ignore in ignored_files)
                           and file.lower().endswith(('.jpg', '.jpeg', '.png'))]

            if not image_files:
                raise HTTPException(status_code=400, detail="No valid images found in the ZIP file.")

            max_images_allowed = event.get("num_images", 10000)
            if len(image_files) > max_images_allowed:
                raise HTTPException(status_code=400,
                                    detail=f"Uploaded ZIP contains {len(image_files)} images, exceeding the allowed limit of {max_images_allowed}.")

            event_folder_path = generate_event_folder_path(event)
            uploaded_files = []

            # Sequential upload (cheapest approach)
            for index, original_filename in enumerate(image_files, start=1):
                file_ext = os.path.splitext(original_filename)[1]  # Get file extension (.jpg, .png, etc.)
                new_filename = f"{index}{file_ext}"

                # Read image bytes
                with zip_ref.open(original_filename) as image_file:
                    image_data = io.BytesIO(image_file.read())  # Convert to BytesIO object for S3 upload

                s3_key = f"{event_folder_path}album/{new_filename}"
                upload_success = upload_file_to_s3(image_data, s3_key, content_type=f"image/{file_ext.lstrip('.')}")

                if upload_success:
                    uploaded_files.append(new_filename)
                else:
                    raise HTTPException(status_code=500, detail=f"Failed to upload {new_filename}")

        # Mark event as having an uploaded album
        update_event_status(event_id, "אלבום הועלה")

        return JSONResponse(
            content={"message": f"Album uploaded successfully! {len(uploaded_files)} images processed."},
            status_code=200)

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file format.")

    except HTTPException:
        raise  # Keep the original FastAPI exceptions

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing album: {str(e)}")


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

    await validate_guest_by_uuid_and_phone_number(event_folder_path, guest_uuid, phone_number)

    album_filename = f"{phone_number}.zip"
    s3_key = f"{event_folder_path}personalized-albums/{phone_number}/{album_filename}"

    try:
        s3_client.head_object(Bucket=BUCKET_NAME, Key=s3_key)
        file_data = download_file_as_bytes(s3_key)
    except s3_client.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            raise HTTPException(404, "Album not found.")
        raise HTTPException(500, f"Error retrieving album: {str(e)}")
    except Exception as e:
        raise HTTPException(500, f"Unexpected error: {str(e)}")

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

    await validate_guest_by_uuid_and_phone_number(event_folder_path, guest_uuid, phone_number)

    s3_prefix = f"{event_folder_path}personalized-albums/{phone_number}/"

    # List all images in the guest's folder
    try:
        response = s3_client.list_objects_v2(Bucket="photoguests-events", Prefix=s3_prefix)

        photos = [
            generate_presigned_url(obj["Key"])
            for obj in response.get("Contents", [])
            if obj["Key"].endswith((".jpg", ".jpeg", ".png"))
        ]

        return {"photos": photos}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving photos: {str(e)}")
