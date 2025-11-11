"""De-identification API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI, HTTPException

from ...deid import build_deid_response
from ...models import DeidRequest, DeidResponse

router = APIRouter(prefix="/v1", tags=["deid"])


@router.post("/deidentify:test", response_model=DeidResponse)
def deidentify(req: DeidRequest) -> DeidResponse:
    """根据策略执行去标识化，并在策略不存在时返回错误。"""
    try:
        return build_deid_response(req)
    except KeyError as exc:
        policy_id = exc.args[0]
        raise HTTPException(status_code=400, detail=f"Unknown policy_id '{policy_id}'") from exc


def register_routes(app: FastAPI) -> None:
    """Register de-identification endpoints on the provided application."""

    app.include_router(router)
