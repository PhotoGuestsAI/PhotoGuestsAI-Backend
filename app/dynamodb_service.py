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
