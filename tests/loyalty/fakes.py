from dataclasses import replace

from loyalty.entities import Loyalty, LoyaltyStatus
from loyalty.repository import LoyaltyRepository


class InMemoryLoyaltyRepository(LoyaltyRepository):
    """Хранилище лояльности в памяти: тесты не требуют Postgres."""

    def __init__(self, initial: list[Loyalty] | None = None) -> None:
        self._storage: dict[str, Loyalty] = {}
        self._next_id = 1
        for item in initial or []:
            self._storage[item.username] = replace(item, id=self._next_id)
            self._next_id += 1

    async def get(self, username: str) -> Loyalty | None:
        found = self._storage.get(username)
        return replace(found) if found is not None else None

    async def add(self, loyalty: Loyalty) -> Loyalty:
        stored = replace(loyalty, id=self._next_id)
        self._next_id += 1
        self._storage[stored.username] = stored
        return replace(stored)

    async def save_tier(
        self, username: str, reservation_count: int, status: LoyaltyStatus, discount: int
    ) -> Loyalty | None:
        found = self._storage.get(username)
        if found is None:
            return None
        updated = replace(found, reservation_count=reservation_count, status=status, discount=discount)
        self._storage[username] = updated
        return replace(updated)
