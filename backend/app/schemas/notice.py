from pydantic import BaseModel, EmailStr
from typing import List, Optional

class NoticeSend(BaseModel):
    detection_id: int
    recipient_email: EmailStr
    subject: str
    content: str
    attachments: Optional[List[str]] = None
