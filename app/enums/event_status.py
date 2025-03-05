from enum import Enum

class EventStatus(str, Enum):
    PENDING_UPLOAD = "ממתין להעלאה"
    ALBUM_UPLOADED = "אלבום הועלה"
    COMPLETED = "האלבומים נשלחו לאורחים"
