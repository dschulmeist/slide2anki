from fastapi import APIRouter

router = APIRouter()


@router.get("/auth/status")
async def auth_status() -> dict[str, str]:
    """Check authentication status.

    Note: This app is designed to run locally without authentication.
    This endpoint exists for future extensibility.
    """
    return {"status": "no_auth_required", "message": "Local mode - no authentication"}
