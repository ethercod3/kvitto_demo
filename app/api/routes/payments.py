import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.payment import Payment, PaymentStatus
from app.models.tariff import Tariff
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.services.payments import build_installment_schedule, calculate_amount

router = APIRouter(prefix="/payments", tags=["payments"])


async def find_by_idempotency_key(session: AsyncSession, key: str) -> Payment | None:
    return await session.scalar(select(Payment).where(Payment.idempotency_key == key))


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payload: PaymentCreate,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Payment:
    if idempotency_key is not None:
        idempotency_key = idempotency_key.strip()
        if not idempotency_key:
            raise HTTPException(status_code=422, detail="Idempotency-Key must not be empty")
        existing = await find_by_idempotency_key(session, idempotency_key)
        if existing is not None:
            response.status_code = status.HTTP_200_OK
            return existing

    tariff = await session.get(Tariff, payload.tariff_id)
    if tariff is None:
        raise HTTPException(status_code=404, detail="Tariff not found")

    amount, discount = calculate_amount(tariff.price, payload.promo_code)
    schedule = (
        build_installment_schedule(amount, payload.installment_months)
        if payload.installment_months is not None
        else None
    )
    payment = Payment(
        tariff_id=tariff.id,
        amount=amount,
        discount=discount,
        method=payload.method,
        installment_months=payload.installment_months,
        schedule=schedule,
        email=str(payload.email),
        idempotency_key=idempotency_key,
    )
    session.add(payment)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        if idempotency_key is None:
            raise
        existing = await find_by_idempotency_key(session, idempotency_key)
        if existing is None:
            raise
        response.status_code = status.HTTP_200_OK
        return existing

    await session.refresh(payment)
    return payment


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Payment:
    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.get("", response_model=list[PaymentResponse])
async def list_payments(
    session: Annotated[AsyncSession, Depends(get_session)],
    email: str | None = None,
    payment_status: Annotated[PaymentStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Payment]:
    statement = select(Payment)
    if email is not None:
        statement = statement.where(Payment.email == email)
    if payment_status is not None:
        statement = statement.where(Payment.status == payment_status)
    statement = statement.order_by(Payment.created_at, Payment.id).limit(limit).offset(offset)
    return list(await session.scalars(statement))
