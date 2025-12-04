from typing import Dict, List, Any, Optional
from pydantic import BaseModel

class EmailData(BaseModel):
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    recipient_name: Optional[str] = None
    recipient_email: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    attachment_filenames: Optional[List[str]] = None

class PredictRequest(BaseModel):
    emails: List[EmailData]

class PredictResponse(BaseModel):
    verdicts: List[Dict[str, Any]]