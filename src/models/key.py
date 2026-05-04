from datetime import datetime

from pydantic import Field

from src.models.base import ApiModel


class AccessControl(ApiModel):
    standards: bool = False
    toolkits: bool = False
    asset_library: bool = Field(False, alias="assetLibrary")
    yaml_sidecars: bool = Field(False, alias="yamlSidecars")
    json_tokens: bool = Field(False, alias="jsonTokens")
    search_integration: bool = Field(False, alias="searchIntegration")


class Billing(ApiModel):
    layer: int | None = None
    currency: str | None = None
    invoiced: bool | None = None
    amount: int | float | None = None


class ClientKey(ApiModel):
    client_id: str = Field(alias="clientId")
    client_name: str = Field(alias="clientName")
    key_hash: str = Field(alias="keyHash")
    key_hint: str | None = Field(default=None, alias="keyHint")
    tier: int
    label: str | None = None
    created: datetime
    expires: datetime
    ttl_days: int | None = Field(default=None, alias="ttlDays")
    status: str
    mcp_endpoint: str = Field(alias="mcpEndpoint")
    bucket_uri: str = Field(alias="bucketUri")
    index_file: str = Field(alias="indexFile")
    access_control: AccessControl = Field(alias="accessControl")
    watermark: bool = True
    assets_redacted: bool = Field(default=False, alias="assetsRedacted")
    billing: Billing | None = None
