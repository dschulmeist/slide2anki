from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness_check() -> dict[str, str]:
    """Readiness check - verifies all dependencies are available."""
    # TODO: Check database, redis, minio connectivity
    return {"status": "ready"}
