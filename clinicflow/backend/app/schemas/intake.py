from typing import Optional

from pydantic import BaseModel


class IntakeData(BaseModel):
    full_name: Optional[str] = None
    symptoms: list[str] = []
    duration: Optional[str] = None
    reason_for_visit: Optional[str] = None
    insurance_provider: Optional[str] = None
