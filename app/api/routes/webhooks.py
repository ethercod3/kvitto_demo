import hashlib
import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.models.payment import Payment
from app.schemas.payment import WebhookRequest, WebhookResponse
from app.services.payments import transition_is_allowed

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/bank", response_model=WebhookResponse)
async def bank_webhook(
    request: Request,
    payload: WebhookRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    signature: Annotated[str | None, Header(alias="X-Signature")] = None,
) -> WebhookResponse | JSONResponse:
    expected = hmac.new(
        settings.webhook_secret.encode(), await request.body(), hashlib.sha256
    ).hexdigest()
    if signature is None or not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payment = await session.get(Payment, payload.payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    if not transition_is_allowed(payment.status, payload.status):
        return JSONResponse(status_code=409, content={"error": "invalid_transition"})

    payment.status = payload.status
    await session.commit()
    return WebhookResponse(result="ok")
