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
            ServerSideEncryption="aws:kms"
        )

    return folder_name


def generate_upload_url(folder, file_name, expiration=86400):
    """
    Generate a pre-signed URL for uploading to S3.
    """
    key = f"{folder}{file_name}"
    return s3_client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": BUCKET_NAME,
            "Key": key,
            "ServerSideEncryption": "aws:kms"
        },
        ExpiresIn=expiration
    )
