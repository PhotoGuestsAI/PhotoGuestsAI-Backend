import os

import boto3
from dotenv import load_dotenv

load_dotenv()

s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
    region_name=os.getenv("AWS_REGION", "us-east-1"),
)

BUCKET_NAME = "photo-guests-events"


def create_event_folder(event_date, event_id):
    """
    Create the S3 folder structure under the bucket named 'photo-guests-events'.
    Folder structure: <event_date>/<event_id>/<subfolders>.
    """
    folder_name = f"{event_date}/{event_id}/"

    # Create subfolders for album, guest submissions, and personalized albums
    subfolders = ["album/", "guest-submissions/", "personalized-albums/"]
    for subfolder in subfolders:
        full_path = f"{folder_name}{subfolder}"
        print(f"Creating folder: {full_path}")
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=full_path,
            ServerSideEncryption="aws:kms"  # Required header
        )

    return folder_name


def generate_presigned_upload_url(bucket_name, key, expiration=86400):
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


def generate_event_presigned_urls(event_date, event_id):
    """
    Generate pre-signed URLs for uploading the guest list CSV and event album.
    """
    # Guest list CSV upload URL
    guest_list_key = f"{event_date}/{event_id}/guest-submissions/guest_list.csv"
    guest_list_url = generate_presigned_upload_url(BUCKET_NAME, guest_list_key)

    # Event album upload URL
    album_key = f"{event_date}/{event_id}/album/event_album.zip"
    album_url = generate_presigned_upload_url(BUCKET_NAME, album_key)

    return {"guest_list_upload_url": guest_list_url, "album_upload_url": album_url}