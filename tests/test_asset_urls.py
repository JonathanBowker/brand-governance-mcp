from datetime import UTC, datetime, timedelta

from src.utils.asset_urls import build_asset_url, verify_asset_signature


def test_asset_url_round_trip():
    bucket = "https://brand-store.lon1.digitaloceanspaces.com/brand-pwc/"
    path = "brand-pwc/advanced-user/standards/logo/images/logo.png"
    url = build_asset_url(bucket, path, 3600)
    assert "/brand-governance-asset?" in url


def test_verify_asset_signature_rejects_expired():
    bucket = "https://brand-store.lon1.digitaloceanspaces.com/brand-pwc/"
    path = "brand-pwc/advanced-user/standards/logo/images/logo.png"
    expires = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    assert verify_asset_signature(bucket, path, expires, "bad") is False
