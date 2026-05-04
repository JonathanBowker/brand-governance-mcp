from src.config import settings
from src.s3 import _normalise_spaces_endpoint


def test_normalise_spaces_endpoint_to_region_root():
    assert _normalise_spaces_endpoint("https://brand-store.lon1.digitaloceanspaces.com") == (
        f"https://{settings.s3_region}.digitaloceanspaces.com"
    )


def test_normalise_spaces_endpoint_leaves_region_root_alone():
    assert _normalise_spaces_endpoint(f"https://{settings.s3_region}.digitaloceanspaces.com") == (
        f"https://{settings.s3_region}.digitaloceanspaces.com"
    )
