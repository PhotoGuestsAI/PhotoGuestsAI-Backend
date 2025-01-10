from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import events, guests, auth

# Initialize the FastAPI app
app = FastAPI()

# CORS configuration - Allow frontend to interact with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Include routers for different sections of the app
app.include_router(events.router, prefix="/events", tags=["events"])
app.include_router(guests.router, prefix="/guests", tags=["guests"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])


# Root endpoint for health checks and general status
@app.get("/")
def read_root():
    return {"message": "Photo Guests Backend is running"}
