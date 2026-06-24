import pytest
from app.core.db import engine, Base

# Ensure tables exist before any tests run
# Required because TestClient in this starlette version doesn't trigger lifespan
Base.metadata.create_all(bind=engine)
