from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PatientResponse(BaseModel):
    id: int
    full_name: str
    phone: str
    dob_or_age_group: Optional[str] = None
    insurance_provider: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
