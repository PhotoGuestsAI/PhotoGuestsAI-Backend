import os
import tempfile
import shutil
import requests
from dotenv import load_dotenv
from .s3_service import download_file_from_s3, upload_file_to_s3

# Load environment variables from .env file
load_dotenv()

# Define a custom temp directory within the project structure
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUSTOM_TEMP_DIR = os.path.join(BASE_DIR, "temp")

# Ensure the directory exists
os.makedirs(CUSTOM_TEMP_DIR, exist_ok=True)

# AWS S3 Configuration
BUCKET_NAME = os.getenv("EVENTS_BUCKET_NAME", "photo-guests-events")
FACE_RECOGNITION_SERVICE_URL = os.getenv("FACE_RECOGNITION_MICRO_SERVICE_URL_DEV")


def create_and_upload_personalized_albums(username, event_date, event_name, event_id, relative_guest_photo_path,
                                          phone_number):
    """
    Process the album for an event and upload the personalized version to S3.

    Args:
        username (str): Username of the event organizer.
        event_date (str): Event date in the format 'YYYY-MM-DD'.
        event_name (str): Name of the event.
        event_id (str): Unique event ID.
        relative_guest_photo_path (str): Relative path to the guest's photo.
        phone_number (str): Guest's phone number.

    Returns:
        str: S3 path of the uploaded personalized album.
    """
    temp_dir = tempfile.mkdtemp(dir=CUSTOM_TEMP_DIR)

    try:
        base_path = f"{username}/{event_date}/{event_name}/{event_id}/"
        event_album_s3_path = f"{base_path}album/event_album.zip"
        guest_photo_s3_path = f"{base_path}{relative_guest_photo_path.lstrip('/')}"  # Construct full S3 path
        personalized_album_s3_path = f"{base_path}personalized-albums/{phone_number}.zip"

        print(f"Starting processing for album: {event_album_s3_path}")

        # Step 1: Download Event Album from S3
        album_zip_path = os.path.join(temp_dir, 'event_album.zip')
        print(f"S3 Path: {event_album_s3_path}")
        print(f"Local Path: {album_zip_path}")
        print(f"Downloading event album from S3: {event_album_s3_path}")
        download_file_from_s3(BUCKET_NAME, event_album_s3_path, album_zip_path)

        # Step 2: Download Guest Photo from S3
        guest_photo_path = os.path.join(temp_dir, 'guest_photo.jpg')
        print(f"S3 Path: {event_album_s3_path}")
        print(f"Local Path: {album_zip_path}")
        print(f"Downloading guest photo from S3: {guest_photo_s3_path}")
        download_file_from_s3(BUCKET_NAME, guest_photo_s3_path, guest_photo_path)

        # Step 3: Send Album and Guest Photo to Face Recognition Service
        print("Sending album and guest photo to face recognition service...")
        personalized_album_content = send_to_face_recognition_service(album_zip_path, guest_photo_path)

        # Step 4: Save and Upload Personalized Album to S3
        personalized_album_path = os.path.join(temp_dir, f'{phone_number}_personalized_album.zip')
        with open(personalized_album_path, 'wb') as output_file:
            output_file.write(personalized_album_content)

        print(f"Uploading personalized album to S3: {personalized_album_s3_path}")
        upload_file_to_s3(
            file=open(personalized_album_path, 'rb'),
            file_name=personalized_album_s3_path,
            content_type='application/zip'
        )

        print(f"Personalized album uploaded successfully to S3: {personalized_album_s3_path}")
        return personalized_album_s3_path

    except Exception as e:
        print(f"Error processing album: {e}")
        raise

    finally:
        print("Cleaning up temporary files...")
        cleanup_temp_directory(temp_dir)


def send_to_face_recognition_service(album_path, guest_photo_path):
    """
    Send album and guest photo to the face recognition service.

    Args:
        album_path (str): Local path to the event album zip file.
        guest_photo_path (str): Local path to the guest's photo.

    Returns:
        bytes: Content of the personalized album returned by the face recognition service.
    """
    try:
        with open(album_path, 'rb') as album_file, open(guest_photo_path, 'rb') as guest_file:
            response = requests.post(
                FACE_RECOGNITION_SERVICE_URL,
                files={
                    'event_album': album_file,
                    'guest_photo': guest_file
                }
            )
        if response.status_code != 200:
            raise Exception(
                f"Face recognition service failed with status {response.status_code}: {response.text}"
            )
        print("Face recognition completed successfully.")
        return response.content

    except requests.exceptions.RequestException as req_error:
        print(f"Request to face recognition service failed: {req_error}")
        raise

    except Exception as e:
        print(f"Unexpected error during face recognition: {e}")
        raise


def cleanup_temp_directory(temp_dir):
    """
    Clean up temporary directory and files.
    """
    try:
        shutil.rmtree(temp_dir)
        print(f"Temporary directory cleaned: {temp_dir}")
    except Exception as e:
        print(f"Error cleaning up temp directory {temp_dir}: {e}")
