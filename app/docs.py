from pathlib import Path

from fastapi import FastAPI, Request
from starlette.responses import Response
from starlette.templating import Jinja2Templates

SWAGGER_UI_VERSION = "5"
TEMPLATES_DIRECTORY = Path(__file__).parent / "templates"

templates = Jinja2Templates(directory=TEMPLATES_DIRECTORY)


def build_swagger_ui_html(request: Request, app: FastAPI) -> Response:
    return templates.TemplateResponse(
        request=request,
        name="swagger_ui.html",
        context={
            "openapi_url": app.openapi_url,
            "swagger_ui_version": SWAGGER_UI_VERSION,
            "title": f"{app.title} - Swagger UI",
        },
    )
