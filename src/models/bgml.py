from typing import Any

from pydantic import Field

from src.models.base import ApiModel


class ImageInfo(ApiModel):
    path: str | None = None
    count: int | None = None


class StandardFile(ApiModel):
    markdown: str | None = None
    yaml: str | None = None
    json_file: str | None = Field(default=None, alias="json")
    images: ImageInfo | None = None
    screenshot: str | None = None


class IndexEntry(ApiModel):
    id: str
    category: str
    tier: str | None = None
    status: str
    name: str
    description: str
    files: StandardFile
    slug: str | None = None
    group: str | None = None
    key_rules: list[str] = Field(default_factory=list, alias="keyRules")
    related: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    version: str | None = None
    last_modified: str | None = Field(default=None, alias="lastModified")
    parent: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict, exclude=True)

    model_config = ApiModel.model_config | {"extra": "allow"}


class Standard(IndexEntry):
    tier: str | None = None


class BgmlIndex(ApiModel):
    version: str
    schema_: str | None = Field(default=None, alias="schema")
    meta: dict[str, Any]
    precedence: list[str] = Field(default_factory=list)
    standards: list[Standard] = Field(default_factory=list)
    collections: dict[str, list[IndexEntry]] = Field(default_factory=dict)
    stats: dict[str, Any] = Field(default_factory=dict)


class BgmlEnvelope(ApiModel):
    bgml: BgmlIndex


def parse_bgml(raw: str | bytes | dict[str, Any]) -> BgmlIndex:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    if isinstance(raw, str):
        env = BgmlEnvelope.model_validate_json(raw)
    else:
        env = BgmlEnvelope.model_validate(raw)
    return env.bgml
