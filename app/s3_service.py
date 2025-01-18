import io
import json
import os
import zipfile
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv
import boto3

# Load environment variables from .env file
load_dotenv()

# Set up AWS S3 client with the credentials from environment variables
s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
    region_name=os.getenv("AWS_REGION", "us-east-1"),
)

BUCKET_NAME = "photo-guests-events"


def create_event_folder(photographer_name, event_date, event_name, event_id):
    """
    Create the S3 folder structure under the specified bucket.
    Creates subfolders for album, guest submissions, and personalized albums.
    Also creates an empty album zip file in the 'album' folder.

    Args:
        photographer_name (str): Photographer's name.
        event_date (str): Event date in the format 'YYYY-MM-DD'.
        event_name (str): Name of the event.
        event_id (str): Unique event ID.

    Returns:
        str: The folder path created on S3.
    """
    folder_name = f"{photographer_name}/{event_date}/{event_name}/{event_id}/"

    # List of subfolders to create under the event folder
    subfolders = ["album/", "guest-submissions/", "personalized-albums/"]
    for subfolder in subfolders:
        full_path = f"{folder_name}{subfolder}"
        print(f"Creating folder: {full_path}")
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=full_path,
            ServerSideEncryption="aws:kms",  # Optional encryption for the folder
        )

    # Create an empty event_album.zip file in the 'album' folder
    empty_zip_file = io.BytesIO()  # In-memory bytes buffer
    with zipfile.ZipFile(empty_zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        pass  # Empty zip file, no files added

    empty_zip_file.seek(0)  # Ensure the buffer is at the beginning

    # Upload the empty zip file to the album folder on S3
    zip_file_path = f"{folder_name}album/event_album.zip"
    print(f"Creating empty zip file: {zip_file_path}")
    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=zip_file_path,
        Body=empty_zip_file,
        ContentType='application/zip',
        ServerSideEncryption="aws:kms",  # Optional encryption
    )

    return folder_name


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


def download_file_from_s3(bucket_name, s3_key, local_path):
    """
    Download a file from S3 to a local path.

    Args:
        bucket_name (str): Name of the S3 bucket.
        s3_key (str): The S3 key (path) of the file to download.
        local_path (str): The local path to save the file.

    Returns:
        None
    """
    try:
        with open(local_path, 'wb') as file:
            s3_client.download_fileobj(bucket_name, s3_key, file)
        print(f"File downloaded successfully from S3: {s3_key} to {local_path}")
    except NoCredentialsError:
        raise Exception("Credentials not available")
    except Exception as e:
        raise Exception(f"Error downloading file from S3: {str(e)}")


def append_to_guest_list_in_s3(file_key, guest_submission):
    """ Append a guest's submission to the existing guest list in S3. """
    try:
        try:
            file_object = s3_client.get_object(Bucket=BUCKET_NAME, Key=file_key)
            guest_list = json.loads(file_object['Body'].read().decode('utf-8'))
        except s3_client.exceptions.NoSuchKey:
            guest_list = []

        guest_list.append(guest_submission)

        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=file_key,
            Body=json.dumps(guest_list),
            ContentType='application/json'
        )
    except Exception as e:
        print(f"Error appending to guest list in S3: {str(e)}")
        raise


def generate_presigned_upload_url():
    return None
