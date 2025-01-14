import csv
import os
import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables for AWS credentials and region
load_dotenv()

# Initialize DynamoDB resource
dynamodb = boto3.resource(
    "dynamodb",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
    region_name=os.getenv("AWS_REGION", "us-east-1"),
)

# Access the Events table in DynamoDB
events_table = dynamodb.Table("Events")


# === Event-related database operations ===

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

    Args:
        event_id (str): The unique event ID.

    Returns:
        dict: The event data.
    """
    try:
        response = events_table.get_item(Key={"event_id": event_id})
        return response.get("Item")  # Return event if found
    except Exception as e:
        raise Exception(f"Error fetching event by ID: {str(e)}")


def save_event(event_item: dict):
    """
    Save a new event to DynamoDB.

    Args:
        event_item (dict): The event details to be saved.
    """
    try:
        events_table.put_item(Item=event_item)
    except Exception as e:
        raise Exception(f"Failed to save event to DynamoDB: {str(e)}")


# === Guest List Management ===

def insert_guests_from_s3_to_dynamodb(event_id: str):
    """
    Process the uploaded guest list CSV from S3 and update the guest list in DynamoDB.

    Args:
        event_id (str): The unique event ID.
    """
    from .s3_service import s3_client  # Import here to avoid circular imports

    bucket_name = "photo-guests-events"
    key = f"{event_id}/guest-submissions/guest_list.csv"

    # Path to temporarily store the downloaded CSV file
    temp_file_path = "/tmp/guest_list.csv"

    try:
        # Download the CSV file from S3
        s3_client.download_file(bucket_name, key, temp_file_path)
        print(f"Downloaded guest list from S3: {key}")

        # Read the CSV file and prepare the guest list
        guest_list = []
        with open(temp_file_path, "r") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                guest_list.append({"name": row["name"], "phone": row["phone"]})

        # Update the guest list in DynamoDB
        update_guest_list_in_dynamodb(event_id, guest_list)
        print(f"Guest list successfully updated for event_id: {event_id}")

    except Exception as e:
        print(f"Error processing guest list for event_id {event_id}: {e}")
        raise
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


# dynamodb_service.py

# def update_guest_list_in_dynamodb(event_id: str, guest_data: dict):
#     """
#     Update the guest list for an event in DynamoDB by appending new guest data.
#
#     Args:
#         event_id (str): The event ID.
#         guest_data (dict): The data of the guest to add. It includes the name, phone, and photo URL.
#
#     Returns:
#         None
#     """
#     try:
#         # Retrieve the current guest list for the event
#         event = get_event_by_id(event_id)
#         if not event:
#             raise Exception("Event not found")
#
#         current_guest_list = event.get("guest_list", [])
#
#         # Append the new guest data
#         current_guest_list.append(guest_data)
#
#         # Update the guest list in DynamoDB
#         events_table.update_item(
#             Key={"event_id": event_id},
#             UpdateExpression="SET guest_list = :g",
#             ExpressionAttributeValues={":g": current_guest_list},
#         )
#         print(f"Guest list updated successfully for event_id {event_id}!")
#
#     except Exception as error:
#         print(f"Error updating guest list: {error}")
#         raise


# === Event Status Management ===

def update_event_status(event_id: str, status: str):
    """
    Update the status of an event in DynamoDB.

    Args:
        event_id (str): The unique event ID.
        status (str): The new status to be set for the event.
    """
    try:
        response = events_table.update_item(
            Key={"event_id": event_id},
            UpdateExpression="SET #status = :status",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":status": status},
            ReturnValues="UPDATED_NEW"
        )
        print(f"Event status updated successfully for event_id {event_id}: {response}")
    except ClientError as e:
        print(f"Error updating event status: {e}")
        raise
