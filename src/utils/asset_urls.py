import base64
import hmac
import json
import zlib
from datetime import UTC, datetime, timedelta
from hashlib import md5, sha256
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


def _compact_payload(bucket_uri: str, path: str, expires_at: datetime) -> str:
    return json.dumps({"b": bucket_uri, "p": path, "x": int(expires_at.timestamp())}, separators=(",", ":"))


def _sign_compact_payload(payload: str) -> str:
    return hmac.new(_secret().encode("utf-8"), payload.encode("utf-8"), md5).hexdigest()


def _legacy_compact_signatures(payload: str) -> set[str]:
    digest = hmac.new(_secret().encode("utf-8"), payload.encode("utf-8"), sha256).digest()
    return {
        hmac.new(_secret().encode("utf-8"), payload.encode("utf-8"), sha256).hexdigest(),
        base64.urlsafe_b64encode(digest[:16]).decode("utf-8").rstrip("="),
    }


def _encode_payload(payload: str) -> str:
    compressed = zlib.compress(payload.encode("utf-8"), level=9)
    return base64.urlsafe_b64encode(compressed).decode("utf-8").rstrip("=")


def _decode_payload(token: str) -> str | None:
    padding = "=" * (-len(token) % 4)
    try:
        raw = base64.urlsafe_b64decode(f"{token}{padding}".encode("utf-8"))
        try:
            return zlib.decompress(raw).decode("utf-8")
        except zlib.error:
            return raw.decode("utf-8")
    except Exception:
        return None


def build_asset_url(bucket_uri: str, path: str, expiry_seconds: int) -> str:
    expires_dt = datetime.now(UTC) + timedelta(seconds=expiry_seconds)
    payload = _compact_payload(bucket_uri, path, expires_dt)
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
    if not hmac.compare_digest(expected, sig) and not any(
        hmac.compare_digest(legacy_expected, sig) for legacy_expected in _legacy_compact_signatures(payload)
    ):
        return None
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError:
        return None
    bucket_uri = decoded.get("b", "")
    path = decoded.get("p", "")
    expires = decoded.get("e", "")
    expires_timestamp = decoded.get("x")
    if not bucket_uri or not path or not (expires or expires_timestamp):
        return None
    try:
        if expires_timestamp:
            expires_at = datetime.fromtimestamp(int(expires_timestamp), UTC)
            expires = expires_at.isoformat()
        else:
            expires_at = datetime.fromisoformat(expires)
    except (TypeError, ValueError):
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
