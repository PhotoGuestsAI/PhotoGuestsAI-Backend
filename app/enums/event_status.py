from enum import Enum


class EventStatus(str, Enum):
    PENDING_UPLOAD = "Pending Upload"
    ALBUM_UPLOADED = "Album Uploaded"
    COMPLETED = "Completed"
