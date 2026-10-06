from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from starlette.responses import Response

from app.api.router import api_router
from app.core.config import settings
from app.db.seed import seed_tariffs
from app.db.session import SessionFactory
from app.docs import build_swagger_ui_html


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with SessionFactory() as session:
        await seed_tariffs(session)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan, docs_url=None)
app.include_router(api_router)


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui(request: Request) -> Response:
    return build_swagger_ui_html(request, app)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
