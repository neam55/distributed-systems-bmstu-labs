import pytest

from src.core.exceptions import PersonNotFoundError
from src.domain.entities import Person
from src.domain.services import PersonService


async def test_create_person_assigns_id(service: PersonService) -> None:
    created = await service.create_person(Person(name="Ivan", age=31, address="Moscow", work="BMSTU"))

    assert created.id is not None
    assert (created.name, created.age, created.address, created.work) == (
        "Ivan",
        31,
        "Moscow",
        "BMSTU",
    )


async def test_get_missing_person_raises(service: PersonService) -> None:
    with pytest.raises(PersonNotFoundError) as exc_info:
        await service.get_person(404)

    assert exc_info.value.person_id == 404


async def test_partial_update_keeps_untouched_fields(service: PersonService) -> None:
    created = await service.create_person(Person(name="Ivan", age=31, address="Moscow", work="BMSTU"))
    assert created.id is not None

    updated = await service.update_person(created.id, {"name": "Petr", "address": "Tver"})

    assert updated.name == "Petr"
    assert updated.address == "Tver"
    assert updated.age == 31
    assert updated.work == "BMSTU"


async def test_delete_removes_person(service: PersonService) -> None:
    created = await service.create_person(Person(name="Ivan"))
    assert created.id is not None

    await service.delete_person(created.id)

    with pytest.raises(PersonNotFoundError):
        await service.get_person(created.id)
    with pytest.raises(PersonNotFoundError):
        await service.delete_person(created.id)


async def test_list_returns_all_created_persons(service: PersonService) -> None:
    await service.create_person(Person(name="Ivan"))
    await service.create_person(Person(name="Petr"))

    persons = await service.list_persons()

    assert sorted(person.name for person in persons) == ["Ivan", "Petr"]
