import io
import os
import zipfile

import boto3
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv

load_dotenv()

s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
    region_name=os.getenv("AWS_REGION", "us-east-1"),
)

BUCKET_NAME = "photo-guests-events"


def create_event_folder(photographer_name, event_date, event_name, event_id):
    """
    Create the S3 folder structure under the bucket named 'photo-guests-events'.
    Folder structure: <photographer_name>/<event_date>/<event_name>/<event_id>/<subfolders>.
    Creates an empty event_album.zip file in the 'album' folder.
    """
    folder_name = f"{photographer_name}/{event_date}/{event_name}/{event_id}/"

    # Create subfolders for album, guest submissions, and personalized albums
    subfolders = ["album/", "guest-submissions/", "personalized-albums/"]
    for subfolder in subfolders:
        full_path = f"{folder_name}{subfolder}"
        print(f"Creating folder: {full_path}")
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=full_path,
            ServerSideEncryption="aws:kms",  # Optional encryption requirement
        )

    # Create an empty event_album.zip file in the 'album' folder
    empty_zip_file = io.BytesIO()  # Create an in-memory bytes buffer
    with zipfile.ZipFile(empty_zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        pass  # Empty zip file, no files added

    # Ensure the file is at the beginning of the buffer before uploading
    empty_zip_file.seek(0)

    # Upload the empty zip file to S3 in the 'album' folder
    zip_file_path = f"{folder_name}album/event_album.zip"
    print(f"Creating empty zip file: {zip_file_path}")
    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=zip_file_path,
        Body=empty_zip_file,
        ContentType='application/zip',
        ServerSideEncryption="aws:kms",  # Optional encryption requirement
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


def generate_event_presigned_urls(photographer_name, event_date, event_name, event_id):
    """
    Generate pre-signed URLs for uploading the guest list CSV and album photos.
    """
    # Define paths for the files
    guest_list_key = f"{photographer_name}/{event_date}/{event_name}/{event_id}/guest-submissions/guest_list.csv"
    album_key = f"{photographer_name}/{event_date}/{event_name}/{event_id}/album/event_album.zip"

    # Generate pre-signed URLs
    guest_list_url = generate_presigned_upload_url(BUCKET_NAME, guest_list_key)
    album_url = generate_presigned_upload_url(BUCKET_NAME, album_key)

    return {
        "guest_list_upload_url": guest_list_url,
        "album_upload_url": album_url
    }


def upload_file_to_s3(file, file_name, content_type):
    """
    Upload a file to S3.

    Args:
        file: The file to upload.
        file_name (str): The destination file name in S3.
        content_type (str): The content type of the file (e.g., 'application/zip').

    Returns:
        bool: True if upload is successful, False otherwise.
    """
    try:
        s3_client.upload_fileobj(
            file,
            BUCKET_NAME,
            file_name,
            ExtraArgs={
                'ContentType': content_type,
                'ServerSideEncryption': 'aws:kms'  # Optional encryption for the file
            }
        )
        return True
    except NoCredentialsError:
        raise Exception("Credentials not available")
    except Exception as e:
        raise Exception(f"Error uploading file: {str(e)}")
