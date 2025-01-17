from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import requests
import jwt
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta

# Constants
GOOGLE_CLIENT_ID = "134801815902-ab4t528nqfnkadh4c93otdk80kcc1mhc.apps.googleusercontent.com"
GOOGLE_TOKEN_INFO_URL = "https://oauth2.googleapis.com/tokeninfo?id_token="
SECRET_KEY = "your_secret_key"  # Replace with a strong secret key
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60

router = APIRouter()


class Token(BaseModel):
    token: str


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

        # Return user details without generating a new token
        return {
            "user": {
                "name": user_info["name"],
                "email": user_info["email"],
                "picture": user_info["picture"],
                "token": data.token,  # Send the same token back to the client
            }
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")


def generate_jwt_token(email: str):
    """
    Generate a JWT token with an expiration time.
    """
    # expiration = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    payload = {
        "email": email,
        # "exp": expiration,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def raise_http_exception(detail: str):
    """
    Helper function to raise HTTPException.
    """
    raise HTTPException(status_code=400, detail=detail)
