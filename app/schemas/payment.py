import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator

from app.models.payment import PaymentMethod, PaymentStatus


class PaymentCreate(BaseModel):
    tariff_id: int
    email: EmailStr
    method: PaymentMethod
    installment_months: int | None = None
    promo_code: str | None = None

    @field_validator("promo_code")
    @classmethod
    def validate_promo_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value.upper() != "KVITTO10":
            raise ValueError("unknown promo code")
        return value.upper()

    @model_validator(mode="after")
    def validate_installment(self) -> "PaymentCreate":
        if self.method == PaymentMethod.INSTALLMENT:
            if self.installment_months not in {3, 6, 12}:
                raise ValueError("installment_months must be 3, 6, or 12")
        elif self.installment_months is not None:
            raise ValueError("installment_months is only allowed for installment payments")
        return self


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: PaymentStatus
    tariff_id: int
    amount: int
    discount: int
    method: PaymentMethod
    installment_months: int | None
    schedule: list[int] | None
    email: EmailStr
    created_at: datetime


class WebhookRequest(BaseModel):
    payment_id: uuid.UUID
    status: PaymentStatus


class WebhookResponse(BaseModel):
    result: str
