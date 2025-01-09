from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests

router = APIRouter()

GOOGLE_CLIENT_ID = "134801815902-ab4t528nqfnkadh4c93otdk80kcc1mhc.apps.googleusercontent.com"


class Token(BaseModel):
    token: str


@router.post("/verify-token")
async def verify_google_token(data: Token):
    """
    Verifies the Google ID token using Google's API.
    """
    url = f"https://oauth2.googleapis.com/tokeninfo?id_token={data.token}"
    response = requests.get(url)

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Invalid token")

    user_info = response.json()

    # Validate audience matches your Client ID
    if user_info["aud"] != GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=400, detail="Invalid Client ID")

    return {
        "user": {
            "name": user_info["name"],
            "email": user_info["email"],
            "picture": user_info["picture"],
        }
    }
