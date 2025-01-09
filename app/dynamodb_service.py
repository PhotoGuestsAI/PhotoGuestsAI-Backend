import csv
from datetime import datetime, timezone
import boto3
import os

dynamodb = boto3.resource(
    "dynamodb",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
    region_name=os.getenv("AWS_REGION", "us-east-1"),
)

EVENTS_TABLE = "Events"


def save_event(event_id, event_name, event_date, photographer_name, email, phone, upload_urls, folder):
    """
    Save event details to the Events DynamoDB table.
    """
    try:
        table = dynamodb.Table(EVENTS_TABLE)
        table.put_item(
            Item={
                "event_id": event_id,  # Partition key
                "event_name": event_name,
                "event_date": event_date,
                "photographer_name": photographer_name,
                "email": email,
                "phone": phone,  # Photographer phone number
                "upload_urls": upload_urls,  # Contains URLs for guest list and album upload
                "folder": folder,
                "created_at": datetime.now(timezone.utc).isoformat(),  # ISO 8601 timestamp
                "status": "Pending Upload",  # Default status
                "guest_list": [],  # Initially an empty list
            }
        )
        print(f"Event {event_name} created successfully!")
    except Exception as error:
        print(f"Error saving event to DynamoDB: {error}")
        raise


def insert_guests_from_s3_to_dynamodb(event_id):
    """
    Processes the uploaded guest list CSV and updates the DynamoDB table.
    """
    from app.s3_service import s3_client  # Import here to avoid circular imports

    bucket_name = "photo-guests-events"
    key = f"guest-submissions/{event_id}/guest_list.csv"

    # Download the CSV file
    s3_client.download_file(bucket_name, key, "/tmp/guest_list.csv")

    # Parse the CSV
    guest_list = []
    with open("/tmp/guest_list.csv", "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            guest_list.append({"name": row["name"], "phone": row["phone"]})

    # Update DynamoDB
    update_guest_list_in_dynamodb(event_id, guest_list)


def update_guest_list_in_dynamodb(event_id, guest_list):
    """
    Update the guest list for an event in the Events table.
    """
    try:
        table = dynamodb.Table(EVENTS_TABLE)
        table.update_item(
            Key={"event_id": event_id},
            UpdateExpression="SET guest_list = :g",
            ExpressionAttributeValues={":g": guest_list},
        )
        print(f"Guest list updated successfully for event_id {event_id}!")
    except Exception as error:
        print(f"Error updating guest list: {error}")
        raise
