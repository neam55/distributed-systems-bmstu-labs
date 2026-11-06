from dataclasses import replace
from uuid import UUID

from loyalty.entities import Loyalty, tier_for
from loyalty.repository import LoyaltyRepository


class InMemoryLoyaltyRepository(LoyaltyRepository):
    """Хранилище лояльности в памяти: тесты не требуют Postgres."""

    def __init__(self, initial: list[Loyalty] | None = None) -> None:
        self._storage: dict[str, Loyalty] = {}
        self._next_id = 1
        self._operations: set[tuple[str, UUID]] = set()
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

    async def change_count(
        self, username: str, delta: int, operation_uid: UUID | None = None
    ) -> Loyalty | None:
        found = self._storage.get(username)
        if found is None:
            return None
        if operation_uid is not None:
            key = (username, operation_uid)
            if key in self._operations:
                return replace(found)
            self._operations.add(key)
        reservation_count = max(0, found.reservation_count + delta)
        status, discount = tier_for(reservation_count)
        updated = replace(found, reservation_count=reservation_count, status=status, discount=discount)
        self._storage[username] = updated
        return replace(updated)
