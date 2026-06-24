from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.db import Base, engine
from app.models.provider_schedule import ProviderSchedule  # noqa: F401
from app.models.conversation_audit_log import ConversationAuditLog  # noqa: F401
from app.services.availability_service import seed_default_providers
from app.core.db import SessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_default_providers(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="ClinicFlow AI",
    description="Call-first clinic voice workflow backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
