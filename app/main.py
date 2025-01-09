from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import events, guests, auth

import sys

print(sys.path)

app = FastAPI()

# Allow CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include existing routers
app.include_router(events.router, prefix="/events", tags=["events"])
app.include_router(guests.router, prefix="/guests", tags=["guests"])

# Include the new auth router
app.include_router(auth.router, prefix="/auth", tags=["auth"])


@app.get("/")
def read_root():
    return {"message": "Photo Guests Backend is running"}
