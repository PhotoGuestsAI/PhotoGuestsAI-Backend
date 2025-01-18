import os
import tempfile
import boto3
import requests
from dotenv import load_dotenv
from s3_service import download_file_from_s3, upload_file_to_s3  # Custom S3 utilities in your project

# Load environment variables from .env file
load_dotenv()

# AWS S3 Configuration
BUCKET_NAME = os.getenv("EVENTS_BUCKET_NAME", "photo-guests-events")
FACE_RECOGNITION_SERVICE_URL = os.getenv("FACE_RECOGNITION_SERVICE_URL", "http://localhost:5000/process")


def process_and_upload_album(username, event_date, event_name, event_id, guest_photo_path, phone_number):
    """
    Process the album for an event and upload the personalized version to S3.

    Args:
        username (str): Username of the event organizer.
        event_date (str): Event date in the format 'YYYY-MM-DD'.
        event_name (str): Name of the event.
        event_id (str): Unique event ID.
        guest_photo_path (str): Local path to the guest's photo.
        phone_number (str): Guest's phone number.

    Returns:
        str: S3 path of the uploaded personalized album.
    """
    temp_dir = tempfile.mkdtemp()

    try:
        # Construct the S3 paths
        base_path = f"{username}/{event_date}/{event_name}/{event_id}/"
        event_album_s3_path = f"{base_path}album/event_album.zip"
        personalized_album_s3_path = f"{base_path}personalized-albums/{phone_number}_album.zip"

        # Step 1: Download Event Album from S3
        album_zip_path = os.path.join(temp_dir, 'event_album.zip')
        download_file_from_s3(BUCKET_NAME, event_album_s3_path, album_zip_path)

        # Step 2: Send Album and Guest Photo to Face Recognition Service
        personalized_album_content = send_to_face_recognition_service(album_zip_path, guest_photo_path)

        # Step 3: Save and Upload Personalized Album to S3
        personalized_album_path = os.path.join(temp_dir, f'{phone_number}_personalized_album.zip')
        with open(personalized_album_path, 'wb') as output_file:
            output_file.write(personalized_album_content)

        upload_file_to_s3(
            file=open(personalized_album_path, 'rb'),
            file_name=personalized_album_s3_path,
            content_type='application/zip'
        )

        print(f"Personalized album uploaded successfully to S3: {personalized_album_s3_path}")
        return personalized_album_s3_path

    finally:
        # Cleanup Temporary Directory
        cleanup_temp_directory(temp_dir)


def send_to_face_recognition_service(album_path, guest_photo_path):
    """Send album and guest photo to the face recognition service."""
    try:
        with open(album_path, 'rb') as album_file, open(guest_photo_path, 'rb') as guest_file:
            response = requests.post(
                FACE_RECOGNITION_SERVICE_URL,
                files={'event_album': album_file, 'guest_photo': guest_file}
            )
        if response.status_code != 200:
            raise Exception(f"Face recognition service failed: {response.text}")
        return response.content
    except Exception as e:
        print(album_path, None, f"Face recognition service error: {e}")
        raise


def cleanup_temp_directory(temp_dir):
    """Cleanup temporary directory."""
    for file in os.listdir(temp_dir):
        os.remove(os.path.join(temp_dir, file))
    os.rmdir(temp_dir)


# Example Usage
if __name__ == "__main__":
    try:
        result_path = process_and_upload_album(
            username="Amit Lus",
            event_date="2025-01-09",
            event_name="3434",
            event_id="c63e5499-ee78-4d04-9816-336d6b893afe",
            guest_photo_path="/guest-submissions/badur_a5eb7dbc-c50e-435f-b16a-8896efdbf814.jpg",
            phone_number="9876543210"
        )

        print(f"Process completed. Personalized album available at: {result_path}")
    except Exception as e:
        print(f"Process failed: {e}")
