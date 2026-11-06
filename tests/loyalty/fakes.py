from dataclasses import replace
from uuid import UUID

from fastapi import HTTPException

from loyalty.entities import Loyalty, tier_for
from loyalty.repository import LoyaltyRepository


class InMemoryLoyaltyRepository(LoyaltyRepository):
    """Хранилище лояльности в памяти: тесты не требуют Postgres."""

    def __init__(self, initial: list[Loyalty] | None = None) -> None:
        self._storage: dict[str, Loyalty] = {}
        self._next_id = 1
        self._operations: dict[tuple[str, UUID], tuple[int, str]] = {}
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
                if self._operations[key][0] != delta:
                    raise HTTPException(status_code=409, detail="Loyalty operation payload conflict")
                return replace(found)
            self._operations[key] = (delta, "APPLIED")
        reservation_count = max(0, found.reservation_count + delta)
        status, discount = tier_for(reservation_count)
        updated = replace(found, reservation_count=reservation_count, status=status, discount=discount)
        self._storage[username] = updated
        return replace(updated)

    async def reverse_increment(self, username: str, operation_uid: UUID) -> Loyalty | None:
        found = self._storage.get(username)
        if found is None:
            return None
        key = (username, operation_uid)
        operation = self._operations.get(key)
        if operation is not None and operation[0] != 1:
            raise HTTPException(status_code=409, detail="Only booking increments can be reversed")
        if operation == (1, "APPLIED"):
            count = max(0, found.reservation_count - 1)
            status, discount = tier_for(count)
            found = replace(found, reservation_count=count, status=status, discount=discount)
            self._storage[username] = found
        self._operations[key] = (1, "REVERSED")
        return replace(found)
