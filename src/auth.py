import hmac
import logging
from datetime import UTC, datetime

from pydantic import ValidationError

from src.config import settings
from src.errors import AccessDeniedError, KeyExpiredError, KeyInvalidError
from src.models.key import ClientKey
from src.s3 import S3ObjectNotFound, get_key_object, key_object_exists
from src.utils.hash import key_hash_value, key_lookup_name

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def _log_validation(event: str, *, client_id: str | None, key_hint: str | None = None, detail: str = "") -> None:
    logger.info(
        "key_validation event=%s clientId=%s timestamp=%s keyHint=%s detail=%s",
        event,
        client_id or "unknown",
        _now().isoformat(),
        key_hint or "unknown",
        detail,
    )


async def _load_key_record(api_key: str) -> ClientKey:
    lookup_name = key_lookup_name(api_key)
    active_key = f"active/{lookup_name}"
    expired_key = f"expired/{lookup_name}"
    try:
        raw = await get_key_object(settings.keys_bucket, active_key)
    except S3ObjectNotFound:
        if await key_object_exists(settings.keys_bucket, expired_key):
            raw_expired = await get_key_object(settings.keys_bucket, expired_key)
            try:
                expired_record = ClientKey.model_validate_json(raw_expired)
                _log_validation("expired_record_found", client_id=expired_record.client_id, key_hint=expired_record.key_hint)
                raise KeyExpiredError(
                    "Trial period ended. Upgrade to Layer 2 for permanent governed brand access.",
                    details={"clientId": expired_record.client_id},
                )
            except ValidationError as exc:
                raise KeyExpiredError("Trial key has expired or is no longer available.") from exc
        _log_validation("key_not_found", client_id=None, detail="no active or expired key record")
        raise KeyExpiredError("Trial key has expired or is no longer available.") from None
    try:
        return ClientKey.model_validate_json(raw)
    except ValidationError as exc:
        _log_validation("key_parse_failed", client_id=None, detail=str(exc))
        raise KeyInvalidError("API key record is malformed. Contact support.") from exc


async def validate_key(api_key: str) -> ClientKey:
    if not api_key:
        _log_validation("missing_key", client_id=None)
        raise KeyInvalidError("API key is required.")

    client = await _load_key_record(api_key)
    expected_hash = key_hash_value(api_key)
    if not hmac.compare_digest(client.key_hash, expected_hash):
        _log_validation("hash_mismatch", client_id=client.client_id, key_hint=client.key_hint)
        raise KeyInvalidError("API key is invalid. Check your key and try again.")

    if client.status != "active":
        _log_validation("inactive_key", client_id=client.client_id, key_hint=client.key_hint, detail=client.status)
        raise KeyInvalidError("API key is not active.")

    expires = client.expires
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires <= _now():
        _log_validation("expired_key", client_id=client.client_id, key_hint=client.key_hint)
        raise KeyExpiredError(
            "Trial period ended. Upgrade to Layer 2 for permanent governed brand access.",
            details={"clientId": client.client_id, "expiredAt": expires.isoformat()},
        )

    _log_validation("success", client_id=client.client_id, key_hint=client.key_hint)
    return client


__all__ = ["validate_key", "AccessDeniedError", "KeyExpiredError", "KeyInvalidError"]
