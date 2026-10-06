import hashlib
import hmac
import json
import uuid

import pytest
from httpx import AsyncClient

from app.core.config import settings


async def create_payment(
    client: AsyncClient,
    *,
    email: str = "student@example.com",
    method: str = "card",
    promo_code: str | None = None,
    installment_months: int | None = None,
    idempotency_key: str | None = None,
):
    body: dict[str, object] = {"tariff_id": 2, "email": email, "method": method}
    if promo_code is not None:
        body["promo_code"] = promo_code
    if installment_months is not None:
        body["installment_months"] = installment_months
    headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
    return await client.post("/payments", json=body, headers=headers)


async def signed_webhook(client: AsyncClient, payload: dict[str, str], valid: bool = True):
    body = json.dumps(payload, separators=(",", ":")).encode()
    signature = hmac.new(settings.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    if not valid:
        signature = "0" * 64
    return await client.post(
        "/webhooks/bank",
        content=body,
        headers={"Content-Type": "application/json", "X-Signature": signature},
    )


@pytest.mark.asyncio
async def test_docs_can_sign_webhook_requests(client: AsyncClient) -> None:
    response = await client.get("/docs")

    assert response.status_code == 200
    assert 'id="webhook-secret"' in response.text
    assert "requestInterceptor: signWebhookRequest" in response.text
    assert 'request.headers["X-Signature"] = signature' in response.text
    assert 'url.pathname !== "/webhooks/bank"' in response.text
    assert settings.webhook_secret not in response.text


@pytest.mark.asyncio
async def test_openapi_remains_available(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    assert "/webhooks/bank" in response.json()["paths"]


@pytest.mark.asyncio
async def test_tariffs_are_seeded(client: AsyncClient) -> None:
    response = await client.get("/tariffs")

    assert response.status_code == 200
    assert response.json() == [
        {"id": 1, "title": "Basic", "price": 990_000},
        {"id": 2, "title": "Standard", "price": 1_990_000},
        {"id": 3, "title": "Premium", "price": 2_990_000},
    ]


@pytest.mark.asyncio
async def test_create_payment_without_promo(client: AsyncClient) -> None:
    response = await create_payment(client)

    assert response.status_code == 201
    assert response.json()["amount"] == 1_990_000
    assert response.json()["discount"] == 0
    assert response.json()["status"] == "pending"
    assert response.json()["schedule"] is None


@pytest.mark.asyncio
async def test_lowercase_promo_code(client: AsyncClient) -> None:
    response = await create_payment(client, promo_code="kvitto10")

    assert response.status_code == 201
    assert response.json()["amount"] == 1_791_000
    assert response.json()["discount"] == 199_000


@pytest.mark.asyncio
async def test_unknown_promo_uses_standard_validation_error(client: AsyncClient) -> None:
    response = await create_payment(client, promo_code="nope")

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


@pytest.mark.asyncio
@pytest.mark.parametrize("months", [3, 6, 12])
async def test_installment_schedule(client: AsyncClient, months: int) -> None:
    response = await create_payment(client, method="installment", installment_months=months)

    assert response.status_code == 201
    schedule = response.json()["schedule"]
    assert len(schedule) == months
    assert sum(schedule) == response.json()["amount"]
    assert schedule == sorted(schedule, reverse=True)


@pytest.mark.asyncio
async def test_installment_months_validation(client: AsyncClient) -> None:
    missing = await create_payment(client, method="installment")
    invalid = await create_payment(client, method="installment", installment_months=5)
    unexpected = await create_payment(client, method="card", installment_months=3)

    assert missing.status_code == 422
    assert invalid.status_code == 422
    assert unexpected.status_code == 422


@pytest.mark.asyncio
async def test_idempotency_returns_same_payment(client: AsyncClient) -> None:
    first = await create_payment(client, idempotency_key="checkout-42")
    second = await create_payment(client, idempotency_key="checkout-42")

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]


@pytest.mark.asyncio
async def test_get_unknown_payment(client: AsyncClient) -> None:
    response = await client.get(f"/payments/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_signed_webhook_and_forbidden_transition(client: AsyncClient) -> None:
    payment = (await create_payment(client)).json()
    success = await signed_webhook(client, {"payment_id": payment["id"], "status": "succeeded"})
    forbidden = await signed_webhook(client, {"payment_id": payment["id"], "status": "failed"})
    stored = await client.get(f"/payments/{payment['id']}")

    assert success.status_code == 200
    assert success.json() == {"result": "ok"}
    assert forbidden.status_code == 409
    assert forbidden.json() == {"error": "invalid_transition"}
    assert stored.json()["status"] == "succeeded"


@pytest.mark.asyncio
async def test_webhook_rejects_invalid_signature(client: AsyncClient) -> None:
    payment = (await create_payment(client)).json()
    response = await signed_webhook(
        client, {"payment_id": payment["id"], "status": "succeeded"}, valid=False
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_webhook_unknown_payment(client: AsyncClient) -> None:
    response = await signed_webhook(
        client, {"payment_id": str(uuid.uuid4()), "status": "succeeded"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_payment_filters(client: AsyncClient) -> None:
    first = (await create_payment(client, email="one@example.com")).json()
    await create_payment(client, email="two@example.com")
    await signed_webhook(client, {"payment_id": first["id"], "status": "succeeded"})

    by_email = await client.get("/payments", params={"email": "one@example.com"})
    by_status = await client.get("/payments", params={"status": "pending"})
    combined = await client.get(
        "/payments", params={"email": "one@example.com", "status": "succeeded"}
    )

    assert [item["email"] for item in by_email.json()] == ["one@example.com"]
    assert all(item["status"] == "pending" for item in by_status.json())
    assert [item["id"] for item in combined.json()] == [first["id"]]
