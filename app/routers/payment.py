import os
import time
import uuid

import httpx
import paypalrestsdk
from dotenv import load_dotenv
from fastapi import HTTPException, Depends, APIRouter, Request
from pydantic import BaseModel
from starlette.responses import RedirectResponse

from .auth import get_current_user

load_dotenv()

ENV = os.getenv("ENV").lower()

FRONTEND_DOMAIN = (
    os.getenv("BACKEND_FRONTEND_DNS_HOST_NAME")  # Use production domain
    if ENV == "production"
    else os.getenv("LOCAL_FRONTEND")  # Use localhost for development
)

BACKEND_DOMAIN = (
    os.getenv("BACKEND_FRONTEND_DNS_HOST_NAME")  # Use production domain
    if ENV == "production"
    else os.getenv("LOCAL_BACKEND")  # Use localhost for development
)

router = APIRouter()

# In-memory storage for temporary tokens with expiration
token_storage = {}
# Token expiration time in seconds (30 minutes)
TOKEN_EXPIRATION = 30 * 60

paypalrestsdk.configure({
    "mode": "live",
    "client_id": os.getenv("PAYPAL_CLIENT_ID"),
    "client_secret": os.getenv("PAYPAL_CLIENT_SECRET")
})

tiered_pricing = [
    (100, 1000, 120), (100, 2500, 240), (100, 5000, 440), (100, 10000, 840),
    (250, 1000, 180), (250, 2500, 300), (250, 5000, 500), (250, 10000, 900),
    (500, 1000, 280), (500, 2500, 400), (500, 5000, 600), (500, 10000, 1000),
    (1000, 1000, 480), (1000, 2500, 600), (1000, 5000, 800), (1000, 10000, 1200)
]


def calculate_price(num_guests: int, num_images: int) -> int:
    for guests, images, price in tiered_pricing:
        if num_guests <= guests and num_images <= images:
            return price
    raise Exception(f"No pricing tier found for {num_guests} guests and {num_images} images.")


class EventData(BaseModel):
    name: str
    date: str
    phone: str
    username: str
    email: str
    num_guests: int
    num_images: int
    price: int
    token: str = None


def clean_expired_tokens():
    """Remove expired tokens from storage"""
    current_time = time.time()
    expired_keys = [key for key, value in token_storage.items()
                    if value["expires_at"] < current_time]

    for key in expired_keys:
        del token_storage[key]


@router.post("/calculate-price")
async def get_price(num_guests: int, num_images: int):
    """Endpoint to fetch the price based on guest and image selection."""
    return {"price": calculate_price(num_guests, num_images)}


@router.post("/create-payment")
async def create_payment(event: EventData, user_email: str = Depends(get_current_user)):
    """Creates a PayPal payment and returns approval URL with authentication"""
    calculated_price = calculate_price(event.num_guests, event.num_images)
    if calculated_price != event.price:
        raise HTTPException(status_code=400, detail="Price mismatch detected.")

    # Clean expired tokens first
    clean_expired_tokens()

    if event.email != user_email:
        raise HTTPException(status_code=403, detail="Unauthorized to create this event.")

    reference_id = str(uuid.uuid4())  # Generated a unique reference ID (can't pass token in "custom" - too long

    # Store the token with the reference ID and expiration
    token_storage[reference_id] = {
        "token": event.token,
        "expires_at": time.time() + TOKEN_EXPIRATION
    }

    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {"payment_method": "paypal"},
        "redirect_urls": {
            "return_url": f"http://{BACKEND_DOMAIN}/payment/success",
            "cancel_url": f"http://{BACKEND_DOMAIN}/payment/cancel"
        },
        "transactions": [{
            "amount": {"total": str(calculated_price), "currency": "ILS"},
            "description": f"Payment for event {event.name}",
            "custom": f"{event.name}|{event.date}|{event.phone}|{event.username}|{event.email}|{event.num_guests}|{event.num_images}|{event.price}|{reference_id}",
        }]
    })

    if payment.create():
        for link in payment.links:
            if link.rel == "approval_url":
                return {"approval_url": link.href}
    else:
        raise HTTPException(status_code=400, detail=str(payment.error))


@router.get("/success")
async def payment_success(request: Request):
    """Handles successful PayPal payments and then creates the event"""
    # First, clean expired tokens
    clean_expired_tokens()

    payer_id = request.query_params.get("PayerID")
    payment_id = request.query_params.get("paymentId")

    if not payer_id or not payment_id:
        raise HTTPException(status_code=400, detail="Invalid PayPal response")

    try:
        # Fetch PayPal payment details
        payment = paypalrestsdk.Payment.find(payment_id)
        if not payment:
            raise HTTPException(status_code=400, detail="Payment not found")

        # Execute the payment
        if not payment.execute({"payer_id": payer_id}):
            raise HTTPException(status_code=400, detail=f"Payment execution failed: {payment.error}")

        # Check if transactions exist
        if not payment.transactions or len(payment.transactions) == 0:
            print("⚠️ DEBUG: No transactions found in payment:", payment.to_dict())
            raise HTTPException(status_code=400, detail="No transactions found in payment")

        # Get transaction details
        transaction = payment.transactions[0]
        transaction_dict = transaction.to_dict()

        # Attempt to get metadata from dictionary
        event_metadata = transaction_dict.get("custom")

        # Fallback to related_resources if needed
        if not event_metadata and "related_resources" in transaction_dict:
            try:
                event_metadata = transaction_dict["related_resources"][0]["sale"]["custom"]
            except (IndexError, KeyError, TypeError):
                pass

        if not event_metadata:
            print("⚠️ DEBUG: Missing event metadata. Full payment data:", payment.to_dict())
            raise HTTPException(status_code=400, detail="Missing event metadata")

        try:
            name, date, phone, username, email, num_guests, num_images, price, reference_id = event_metadata.split("|")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid event metadata format")

        if reference_id not in token_storage:
            raise HTTPException(status_code=400, detail=f"Invalid or expired session. Reference ID: {reference_id}")

        token = token_storage[reference_id]["token"]

        # Clean up the token storage after successful retrieval
        del token_storage[reference_id]

        event_data = {"name": name, "date": date, "phone": phone, "username": username, "email": email,
                      "num_guests": num_guests, "num_images": num_images, "price": price}

        # Call POST /events/ API
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"http://{BACKEND_DOMAIN}/events/",
                json=event_data,
                headers={"Authorization": f"Bearer {token}"},
            )

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Failed to create event: {response.text}")

        # Redirect to frontend
        return RedirectResponse(
            url=f"http://{FRONTEND_DOMAIN}/events"
        )

    except paypalrestsdk.ResourceNotFound as e:
        raise HTTPException(status_code=404, detail=f"Payment not found: {str(e)}")
    except KeyError as e:
        print(f"ERROR: Key error - {e}")
        raise HTTPException(status_code=400, detail=f"Missing required data: {str(e)}")
    except Exception as e:
        print(f"ERROR: Unexpected issue in payment_success: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
