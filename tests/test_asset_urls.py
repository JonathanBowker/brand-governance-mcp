from datetime import UTC, datetime, timedelta

from urllib.parse import urlparse

from src.utils.asset_urls import build_asset_url, resolve_asset_path_token, verify_asset_signature


def test_asset_url_round_trip():
    bucket = "https://brand-store.lon1.digitaloceanspaces.com/brand-pwc/"
    path = "brand-pwc/advanced-user/standards/logo/images/logo.png"
    url = build_asset_url(bucket, path, 3600)
    parsed = urlparse(url)
    assert "/brand-governance-asset/" in parsed.path
    assert parsed.query == ""
    assert parsed.path.endswith("/logo.png")
    token = parsed.path.split("/brand-governance-asset/", 1)[1].split("/", 1)[0]
    _asset, _separator, sig = token.rpartition(".")
    assert len(sig) == 32
    resolved = resolve_asset_path_token(token)
    assert resolved is not None
    assert resolved[0] == bucket
    assert resolved[1] == path


def test_verify_asset_signature_rejects_expired():
    bucket = "https://brand-store.lon1.digitaloceanspaces.com/brand-pwc/"
    path = "brand-pwc/advanced-user/standards/logo/images/logo.png"
    expires = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    assert verify_asset_signature(bucket, path, expires, "bad") is False
