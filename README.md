# Kvitto Payment API

Тестовый API приема платежей на FastAPI. Все денежные значения передаются и хранятся в целых копейках.

## Запуск через Docker Compose

Нужны Docker Desktop или Docker Engine с Compose. Секрет вебхука передается через окружение и не должен попадать в Git.

### Bash

```bash
export WEBHOOK_SECRET='replace-with-a-long-random-secret'
docker compose up --build
```

### Nushell

```nu
$env:WEBHOOK_SECRET = 'replace-with-a-long-random-secret'
docker compose up --build
```

Compose поднимает PostgreSQL, ожидает его healthcheck, применяет Alembic-миграции и запускает API. После запуска доступны:

- API: `http://localhost:8000`;
- Swagger UI: `http://localhost:8000/docs`;
- OpenAPI: `http://localhost:8000/openapi.json`;
- healthcheck: `http://localhost:8000/health`.

Запуск в фоне и просмотр логов:

```bash
docker compose up --build --detach --wait
docker compose logs --follow api
```

Остановка с сохранением данных PostgreSQL:

```bash
docker compose down
```

Для полного удаления тестовой базы используйте `docker compose down --volumes`. Эта команда безвозвратно удаляет Compose volume с данными.

## Локальный запуск без Docker

Нужны Python 3.11+ и [uv](https://docs.astral.sh/uv/).

По умолчанию приложение использует SQLite-файл `kvitto.db`. Секрет задайте только в окружении.

### Bash

```bash
uv sync
export WEBHOOK_SECRET='replace-with-a-long-random-secret'
export DATABASE_URL='sqlite+aiosqlite:///./kvitto.db'
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

### Nushell

```nu
uv sync
$env:WEBHOOK_SECRET = 'replace-with-a-long-random-secret'
$env:DATABASE_URL = 'sqlite+aiosqlite:///./kvitto.db'
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Для внешнего PostgreSQL используйте URL вида `postgresql+asyncpg://user:password@host:5432/database`. Перечень переменных есть в `.env.example`; реальные `.env` и секреты коммитить нельзя.

## Проверки

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run alembic check
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

## Безопасная подпись банковского вебхука

`X-Signature` — это hex-представление HMAC-SHA256 от точных байтов HTTP-тела. Критически важно сначала один раз сериализовать JSON, затем подписать полученные байты и отправить те же байты через `content`. Если после вычисления HMAC снова передать объект через `json=...`, HTTP-клиент может изменить пробелы или порядок полей, и подпись перестанет совпадать.

### Python-клиент

```python
import hashlib
import hmac
import json
import os

import httpx

payload = {
    "payment_id": "PAYMENT_ID",
    "status": "succeeded",
}

body = json.dumps(
    payload,
    ensure_ascii=False,
    separators=(",", ":"),
).encode("utf-8")

secret = os.environ["WEBHOOK_SECRET"].encode("utf-8")
signature = hmac.new(secret, body, hashlib.sha256).hexdigest()

response = httpx.post(
    "http://localhost:8000/webhooks/bank",
    content=body,
    headers={
        "Content-Type": "application/json",
        "X-Signature": signature,
    },
    timeout=10,
)
response.raise_for_status()
print(response.json())
```

Запуск примера должен происходить с тем же `WEBHOOK_SECRET`, с которым запущен API. В проекте сервер вычисляет HMAC от `await request.body()` и сравнивает подписи через `hmac.compare_digest`, а не через обычный `==`. Это снижает риск атак по времени сравнения.

### Bash и curl

```bash
BODY='{"payment_id":"PAYMENT_ID","status":"succeeded"}'
SIGNATURE=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" -hex | sed 's/^.* //')
curl -X POST http://localhost:8000/webhooks/bank \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$BODY"
```

### Swagger UI

На странице `/docs` над Swagger UI есть поле `Webhook secret`. Значение хранится только в памяти текущей вкладки. При отправке `POST /webhooks/bank` интерфейс подписывает фактическое тело запроса и устанавливает `X-Signature` автоматически.

### Правила безопасности

- Передавайте секрет только через переменные окружения или менеджер секретов; не храните его в коде, `.env` в Git, логах или скриншотах.
- Используйте длинный случайный секрет и отдельные значения для разработки, тестов и production.
- В production отправляйте вебхуки только по HTTPS: HMAC подтверждает целостность и отправителя, но не шифрует тело.
- Подписывайте и проверяйте исходные байты тела, не разобранный и повторно сериализованный JSON.
- На сервере сравнивайте подписи через `hmac.compare_digest`.
- Текущий контракт из ТЗ не защищает от повторной отправки корректно подписанного тела. Для production-протокола стоит дополнительно подписывать timestamp и уникальный event ID, отклонять старые timestamp и уже обработанные event ID.

## Основные эндпоинты

- `GET /tariffs`
- `POST /payments`
- `GET /payments/{id}`
- `POST /webhooks/bank`
- `GET /payments?email=...&status=...`
