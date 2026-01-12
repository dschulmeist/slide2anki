"""Application settings routes.

The worker runs in a separate Docker container, so it cannot see browser localStorage.
This router persists the selected model provider + model identifier in Postgres so
both the API and the worker can resolve the same runtime configuration.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.session import get_db
from app.schemas.api import AppSettingsResponse, AppSettingsUpdate

router = APIRouter()


async def _get_or_create_settings(db: AsyncSession) -> models.AppSetting:
    """Return the singleton settings row, creating it if missing."""
    result = await db.execute(select(models.AppSetting).limit(1))
    settings_row = result.scalar_one_or_none()
    if settings_row:
        return settings_row

    settings_row = models.AppSetting()
    db.add(settings_row)
    await db.commit()
    await db.refresh(settings_row)
    return settings_row


@router.get("/settings", response_model=AppSettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)) -> AppSettingsResponse:
    """Get persisted application settings (API keys are masked)."""
    settings_row = await _get_or_create_settings(db)
    return AppSettingsResponse.model_validate(settings_row)


@router.put("/settings", response_model=AppSettingsResponse)
async def update_settings(
    payload: AppSettingsUpdate,
    db: AsyncSession = Depends(get_db),
) -> AppSettingsResponse:
    """Update persisted application settings.

    Notes:
        - `api_key` is treated as write-only.
        - Sending an empty string clears the stored key.
    """
    settings_row = await _get_or_create_settings(db)
    settings_row.provider = payload.provider
    settings_row.model = payload.model
    settings_row.base_url = payload.base_url

    if payload.api_key is not None:
        settings_row.api_key = payload.api_key or None
        settings_row.api_key_present = bool(settings_row.api_key)

    db.add(settings_row)
    await db.commit()
    await db.refresh(settings_row)
    return AppSettingsResponse.model_validate(settings_row)

