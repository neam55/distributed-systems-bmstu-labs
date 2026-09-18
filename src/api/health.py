"""Health-check для healthCheckPath хостинга и для docker healthcheck."""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/manage/health", summary="Liveness probe")
async def health() -> dict[str, str]:
    return {"status": "UP"}
