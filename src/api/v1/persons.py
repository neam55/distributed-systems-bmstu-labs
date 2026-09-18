"""REST API над сущностью Person. Контракт — person-service.yaml."""

from fastapi import APIRouter, Path, Response, status

from src.api.dependencies import PersonServiceDep
from src.api.v1.schemas import (
    ErrorResponse,
    PersonRequest,
    PersonResponse,
    PersonUpdateRequest,
    ValidationErrorResponse,
)
from src.domain.entities import Person

router = APIRouter(prefix="/api/v1/persons", tags=["Person REST API operations"])

PersonId = Path(description="Идентификатор записи о человеке", ge=1, examples=[1])


@router.get(
    "",
    response_model=list[PersonResponse],
    summary="Get all Persons",
    description="Информация по всем людям.",
)
async def list_persons(service: PersonServiceDep) -> list[PersonResponse]:
    persons = await service.list_persons()
    return [PersonResponse.model_validate(person) for person in persons]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_class=Response,
    summary="Create new Person",
    description=(
        "Создание новой записи. Возвращает 201 с пустым телом и заголовком "
        "Location: /api/v1/persons/{personId}."
    ),
    responses={
        201: {"description": "Created new Person", "headers": {"Location": {"schema": {"type": "string"}}}},
        400: {"model": ValidationErrorResponse, "description": "Invalid data"},
    },
)
async def create_person(payload: PersonRequest, service: PersonServiceDep) -> Response:
    created = await service.create_person(Person(**payload.model_dump()))
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"Location": f"/api/v1/persons/{created.id}"},
    )


@router.get(
    "/{person_id}",
    response_model=PersonResponse,
    summary="Get Person by ID",
    description="Информация о человеке по идентификатору.",
    responses={404: {"model": ErrorResponse, "description": "Not found Person for ID"}},
)
async def get_person(service: PersonServiceDep, person_id: int = PersonId) -> PersonResponse:
    return PersonResponse.model_validate(await service.get_person(person_id))


@router.patch(
    "/{person_id}",
    response_model=PersonResponse,
    summary="Update Person by ID",
    description="Частичное обновление: переданные поля меняются, остальные сохраняются.",
    responses={
        400: {"model": ValidationErrorResponse, "description": "Invalid data"},
        404: {"model": ErrorResponse, "description": "Not found Person for ID"},
    },
)
async def update_person(
    payload: PersonUpdateRequest,
    service: PersonServiceDep,
    person_id: int = PersonId,
) -> PersonResponse:
    changes = payload.model_dump(exclude_unset=True)
    return PersonResponse.model_validate(await service.update_person(person_id, changes))


@router.delete(
    "/{person_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Remove Person by ID",
    description="Удаление записи о человеке.",
    responses={
        204: {"description": "Person for ID was removed"},
        404: {"model": ErrorResponse, "description": "Not found Person for ID"},
    },
)
async def delete_person(service: PersonServiceDep, person_id: int = PersonId) -> Response:
    await service.delete_person(person_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
