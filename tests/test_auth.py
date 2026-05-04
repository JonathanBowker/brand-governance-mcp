import pytest

from src.auth import validate_key
from src.errors import KeyExpiredError, KeyInvalidError
from tests.conftest import EXPIRED_KEY, INVALID_STATUS_KEY, VALID_KEY


async def test_validate_key_success(s3_env):
    client = await validate_key(VALID_KEY)
    assert client.client_id == "pwc"
    assert client.access_control.standards is True


async def test_validate_key_expired(s3_env):
    with pytest.raises(KeyExpiredError):
        await validate_key(EXPIRED_KEY)


async def test_validate_key_invalid_status(s3_env):
    with pytest.raises(KeyInvalidError):
        await validate_key(INVALID_STATUS_KEY)


async def test_validate_key_missing(s3_env):
    with pytest.raises(KeyExpiredError):
        await validate_key("sk-brand-pwc-missing")
