import os
import uuid
from typing import Any

import boto3
from fastapi import APIRouter, HTTPException, Header, Form, UploadFile, File
from twilio.rest import Client

from .events import generate_event_folder_path
from ..dynamodb_service import get_event_by_id
from ..s3_service import get_guest_list_from_s3, upload_file_to_s3, append_to_guest_list_in_s3

S3_BUCKET_NAME = "photo-guests-events"
s3_client = boto3.client("s3")

WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "your_account_sid")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "your_auth_token")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "+1234567890")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

BUCKET_NAME = "photo-guests-events"

router = APIRouter()


def generate_presigned_url(object_key: str, expiration: int = 60 * 24 * 14) -> Any | None:
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


@router.post("/{event_id}/submit-guest")
async def submit_guest(
        event_id: str,
        name: str = Form(...),
        phone: str = Form(...),
        photo: UploadFile = File(...)
):
    """ Handle the submission of a guest's details (name, phone, photo) and upload it to S3. """
    try:
        event = get_event_by_id(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        event_folder_path = generate_event_folder_path(event)

        guest_uuid = uuid.uuid4()

        guest_photo_s3_key = f"{event_folder_path}guest-submissions/{phone}_{guest_uuid}.jpg"

        upload_success = upload_file_to_s3(photo.file, guest_photo_s3_key, photo.content_type)

        if not upload_success:
            raise HTTPException(status_code=500, detail="Failed to upload the photo")

        guest_submission = {
            "name": name,
            "phone": phone,
            "photo_url": f"https://{BUCKET_NAME}.s3.amazonaws.com/{guest_photo_s3_key}"}

        guest_list_submissions_s3_key = f"{event_folder_path}guest-submissions/guest_list.json"

        append_to_guest_list_in_s3(guest_list_submissions_s3_key, guest_submission)

        return {"message": "Guest submitted successfully!"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting guest: {str(e)}")


# SMS VERSION
@router.post("/send-personalized-albums/")
def send_personalized_albums(
        event_id: str,
        authorization: str = Header(None)
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
                continue

            name = guest.get("name", "Guest")

            guest_uuid = guest.get("photo_url").split("/")[-1].rsplit(".", 1)[0]

            personal_album_link = f"http://localhost:8000/albums/get-personalized-album/{event_id}/{guest_uuid}" # TODO: use env variable for the IP address

            if send_sms_message(event["name"], phone_number, name, personal_album_link):
                success_count += 1

        return {"message": f"Successfully sent {success_count}/{len(guests)} SMS messages."}

    except Exception as e:
        print(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the request.")


def send_sms_message(event_name: str, phone_number: str, name: str, personal_album_endpoint: str) -> bool:
    """
    Send a personalized SMS with the guest's name and album link using Twilio.
    """
    message_body = f"Hi {name}! 🎉 Your {event_name} album is ready. Link to download as zip file: {personal_album_endpoint}\n Enjoy your memories! 📸"

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


# def send_whatsapp_message(event_name: str, phone_number: str, name: str, album_url: str) -> bool:
#     """
#     Send a personalized WhatsApp message with the guest's name and album link.
#     """
#     headers = {
#         "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
#         "Content-Type": "application/json"
#     }
#     payload = {
#         "messaging_product": "whatsapp",
#         "to": phone_number,
#         "type": "text",
#         "text": {
#             "body": f"Hi {name}! 🎉 Your {event_name} album is ready. Click here to download it: {album_url}\nEnjoy your memories! 📸"
#         }
#     }
#
#     try:
#         response = requests.post(WHATSAPP_API_URL, json=payload, headers=headers)
#
#         if response.status_code == 200:
#             print(f"✅ Message sent to {name} ({phone_number})")
#             return True
#         else:
#             print(f"❌ Failed to send message to {name} ({phone_number}): {response.text}")
#             return False
#     except Exception as e:
#         print(f"❌ Error sending WhatsApp message: {e}")
#         return False
