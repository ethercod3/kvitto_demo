# Kvitto Payment API

Тестовый API приема платежей на FastAPI. Все денежные значения передаются и хранятся в целых копейках.

## Быстрый запуск через Docker

```bash
WEBHOOK_SECRET=change-me docker compose up --build
```

После запуска доступны API на `http://localhost:8000`, Swagger UI на `http://localhost:8000/docs` и healthcheck на `http://localhost:8000/health`.

## Локальный запуск

Нужны Python 3.11+ и [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Без `DATABASE_URL` используется локальная SQLite `kvitto.db`. Для PostgreSQL задайте URL вида `postgresql+asyncpg://user:password@host:5432/database`. Переменные перечислены в `.env.example`.

## Проверки

```bash
uv run ruff check .
uv run pytest
```

## Правила API

- Тарифы: Basic — `990000`, Standard — `1990000`, Premium — `2990000` копеек.
- Промокод `KVITTO10` без учета регистра дает скидку 10%.
- Рассрочка доступна на 3, 6 или 12 месяцев. Остаток копеек распределяется по первым платежам.
- Повторный `POST /payments` с тем же `Idempotency-Key` возвращает существующий платеж с HTTP 200.
- Переходы статуса: `pending -> succeeded`, `pending -> failed`, `succeeded -> refunded`.
- Банк подписывает точное тело вебхука HMAC-SHA256 с `WEBHOOK_SECRET`; hex-подпись передается в `X-Signature`.

## Примеры запросов

```bash
curl http://localhost:8000/tariffs

curl -X POST http://localhost:8000/payments \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: order-42" \
  -d '{"tariff_id":2,"email":"student@example.com","method":"installment","installment_months":3,"promo_code":"kvitto10"}'

curl http://localhost:8000/payments/PAYMENT_ID

curl "http://localhost:8000/payments?email=student@example.com&status=pending"
```

Подписанный вебхук можно отправить так:

```bash
BODY='{"payment_id":"PAYMENT_ID","status":"succeeded"}'
SIGNATURE=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" -hex | sed 's/^.* //')
curl -X POST http://localhost:8000/webhooks/bank \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$BODY"
```

## Основные эндпоинты

- `GET /tariffs`
- `POST /payments`
- `GET /payments/{id}`
- `POST /webhooks/bank`
- `GET /payments?email=...&status=...`
