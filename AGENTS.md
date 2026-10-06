# Repository instructions

- Use Python 3.11+, FastAPI, Pydantic v2 and SQLAlchemy 2.x async APIs.
- Represent every monetary value as integer kopecks. Never use `float` for money.
- Keep business rules in `app/services`; keep HTTP parsing and status codes in routes.
- Preserve the documented status transition graph and database-backed idempotency.
- Add or update pytest coverage for every behavior change.
- Before committing, run `uv run ruff check .` and `uv run pytest`.
- Apply schema changes through Alembic migrations.
- Never commit `.env`, credentials, local databases, caches or generated artifacts.
