import json

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

SWAGGER_UI_VERSION = "5"


def build_swagger_ui_html(app: FastAPI) -> HTMLResponse:
    title = json.dumps(f"{app.title} - Swagger UI")
    openapi_url = json.dumps(app.openapi_url)

    return HTMLResponse(
        f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{app.title} - Swagger UI</title>
  <link rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@{SWAGGER_UI_VERSION}/swagger-ui.css">
  <style>
    body {{ margin: 0; background: #fafafa; }}
    .webhook-signing {{
      align-items: center;
      background: #17202a;
      color: #fff;
      display: flex;
      flex-wrap: wrap;
      font-family: sans-serif;
      gap: 12px;
      padding: 12px 24px;
    }}
    .webhook-signing label {{ font-weight: 600; }}
    .webhook-signing input {{
      border: 1px solid #85929e;
      border-radius: 4px;
      min-width: 280px;
      padding: 7px 9px;
    }}
    .webhook-signing button {{
      background: #fff;
      border: 0;
      border-radius: 4px;
      cursor: pointer;
      padding: 7px 12px;
    }}
    #webhook-signing-status {{ color: #d5dbdb; font-size: 13px; }}
  </style>
</head>
<body>
  <div class="webhook-signing">
    <label for="webhook-secret">Webhook secret</label>
    <input id="webhook-secret" type="password" autocomplete="off"
           placeholder="Used only in this browser tab">
    <button id="clear-webhook-secret" type="button">Clear</button>
    <span id="webhook-signing-status">
      POST /webhooks/bank will be signed automatically
    </span>
  </div>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@{SWAGGER_UI_VERSION}/swagger-ui-bundle.js"></script>
  <script>
    const secretInput = document.getElementById("webhook-secret");
    const signingStatus = document.getElementById("webhook-signing-status");
    const encoder = new TextEncoder();

    document.getElementById("clear-webhook-secret").addEventListener("click", () => {{
      secretInput.value = "";
      signingStatus.textContent = "Webhook secret cleared";
    }});

    async function signWebhookRequest(request) {{
      const url = new URL(request.url, window.location.origin);
      const method = (request.method || "").toUpperCase();
      if (method !== "POST" || url.pathname !== "/webhooks/bank") {{
        return request;
      }}

      if (!secretInput.value) {{
        signingStatus.textContent = "Enter the webhook secret before sending";
        return request;
      }}

      const body = typeof request.body === "string"
        ? request.body
        : JSON.stringify(request.body ?? {{}});
      request.body = body;

      const key = await crypto.subtle.importKey(
        "raw",
        encoder.encode(secretInput.value),
        {{ name: "HMAC", hash: "SHA-256" }},
        false,
        ["sign"]
      );
      const signatureBytes = await crypto.subtle.sign("HMAC", key, encoder.encode(body));
      const signature = Array.from(new Uint8Array(signatureBytes))
        .map((byte) => byte.toString(16).padStart(2, "0"))
        .join("");

      request.headers = request.headers || {{}};
      request.headers["X-Signature"] = signature;
      signingStatus.textContent = "Webhook request signed for this body";
      return request;
    }}

    window.ui = SwaggerUIBundle({{
      url: {openapi_url},
      dom_id: "#swagger-ui",
      deepLinking: true,
      displayRequestDuration: true,
      requestInterceptor: signWebhookRequest,
      showMutatedRequest: true,
      presets: [
        SwaggerUIBundle.presets.apis,
        SwaggerUIBundle.SwaggerUIStandalonePreset
      ],
      layout: "BaseLayout"
    }});
    document.title = {title};
  </script>
</body>
</html>"""
    )
