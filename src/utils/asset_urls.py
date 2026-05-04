import base64
import hmac
import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import PurePosixPath
from urllib.parse import quote

from src.config import settings


def _secret() -> str:
    return settings.asset_signing_secret or settings.s3_secret_key or settings.keys_secret_key or ""


def asset_route_path() -> str:
    return f"{settings.mcp_path}-asset"


def _sign(bucket_uri: str, path: str, expires: str) -> str:
    payload = f"{bucket_uri}\n{path}\n{expires}".encode("utf-8")
    return hmac.new(_secret().encode("utf-8"), payload, sha256).hexdigest()


def _compact_payload(bucket_uri: str, path: str, expires: str) -> str:
    return json.dumps({"b": bucket_uri, "p": path, "e": expires}, separators=(",", ":"))


def _sign_compact_payload(payload: str) -> str:
    return hmac.new(_secret().encode("utf-8"), payload.encode("utf-8"), sha256).hexdigest()


def _encode_payload(payload: str) -> str:
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8").rstrip("=")


def _decode_payload(token: str) -> str | None:
    padding = "=" * (-len(token) % 4)
    try:
        return base64.urlsafe_b64decode(f"{token}{padding}".encode("utf-8")).decode("utf-8")
    except Exception:
        return None


def build_asset_url(bucket_uri: str, path: str, expiry_seconds: int) -> str:
    expires_at = (datetime.now(UTC) + timedelta(seconds=expiry_seconds)).isoformat()
    payload = _compact_payload(bucket_uri, path, expires_at)
    asset = _encode_payload(payload)
    sig = _sign_compact_payload(payload)
    token = f"{asset}.{sig}"
    filename = quote(PurePosixPath(path).name or "asset", safe="")
    return f"{settings.public_base_url.rstrip('/')}{asset_route_path()}/{token}/{filename}"


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


def resolve_asset_token(asset: str, sig: str) -> tuple[str, str, str] | None:
    if not _secret() or not asset or not sig:
        return None
    payload = _decode_payload(asset)
    if not payload:
        return None
    expected = _sign_compact_payload(payload)
    if not hmac.compare_digest(expected, sig):
        return None
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError:
        return None
    bucket_uri = decoded.get("b", "")
    path = decoded.get("p", "")
    expires = decoded.get("e", "")
    if not bucket_uri or not path or not expires:
        return None
    try:
        expires_at = datetime.fromisoformat(expires)
    except ValueError:
        return None
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC):
        return None
    return bucket_uri, path, expires


def resolve_asset_path_token(token: str) -> tuple[str, str, str] | None:
    asset, separator, sig = token.rpartition(".")
    if not separator:
        return None
    return resolve_asset_token(asset, sig)
