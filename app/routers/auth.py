from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests

# Constants
GOOGLE_CLIENT_ID = "134801815902-ab4t528nqfnkadh4c93otdk80kcc1mhc.apps.googleusercontent.com"
GOOGLE_TOKEN_INFO_URL = "https://oauth2.googleapis.com/tokeninfo?id_token="

router = APIRouter()


class Token(BaseModel):
    token: str


def raise_http_exception(detail: str):
    """
    Helper function to raise HTTPException.
    """
    raise HTTPException(status_code=400, detail=detail)


@router.post("/verify-token")
async def verify_google_token(data: Token):
    """
    Verifies the Google ID token using Google's API.

    This endpoint ensures that the received Google token is valid
    and that the client ID matches the expected one.
    """
    url = f"{GOOGLE_TOKEN_INFO_URL}{data.token}"
    response = requests.get(url)

    if response.status_code != 200:
        raise_http_exception("Invalid token")

    user_info = response.json()

    # Validate audience matches your Client ID
    if user_info["aud"] != GOOGLE_CLIENT_ID:
        raise_http_exception("Invalid Client ID")

    return {
        "user": {
            "name": user_info["name"],
            "email": user_info["email"],
            "picture": user_info["picture"],
        }
    }
