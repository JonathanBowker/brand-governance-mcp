from dataclasses import dataclass
from typing import Any

from src.config import settings


class BrandMcpError(Exception):
    code = 500
    error = "server_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AccessDeniedError(BrandMcpError):
    code = 403
    error = "access_denied"


class KeyExpiredError(BrandMcpError):
    code = 403
    error = "trial_expired"


class KeyInvalidError(BrandMcpError):
    code = 401
    error = "invalid_key"


class NotFoundError(BrandMcpError):
    code = 404
    error = "not_found"


class CapabilityLockedError(AccessDeniedError):
    error = "capability_locked"


@dataclass(frozen=True)
class ErrorPayload:
    error: str
    message: str
    code: int
    upgrade_url: str | None = None
    details: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ok": False,
            "error": self.error,
            "message": self.message,
            "code": self.code,
        }
        if self.upgrade_url:
            payload["upgradeUrl"] = self.upgrade_url
        if self.details:
            payload["details"] = self.details
        return payload


def error_to_response(error: Exception) -> dict[str, Any]:
    if isinstance(error, KeyExpiredError):
        return ErrorPayload(
            error=error.error,
            message=error.message or f"Your trial period has ended. Contact {settings.support_email} to upgrade.",
            code=error.code,
            upgrade_url=settings.upgrade_url,
            details=error.details,
        ).as_dict()
    if isinstance(error, AccessDeniedError):
        return ErrorPayload(
            error=error.error,
            message=error.message,
            code=error.code,
            upgrade_url=settings.upgrade_url,
            details=error.details,
        ).as_dict()
    if isinstance(error, KeyInvalidError):
        return ErrorPayload(
            error=error.error,
            message=error.message,
            code=error.code,
            details=error.details,
        ).as_dict()
    if isinstance(error, NotFoundError):
        return ErrorPayload(
            error=error.error,
            message=error.message,
            code=error.code,
            details=getattr(error, "details", {}),
        ).as_dict()
    return ErrorPayload(
        error="server_error",
        message="An unexpected error occurred. Please contact support.",
        code=500,
    ).as_dict()


async def tool_error_boundary(coro):
    try:
        return await coro
    except Exception as exc:
        return error_to_response(exc)
