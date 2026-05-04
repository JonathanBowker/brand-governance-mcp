import logging
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AA_", extra="ignore")

    s3_endpoint: str | None = None
    s3_region: str = "fra1"
    s3_access_key: str | None = Field(default=None, validation_alias=AliasChoices("DO_SPACES_KEY", "AA_S3_ACCESS_KEY"))
    s3_secret_key: str | None = Field(default=None, validation_alias=AliasChoices("DO_SPACES_SECRET", "AA_S3_SECRET_KEY"))
    keys_profile: str | None = None
    keys_region: str = "eu-west-2"
    keys_bucket: str = "aa-keys"
    keys_access_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AWS_ACCESS_KEY_ID", "AA_KEYS_ACCESS_KEY"),
    )
    keys_secret_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AWS_SECRET_ACCESS_KEY", "AA_KEYS_SECRET_KEY"),
    )
    keys_session_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AWS_SESSION_TOKEN", "AA_KEYS_SESSION_TOKEN"),
    )

    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8000
    mcp_path: str = "/brand-governance"
    mcp_transport: str = "http"

    log_level: str = "INFO"
    presign_expiry: int = 604800
    public_base_url: str = "https://advancedanalytica.co.uk"
    upgrade_url: str = "https://advancedanalytica.co.uk/brand-governance"
    support_email: str = "jonathan@advancedanalytica.co.uk"
    asset_signing_secret: str | None = Field(default=None, validation_alias=AliasChoices("AA_ASSET_SIGNING_SECRET"))


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return settings


settings = get_settings()
