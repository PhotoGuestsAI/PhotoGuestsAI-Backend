from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import events, guests, albums, auth, payment

# Initialize the FastAPI app
app = FastAPI()

# CORS configuration - Allow frontend to interact with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React local dev
        "http://127.0.0.1:8000",  # React local dev
        "http://photoguests.com",  # Production frontend
        "https://photoguests.com",  # Production frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Include routers for different sections of the app
app.include_router(events.router, prefix="/events", tags=["events"])
app.include_router(guests.router, prefix="/guests", tags=["guests"])
app.include_router(albums.router, prefix="/albums", tags=["albums"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(payment.router, prefix="/payment", tags=["payment"])  # Corrected this line!


# Root endpoint for health checks and general status
@app.get("/")
def read_root():
    return {"message": "Photo Guests Backend is running"}
