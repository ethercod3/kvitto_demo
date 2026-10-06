from app.models.payment import PaymentStatus

PROMO_DISCOUNT_PERCENT = 10

ALLOWED_TRANSITIONS: set[tuple[PaymentStatus, PaymentStatus]] = {
    (PaymentStatus.PENDING, PaymentStatus.SUCCEEDED),
    (PaymentStatus.PENDING, PaymentStatus.FAILED),
    (PaymentStatus.SUCCEEDED, PaymentStatus.REFUNDED),
}


def calculate_amount(price: int, promo_code: str | None) -> tuple[int, int]:
    discount = price * PROMO_DISCOUNT_PERCENT // 100 if promo_code else 0
    return price - discount, discount


def build_installment_schedule(amount: int, months: int) -> list[int]:
    payment, remainder = divmod(amount, months)
    return [payment + (index < remainder) for index in range(months)]


def transition_is_allowed(current: PaymentStatus, target: PaymentStatus) -> bool:
    return (current, target) in ALLOWED_TRANSITIONS
