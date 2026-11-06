import pytest

from loyalty.entities import LoyaltyStatus, tier_for
from loyalty.service import LoyaltyService

from .conftest import TEST_USER


@pytest.mark.parametrize(
    ("count", "status", "discount"),
    [
        (0, LoyaltyStatus.BRONZE, 5),
        (9, LoyaltyStatus.BRONZE, 5),
        (10, LoyaltyStatus.SILVER, 7),
        (19, LoyaltyStatus.SILVER, 7),
        (20, LoyaltyStatus.GOLD, 10),
        (25, LoyaltyStatus.GOLD, 10),
    ],
)
def test_tier_thresholds(count: int, status: LoyaltyStatus, discount: int) -> None:
    assert tier_for(count) == (status, discount)


async def test_seeded_user_is_gold(service: LoyaltyService) -> None:
    loyalty = await service.get_or_create(TEST_USER)

    assert (loyalty.reservation_count, loyalty.status, loyalty.discount) == (25, LoyaltyStatus.GOLD, 10)


async def test_unknown_user_is_created_as_bronze(service: LoyaltyService) -> None:
    loyalty = await service.get_or_create("Someone New")

    assert (loyalty.reservation_count, loyalty.status, loyalty.discount) == (0, LoyaltyStatus.BRONZE, 5)


async def test_booking_increments_counter(service: LoyaltyService) -> None:
    updated = await service.change_count(TEST_USER, 1)

    assert updated.reservation_count == 26
    assert updated.status == LoyaltyStatus.GOLD


async def test_cancel_decrements_counter(service: LoyaltyService) -> None:
    await service.change_count(TEST_USER, 1)
    updated = await service.change_count(TEST_USER, -1)

    assert updated.reservation_count == 25


async def test_status_is_downgraded_when_counter_drops(service: LoyaltyService) -> None:
    """Уровень понижается, если счётчик стал ниже границы: 20 -> 19 даёт SILVER."""
    for _ in range(6):
        await service.change_count(TEST_USER, -1)

    loyalty = await service.get_or_create(TEST_USER)
    assert loyalty.reservation_count == 19
    assert (loyalty.status, loyalty.discount) == (LoyaltyStatus.SILVER, 7)


async def test_counter_never_goes_negative(service: LoyaltyService) -> None:
    loyalty = await service.change_count("Someone New", -1)

    assert loyalty.reservation_count == 0
    assert loyalty.status == LoyaltyStatus.BRONZE
