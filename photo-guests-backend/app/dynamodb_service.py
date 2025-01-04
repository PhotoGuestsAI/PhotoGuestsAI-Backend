import boto3
import os
from uuid import uuid4

dynamodb = boto3.resource(
    "dynamodb",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
    region_name="us-east-1",
)

GUESTS_TABLE = "Guests"


def add_guest(event_id, name, phone):
    table = dynamodb.Table(GUESTS_TABLE)
    guest_id = str(uuid4())
    table.put_item(
        Item={
            "event_id": event_id,
            "guest_id": guest_id,
            "name": name,
            "phone": phone,
        }
    )
    return {"guest_id": guest_id, "name": name, "phone": phone}
