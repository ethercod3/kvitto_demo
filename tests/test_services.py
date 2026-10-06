import pytest

from app.models.payment import PaymentStatus
from app.services.payments import (
    build_installment_schedule,
    calculate_amount,
    transition_is_allowed,
)


def test_calculate_amount_without_promo() -> None:
    assert calculate_amount(1_990_000, None) == (1_990_000, 0)


def test_calculate_amount_with_promo() -> None:
    assert calculate_amount(1_990_000, "KVITTO10") == (1_791_000, 199_000)


@pytest.mark.parametrize("months", [3, 6, 12])
def test_installment_schedule_preserves_every_kopeck(months: int) -> None:
    amount = 1_990_001
    schedule = build_installment_schedule(amount, months)

    assert len(schedule) == months
    assert sum(schedule) == amount
    assert all(isinstance(item, int) for item in schedule)
    assert max(schedule) - min(schedule) <= 1
    assert schedule == sorted(schedule, reverse=True)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (PaymentStatus.PENDING, PaymentStatus.SUCCEEDED),
        (PaymentStatus.PENDING, PaymentStatus.FAILED),
        (PaymentStatus.SUCCEEDED, PaymentStatus.REFUNDED),
    ],
)
def test_allowed_status_transitions(current: PaymentStatus, target: PaymentStatus) -> None:
    assert transition_is_allowed(current, target)


def test_forbidden_status_transition() -> None:
    assert not transition_is_allowed(PaymentStatus.FAILED, PaymentStatus.SUCCEEDED)
