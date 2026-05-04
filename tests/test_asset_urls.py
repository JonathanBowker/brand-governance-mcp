from datetime import UTC, datetime, timedelta

from urllib.parse import parse_qs, urlparse

from src.utils.asset_urls import build_asset_url, resolve_asset_token, verify_asset_signature


def test_asset_url_round_trip():
    bucket = "https://brand-store.lon1.digitaloceanspaces.com/brand-pwc/"
    path = "brand-pwc/advanced-user/standards/logo/images/logo.png"
    url = build_asset_url(bucket, path, 3600)
    assert "/brand-governance-asset?" in url
    query = parse_qs(urlparse(url).query)
    assert "asset" in query
    assert "sig" in query
    assert "bucket" not in query
    resolved = resolve_asset_token(query["asset"][0], query["sig"][0])
    assert resolved is not None
    assert resolved[0] == bucket
    assert resolved[1] == path


def test_verify_asset_signature_rejects_expired():
    bucket = "https://brand-store.lon1.digitaloceanspaces.com/brand-pwc/"
    path = "brand-pwc/advanced-user/standards/logo/images/logo.png"
    expires = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    assert verify_asset_signature(bucket, path, expires, "bad") is False
