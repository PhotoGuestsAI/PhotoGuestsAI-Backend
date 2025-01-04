import csv
from datetime import datetime, timezone

import boto3
import os
from uuid import uuid4
from botocore.exceptions import BotoCoreError, ClientError

# Initialize DynamoDB resource
dynamodb = boto3.resource(
    "dynamodb",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
    region_name=os.getenv("AWS_REGION", "us-east-1"),
)

# Table names
PHOTOGRAPHERS_TABLE = "Photographers"
GUESTS_TABLE = "Guests"


def save_event(event_id, event_name, event_date, photographer_name, email, phone, upload_url, folder):
    """
    Save event details to the Events DynamoDB table.
    """
    try:
        # Reference to the Events table
        table = dynamodb.Table("Events")

        # Add item to the table
        table.put_item(
            Item={
                "event_id": event_id,  # Partition key
                "event_name": event_name,
                "event_date": event_date,
                "photographer_name": photographer_name,
                "email": email,
                "phone": phone,  # Photographer phone number
                "upload_url": upload_url,
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


def add_guest(event_id, name, phone):
    """
    Add a guest to the DynamoDB table.
    """
    try:
        table = dynamodb.Table(GUESTS_TABLE)  # Define the guests table
        guest_id = str(uuid4())
        table.put_item(
            Item={
                "event_id": event_id,
                "guest_id": guest_id,
                "name": name,
                "phone": phone,
            }
        )
        print(f"Guest {name} added successfully!")
        return {"guest_id": guest_id, "name": name, "phone": phone}
    except (BotoCoreError, ClientError) as error:
        print(f"Error adding guest to DynamoDB: {error}")
        raise


def update_guest_list(event_id, guest_list):
    """
    Update the guest list for an event in the Events table.
    """
    try:
        table = dynamodb.Table("Events")
        table.update_item(
            Key={"event_id": event_id},
            UpdateExpression="SET guest_list = :g",
            ExpressionAttributeValues={":g": guest_list},
        )
        print(f"Guest list updated successfully for event_id {event_id}!")
    except Exception as error:
        print(f"Error updating guest list: {error}")
        raise


def process_guest_list(event_id):
    """
    Processes the uploaded guest list CSV and updates the DynamoDB table.
    """
    # S3 client
    s3_client = boto3.client("s3")

    # File location in S3
    bucket_name = "photo-guests-events"
    key = f"guest-submissions/{event_id}/guest_list.csv"

    # Download the CSV file
    s3_client.download_file(bucket_name, key, "/tmp/guest_list.csv")

    # Parse the CSV
    guest_list = []
    with open("/tmp/guest_list.csv", "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            guest_list.append({
                "name": row["name"],
                "phone": row["phone"]
            })

    # Update the DynamoDB table
    update_guest_list(event_id, guest_list)

    print(f"Guest list updated successfully for event_id {event_id}.")
