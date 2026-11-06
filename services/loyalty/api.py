"""REST API Loyalty Service."""

from fastapi import APIRouter

from loyalty.dependencies import LoyaltyServiceDep, UserName
from loyalty.schemas import LoyaltyChangeRequest, LoyaltyResponse

router = APIRouter(prefix="/api/v1/loyalty", tags=["Loyalty API"])


@router.get(
    "",
    response_model=LoyaltyResponse,
    summary="Получить информацию о статусе в программе лояльности",
)
async def get_loyalty(service: LoyaltyServiceDep, x_user_name: UserName) -> LoyaltyResponse:
    loyalty = await service.get_or_create(x_user_name)
    return LoyaltyResponse.model_validate(loyalty)


@router.patch(
    "",
    response_model=LoyaltyResponse,
    summary="Изменить счётчик бронирований",
    description="delta = +1 при новом бронировании, -1 при отмене. Уровень пересчитывается.",
)
async def change_loyalty(
    payload: LoyaltyChangeRequest,
    service: LoyaltyServiceDep,
    x_user_name: UserName,
) -> LoyaltyResponse:
    loyalty = await service.change_count(x_user_name, payload.delta, payload.operation_uid)
    return LoyaltyResponse.model_validate(loyalty)
