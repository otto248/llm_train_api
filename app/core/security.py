from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from app.core.config import Settings
from app.common.deps import get_settings_dependency


def verify_api_key(
    request: Request,
    settings: Settings = Depends(get_settings_dependency),
) -> None:
    expected = settings.admin_api_key
    if not expected:
        return
    provided = request.headers.get(settings.api_key_header)
    if provided != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
