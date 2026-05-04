import hmac
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from urllib.parse import urlencode

from src.config import settings


def _secret() -> str:
    return settings.asset_signing_secret or settings.s3_secret_key or settings.keys_secret_key or ""


def asset_route_path() -> str:
    return f"{settings.mcp_path}-asset"


def _sign(bucket_uri: str, path: str, expires: str) -> str:
    payload = f"{bucket_uri}\n{path}\n{expires}".encode("utf-8")
    return hmac.new(_secret().encode("utf-8"), payload, sha256).hexdigest()


def build_asset_url(bucket_uri: str, path: str, expiry_seconds: int) -> str:
    expires_at = (datetime.now(UTC) + timedelta(seconds=expiry_seconds)).isoformat()
    sig = _sign(bucket_uri, path, expires_at)
    query = urlencode({"bucket": bucket_uri, "path": path, "expires": expires_at, "sig": sig})
    return f"{settings.public_base_url.rstrip('/')}{asset_route_path()}?{query}"


def verify_asset_signature(bucket_uri: str, path: str, expires: str, sig: str) -> bool:
    if not _secret():
        return False
    try:
        expires_at = datetime.fromisoformat(expires)
    except ValueError:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC):
        return False
    expected = _sign(bucket_uri, path, expires)
    return hmac.compare_digest(expected, sig)
