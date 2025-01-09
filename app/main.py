from fastapi import FastAPI
from .routers import events, guests, auth

import sys
print(sys.path)

app = FastAPI()

# Include existing routers
app.include_router(events.router, prefix="/events", tags=["events"])
app.include_router(guests.router, prefix="/guests", tags=["guests"])

# Include the new auth router
app.include_router(auth.router, prefix="/auth", tags=["auth"])


@app.get("/")
def read_root():
    return {"message": "Photo Guests Backend is running"}
