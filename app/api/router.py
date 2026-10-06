from fastapi import APIRouter

from app.api.routes import payments, tariffs, webhooks

api_router = APIRouter()
api_router.include_router(tariffs.router)
api_router.include_router(payments.router)
api_router.include_router(webhooks.router)
