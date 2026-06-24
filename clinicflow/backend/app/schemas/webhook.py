from typing import Optional

from pydantic import BaseModel


class WebhookPayload(BaseModel):
    event: str
    session_id: Optional[int] = None
    payload: Optional[dict] = None


class WebhookResponse(BaseModel):
    status: str
    message: str
