from pydantic import Field

from src.models.base import ApiModel


class ImageMinSize(ApiModel):
    digital_px: int | None = Field(default=None, alias="digitalPx")
    print_inches: float | None = Field(default=None, alias="printInches")


class ImageAssetMetadata(ApiModel):
    filename: str
    title: str | None = None
    description: str = ""
    section: str | None = None
    usage: str = "reference"
    asset_type: str | None = Field(default=None, alias="assetType")
    variant: str | None = None
    colourway: str | None = None
    approved_backgrounds: list[str] = Field(default_factory=list, alias="approvedBackgrounds")
    approved_use_cases: list[str] = Field(default_factory=list, alias="approvedUseCases")
    restrictions: list[str] = Field(default_factory=list)
    min_size: ImageMinSize | None = Field(default=None, alias="minSize")
    clearspace_rule: str | None = Field(default=None, alias="clearspaceRule")
    tags: list[str] = Field(default_factory=list)
    priority: int | None = None
    role: str | None = None


class ImageManifest(ApiModel):
    version: str | None = "1.0"
    standard_id: str | None = Field(default=None, alias="standardId")
    assets: list[ImageAssetMetadata] = Field(default_factory=list)


class MasterImageManifestEntry(ApiModel):
    content_id: str | None = Field(default=None, alias="contentId")
    title: str | None = None
    content_path: str | None = Field(default=None, alias="contentPath")
    image_path: str | None = Field(default=None, alias="imagePath")
    manifest_path: str | None = Field(default=None, alias="manifestPath")
    count: int | None = None
    assets: list[ImageAssetMetadata] = Field(default_factory=list)


class MasterImageManifest(ApiModel):
    version: str | None = "1.0"
    generated_at: str | None = Field(default=None, alias="generatedAt")
    root: str | None = None
    directories: int | None = None
    assets: int | None = None
    entries: list[MasterImageManifestEntry] = Field(default_factory=list)
