from typing import Any

from src.models.base import ApiModel


class ErrorResponse(ApiModel):
    error: str
    message: str
    code: int
    upgrade_url: str | None = None
    details: dict[str, Any] | None = None


class ToolResponse(ApiModel):
    ok: bool = True
    data: dict[str, Any] | list[Any] | str | None = None
    error: ErrorResponse | None = None
