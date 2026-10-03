"""Health-check, по которому wait-script.sh определяет готовность сервиса."""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/manage/health", summary="Liveness probe")
async def health() -> dict[str, str]:
    return {"status": "UP"}
