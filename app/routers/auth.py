from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import requests
import jwt
from fastapi.security import OAuth2PasswordBearer

# Constants
GOOGLE_CLIENT_ID = "134801815902-ab4t528nqfnkadh4c93otdk80kcc1mhc.apps.googleusercontent.com"
GOOGLE_TOKEN_INFO_URL = "https://oauth2.googleapis.com/tokeninfo?id_token="

router = APIRouter()


class Token(BaseModel):
    token: str


# Initialize the OAuth2PasswordBearer to get the token from the header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


# Function to decode JWT token and extract user email
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        # Decode the JWT token using the secret key
        payload = jwt.decode(token, "secret_key", algorithms=["HS256"])  # Adjust secret_key as needed
        return payload["email"]  # Return the email from the token payload
    except jwt.JWTError:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
        )


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


def raise_http_exception(detail: str):
    """
    Helper function to raise HTTPException.
    """
    raise HTTPException(status_code=400, detail=detail)
