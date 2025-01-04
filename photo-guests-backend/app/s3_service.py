import boto3
import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
    region_name=os.getenv("AWS_REGION", "us-east-1"),
)

BUCKET_NAME = "photo-guests-events"


def create_event_folder(event_date, event_name):
    """
    Create the S3 folder structure under the bucket named 'photo-guests-events'.
    Folder structure: <event_date>/<event_name>/<subfolders>.
    """
    folder_name = f"{event_date}/{event_name}/"

    # Create subfolders for album, guest submissions, and personalized albums
    subfolders = ["album/", "guest-submissions/", "personalized-albums/"]
    for subfolder in subfolders:
        full_path = f"{folder_name}{subfolder}"
        print(f"Creating folder: {full_path}")
        s3_client.put_object(
            Bucket="photo-guests-events",
            Key=full_path,
            ServerSideEncryption="aws:kms"  # Required header
        )

    return folder_name


def generate_presigned_url(bucket_name, key, expiration=86400):
    """
    Generate a pre-signed URL for uploading to S3.
    :param bucket_name: Name of the S3 bucket.
    :param key: The path (key) in the S3 bucket where the file will be uploaded.
    :param expiration: Expiration time in seconds (default: 24 hours).
    :return: Pre-signed URL.
    """
    return s3_client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": bucket_name,
            "Key": key,
            "ServerSideEncryption": "aws:kms"  # Optional encryption requirement
        },
        ExpiresIn=expiration
    )


def generate_album_upload_url(folder, file_name):
    """
    Generate a pre-signed URL for uploading a file to the specified folder in the 'events' bucket.
    :param folder: The folder path where the file will be uploaded (e.g., '2025-01-15/Wedding/album/').
    :param file_name: The name of the file to be uploaded (e.g., 'photo1.jpg').
    :return: Pre-signed URL.
    """
    key = f"{folder}{file_name}"
    return generate_presigned_url(BUCKET_NAME, key, expiration=86400)  # 24 hours


def generate_guest_submission_url(event_id, guest_id):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    key = f"{today}/{event_id}/guest-submissions/{guest_id}/photo.jpg"
    return generate_presigned_url(key)
