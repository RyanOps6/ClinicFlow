import pytest
from app.core.db import engine, Base

# Import all models to register them with Base.metadata before creating tables
from app.models.call_session import CallSession
from app.models.patient import Patient
from app.models.appointment import Appointment
from app.models.provider_schedule import ProviderSchedule

# Ensure tables exist before any tests run
# Required because TestClient in this starlette version doesn't trigger lifespan
Base.metadata.create_all(bind=engine)
