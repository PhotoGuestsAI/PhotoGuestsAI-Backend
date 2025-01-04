import boto3
import os

s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
)

BUCKET_NAME = "your-s3-bucket-name"


def create_event_folder(event_id):
    folder_name = f"events/{event_id}/album/"
    s3_client.put_object(Bucket=BUCKET_NAME, Key=folder_name)
    return folder_name


def generate_presigned_url(key, expiration=3600):
    return s3_client.generate_presigned_url(
        "put_object",
        Params={"Bucket": BUCKET_NAME, "Key": key},
        ExpiresIn=expiration,
    )
