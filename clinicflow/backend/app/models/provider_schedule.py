from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from app.core.db import Base


class ProviderSchedule(Base):
    __tablename__ = "provider_schedules"

    id = Column(Integer, primary_key=True, index=True)
    provider_name = Column(String, nullable=False)
    day_of_week = Column(Integer, nullable=False)
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=False)
    slot_duration_minutes = Column(Integer, nullable=False, default=60)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
