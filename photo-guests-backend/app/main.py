from fastapi import FastAPI
from app.routers import events, guests

import sys
print(sys.path)

app = FastAPI()

# Include routers
app.include_router(events.router, prefix="/events", tags=["events"])
app.include_router(guests.router, prefix="/guests", tags=["guests"])


@app.get("/")
def read_root():
    return {"message": "Photo Guests Backend is running"}
