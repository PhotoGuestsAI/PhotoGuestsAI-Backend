import os

import boto3
import requests
from fastapi import APIRouter, HTTPException, Header
from twilio.rest import Client

from .events import generate_event_folder_path
from ..dynamodb_service import get_event_by_id
from ..s3_service import get_guest_list_from_s3

S3_BUCKET_NAME = "photo-guests-events"
s3_client = boto3.client("s3")

WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "your_account_sid")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "your_auth_token")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "+1234567890")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

router = APIRouter()


def generate_presigned_url(object_key: str, expiration: int = 60 * 24 * 14) -> str:
    """
    Generate a pre-signed URL for accessing a private file in S3.
    """
    try:
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET_NAME, "Key": object_key},
            ExpiresIn=expiration,
        )
        return url
    except Exception as e:
        print(f"❌ Error generating pre-signed URL: {e}")
        return None


def send_whatsapp_message(event_name: str, phone_number: str, name: str, album_url: str) -> bool:
    """
    Send a personalized WhatsApp message with the guest's name and album link.
    """
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {
            "body": f"Hi {name}! 🎉 Your {event_name} album is ready. Click here to download it: {album_url}\nEnjoy your memories! 📸"
        }
    }

    try:
        response = requests.post(WHATSAPP_API_URL, json=payload, headers=headers)

        if response.status_code == 200:
            print(f"✅ Message sent to {name} ({phone_number})")
            return True
        else:
            print(f"❌ Failed to send message to {name} ({phone_number}): {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error sending WhatsApp message: {e}")
        return False


# WhatsApp version
# @router.post("/send-personalized-albums/")
# def send_personalized_albums(event_id: str):
#     """
#     Retrieve guest phone numbers and send them their personalized album links via WhatsApp.
#     """
#
#     """
#     Should have a specific authorization token to run this API
#     """
#
#     try:
#         # Fetch event details directly from the database instead of calling the API
#         event = get_event_by_id(event_id)
#         if not event:
#             raise HTTPException(status_code=404, detail="Event not found.")
#
#         event_path = generate_event_folder_path(event)
#
#         guests = get_guest_list_from_s3(event_path)
#
#         if not guests:
#             raise HTTPException(status_code=404, detail="No guests found for this event.")
#
#         success_count = 0
#
#         for guest in guests:
#             phone_number = guest.get("phone")
#
#             if not phone_number:
#                 continue
#
#             name = guest.get("name")
#
#             if not name:
#                 continue
#
#             object_key = f"{event_path}personalized-albums/{phone_number}_album.zip"
#             presigned_url = generate_presigned_url(object_key)
#
#             if not presigned_url:
#                 continue
#
#             if send_whatsapp_message(event["name"], phone_number, name, presigned_url):
#                 success_count += 1
#
#         return {"message": f"Successfully sent {success_count}/{len(guests)} messages."}
#
#     except Exception as e:
#         print(f"Error processing request: {e}")
#         raise HTTPException(status_code=500, detail="An error occurred while processing the request.")


# SMS VERSION
@router.post("/send-personalized-albums/")
def send_personalized_albums(
        event_id: str,
        authorization: str = Header(None)  # Require an Authorization Token
):
    """
    Retrieve guest phone numbers and send them their personalized album links via SMS.
    Requires a specific authorization token to run this API.
    """

    # Validate Authorization Token
    REQUIRED_TOKEN = os.getenv("TOKEN_FOR_EXPENSIVE_REQUESTS")
    if authorization != REQUIRED_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        # Fetch event details directly from the database instead of calling an API
        event = get_event_by_id(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found.")

        event_path = generate_event_folder_path(event)

        guests = get_guest_list_from_s3(event_path)

        if not guests:
            raise HTTPException(status_code=404, detail="No guests found for this event.")

        success_count = 0

        for guest in guests:
            phone_number = guest.get("phone")

            if not phone_number:
                continue  # Skip if no phone number

            name = guest.get("name", "Guest")  # Default to 'Guest' if no name

            object_key = f"{event_path}personalized-albums/{phone_number}_album.zip"
            presigned_url = generate_presigned_url(object_key)

            if not presigned_url:
                continue  # Skip if no album URL

            if send_sms_message(event["name"], phone_number, name, presigned_url):
                success_count += 1

        return {"message": f"Successfully sent {success_count}/{len(guests)} SMS messages."}

    except Exception as e:
        print(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the request.")


def send_sms_message(event_name: str, phone_number: str, name: str, album_url: str) -> bool:
    """
    Send a personalized SMS with the guest's name and album link using Twilio.
    """
    message_body = f"Hi {name}! 🎉 Your {event_name} album is ready. Download it here: {album_url}\nEnjoy your memories! 📸"

    try:
        message = twilio_client.messages.create(
            body=message_body,
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number
        )

        print(f"✅ SMS sent to {name} ({phone_number}) | SID: {message.sid}")
        return True

    except Exception as e:
        print(f"❌ Error sending SMS to {name} ({phone_number}): {e}")
        return False
