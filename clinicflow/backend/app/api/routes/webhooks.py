from fastapi import APIRouter

from app.schemas.webhook import WebhookPayload, WebhookResponse

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/voice", response_model=WebhookResponse)
def voice_webhook(payload: WebhookPayload):
    return WebhookResponse(
        status="received",
        message=f"Webhook event '{payload.event}' received. No real telephony integration yet.",
    )
