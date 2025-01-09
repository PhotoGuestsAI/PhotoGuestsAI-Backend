import csv
import os
import boto3
from boto3.dynamodb.conditions import Attr

# Initialize DynamoDB resource
dynamodb = boto3.resource(
    "dynamodb",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
    region_name=os.getenv("AWS_REGION", "us-east-1"),
)

events_table = dynamodb.Table("Events")


def fetch_events_by_email(email: str):
    """
    Fetch all events for a specific user by email from DynamoDB.

    Args:
        email (str): The email of the user to fetch events for.

    Returns:
        list: A list of events for the user.
    """
    try:
        response = events_table.scan(FilterExpression=Attr("email").eq(email))
        return response.get("Items", [])
    except Exception as e:
        raise Exception(f"Error fetching events from DynamoDB: {str(e)}")


def get_event_by_id(event_id: str):
    """
    Fetch an event by its event_id from DynamoDB.
    """
    try:
        # Get the item using event_id as the key
        response = events_table.get_item(Key={"event_id": event_id})
        return response.get("Item")  # Return the item if found
    except Exception as e:
        raise Exception(f"Error fetching event by ID: {str(e)}")


def save_event(event_item: dict):
    """
    Save a new event to the DynamoDB events table.

    Args:
        event_item (dict): Dictionary containing event details to be saved.

    Returns:
        None
    """
    try:
        events_table.put_item(Item=event_item)
    except Exception as e:
        raise Exception(f"Failed to save event to DynamoDB: {str(e)}")


def insert_guests_from_s3_to_dynamodb(event_id):
    """
    Processes the uploaded guest list CSV from S3 and updates the guest list in DynamoDB.

    Args:
        event_id (str): The unique event ID.

    Returns:
        None
    """
    from .s3_service import s3_client  # Import here to avoid circular imports

    bucket_name = "photo-guests-events"
    key = f"{event_id}/guest-submissions/guest_list.csv"

    # Path for temporary file storage
    temp_file_path = "/tmp/guest_list.csv"

    try:
        # Download the CSV file from S3
        s3_client.download_file(bucket_name, key, temp_file_path)
        print(f"Downloaded guest list from S3: {key}")

        # Parse the CSV file
        guest_list = []
        with open(temp_file_path, "r") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                guest_list.append({"name": row["name"], "phone": row["phone"]})

        # Update the guest list in DynamoDB
        update_guest_list_in_dynamodb(event_id, guest_list)
        print(f"Guest list successfully processed and updated for event_id: {event_id}")

    except Exception as e:
        print(f"Error processing guest list from S3 for event_id {event_id}: {e}")
        raise
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


def update_guest_list_in_dynamodb(event_id, guest_list):
    """
    Update the guest list for an event in the DynamoDB events table.

    Args:
        event_id (str): The unique event ID.
        guest_list (list): List of guests with names and phone numbers.

    Returns:
        None
    """
    try:
        events_table.update_item(
            Key={"event_id": event_id},
            UpdateExpression="SET guest_list = :g",
            ExpressionAttributeValues={":g": guest_list},
        )
        print(f"Guest list updated successfully for event_id {event_id}!")
    except Exception as error:
        print(f"Error updating guest list: {error}")
        raise
