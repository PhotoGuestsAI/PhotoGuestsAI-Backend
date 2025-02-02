import os

import paypalrestsdk
from fastapi import HTTPException, Depends, APIRouter
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import RedirectResponse
from .auth import get_current_user

router = APIRouter()

paypalrestsdk.configure({
    "mode": "live",
    "client_id": os.getenv("PAYPAL_CLIENT_ID"),
    "client_secret": os.getenv("PAYPAL_CLIENT_SECRET")
})


class EventData(BaseModel):
    event_name: str
    event_date: str
    phone_number: str
    email: str


@router.post("/create-payment")
async def create_payment(event: EventData, user_email: str = Depends(get_current_user)):
    """Creates a PayPal payment and returns approval URL with authentication"""

    if event.email != user_email:
        raise HTTPException(status_code=403, detail="Unauthorized to create this event.")

    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {"payment_method": "paypal"},
        "redirect_urls": {
            "return_url": "http://localhost:8000/payment/success",
            "cancel_url": "http://localhost:8000/payment/cancel"
        },
        "transactions": [{
            "amount": {"total": "0.01", "currency": "USD"},
            "description": f"Payment for event {event.event_name}"
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
    """Handles successful PayPal payments and creates the event"""
    payer_id = request.query_params.get("PayerID")
    payment_id = request.query_params.get("paymentId")

    if not payer_id or not payment_id:
        raise HTTPException(status_code=400, detail="Invalid PayPal response")

    payment = paypalrestsdk.Payment.find(payment_id)
    if payment.execute({"payer_id": payer_id}):
        return RedirectResponse(url="http://localhost:3000/events?payment=success")
    else:
        raise HTTPException(status_code=400, detail="Payment execution failed")


@router.get("/cancel")
async def payment_cancel():
    """Handles canceled PayPal payments"""
    return RedirectResponse(url="http://localhost:3000/events?payment=cancel")
