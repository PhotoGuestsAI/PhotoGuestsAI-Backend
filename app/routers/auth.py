import os

import requests
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Constants
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_TOKEN_INFO_URL = "https://oauth2.googleapis.com/tokeninfo?id_token="

router = APIRouter()


class Token(BaseModel):
    token: str


@router.post("/verify-token")
async def verify_google_token(data: Token):
    """
    Verifies the Google ID token sent from the UI.
    """
    try:
        # Validate the token using Google's public endpoint
        response = requests.get(f"{GOOGLE_TOKEN_INFO_URL}{data.token}")

        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")

        user_info = response.json()

        # Ensure the token audience matches the backend client ID
        if user_info["aud"] != GOOGLE_CLIENT_ID:
            raise HTTPException(status_code=401, detail="Invalid audience")

        return {
            "user": {
                "name": user_info["name"],
                "email": user_info["email"],
                "picture": user_info["picture"],
                "token": data.token,
                # Send the same token back to the client (this way, I don't need to manage another token)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")


# Initialize OAuth2PasswordBearer to extract token from the Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Validates the Google ID token sent by the UI and extracts the user email.
    """
    try:
        # Validate the token using Google's public endpoint
        response = requests.get(f"{GOOGLE_TOKEN_INFO_URL}{token}")

        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")

        user_info = response.json()

        # Ensure the token audience matches the backend client ID
        if user_info["aud"] != GOOGLE_CLIENT_ID:
            raise HTTPException(status_code=401, detail="Invalid audience")

        return user_info["email"]
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Could not validate credentials: {str(e)}")
