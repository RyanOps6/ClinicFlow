from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.sessions import router as sessions_router
from app.api.routes.appointments import router as appointments_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.intake import router as intake_router
from app.api.routes.webhooks import router as webhooks_router
from app.api.routes.auth import router as auth_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(health_router)
api_router.include_router(sessions_router)
api_router.include_router(appointments_router)
api_router.include_router(dashboard_router)
api_router.include_router(intake_router)
api_router.include_router(webhooks_router)
