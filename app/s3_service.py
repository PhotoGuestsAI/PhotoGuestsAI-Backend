import json
import os

import boto3
from botocore.config import Config
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv

load_dotenv()

s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
    region_name=os.getenv("AWS_REGION"),
    config=Config(signature_version="s3v4")
)

BUCKET_NAME = "photoguests-events"


def create_event_folder(username, event_date, event_name, event_id):
    """
    Create the S3 folder structure under the specified bucket.
    Creates subfolders for album, guest submissions, and personalized albums.

    Args:
        username (str): User's name.
        event_date (str): Event date in the format 'YYYY-MM-DD'.
        event_name (str): Name of the event.
        event_id (str): Unique event ID.

    Returns:
        str: The folder path created on S3.
    """
    folder_name = f"{username}/{event_date}/{event_name}/{event_id}/"

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

    return folder_name


def upload_images_to_s3(image_paths, base_s3_path):
    """
    Upload multiple images to S3 instead of a ZIP file.

    Args:
        image_paths (list): List of local image file paths.
        base_s3_path (str): The base path in S3 where images should be stored.

    Returns:
        list: List of S3 paths for the uploaded images.
    """
    uploaded_image_urls = []

    for image_path in image_paths:
        try:
            image_filename = os.path.basename(image_path)
            s3_key = f"{base_s3_path}/{image_filename}"

            # Upload each image individually
            with open(image_path, "rb") as image_file:
                s3_client.upload_fileobj(
                    image_file,
                    "photoguests-events",
                    s3_key,
                    ExtraArgs={
                        "ContentType": "image/jpeg",  # Ensure correct content type
                        "ServerSideEncryption": "aws:kms"  # Optional encryption
                    }
                )

            # Generate a pre-signed URL for accessing the uploaded image
            presigned_url = generate_presigned_url(s3_key)
            uploaded_image_urls.append(presigned_url)

        except NoCredentialsError:
            raise Exception("AWS Credentials not available")
        except Exception as e:
            raise Exception(f"Error uploading image {image_path}: {str(e)}")

    return uploaded_image_urls


def generate_presigned_url(s3_key):
    """
    Generate a pre-signed URL for accessing an S3 object.

    Args:
        s3_key (str): The key (path) of the object in S3.

    Returns:
        str: A pre-signed URL for the object.
    """
    try:
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": "photoguests-events", "Key": s3_key},
            ExpiresIn=3600  # URL expires in 1 hour
        )
        return url
    except Exception as e:
        print(f"Error generating pre-signed URL: {e}")
        return None


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
        local_path (str): The full local path where the file will be saved.

    Returns:
        None
    """
    try:
        with open(local_path, 'wb') as file:  # Ensure we write to the file directly
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


def get_guest_list_from_s3(event_path: str) -> list:
    """
    Retrieve and parse the guest list JSON from S3.
    """
    try:
        guest_list_key = f"{event_path}guest-submissions/guest_list.json"
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=guest_list_key)
        guest_data = json.loads(response['Body'].read().decode("utf-8"))
        return guest_data
    except Exception as e:
        print(f"Error fetching guest list: {e}")
        return []


def download_file_as_bytes(s3_key):
    """
    Download a file from S3 and return its content as bytes.

    Args:
        s3_key (str): The file's S3 key (path)

    Returns:
        bytes: The content of the file.
    """
    try:
        file_object = s3_client.get_object(Bucket=BUCKET_NAME, Key=s3_key)
        return file_object['Body'].read()
    except NoCredentialsError:
        raise Exception("Credentials not available")
    except Exception as e:
        raise Exception(f"Error downloading file from S3: {str(e)}")
