"""Image-listing tool for governed brand assets and manifests."""

import json
from pathlib import PurePosixPath

from fastmcp import FastMCP
from fastmcp.dependencies import CurrentHeaders

from src.auth import resolve_api_key, validate_key
from src.config import settings
from src.errors import NotFoundError, tool_error_boundary
from src.models.assets import ImageAssetMetadata, ImageManifest
from src.policy.entitlements import require_collection_access
from src.s3 import S3ObjectNotFound, get_object, list_objects, object_exists
from src.tools.common import find_entry, load_index
from src.utils.asset_urls import build_asset_url

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


async def _load_manifest(bucket_uri: str, images_path: str) -> list[ImageAssetMetadata]:
    """Load an optional image manifest and normalize it into asset metadata entries."""
    manifest_key = f"{images_path.rstrip('/')}/manifest.json"
    if not await object_exists(bucket_uri, manifest_key):
        return []
    try:
        raw = await get_object(bucket_uri, manifest_key)
        data = json.loads(raw)
        if isinstance(data, list):
            return [ImageAssetMetadata.model_validate(item) for item in data]
        if isinstance(data, dict):
            if "assets" in data:
                return ImageManifest.model_validate(data).assets
            if "images" in data:
                return [ImageAssetMetadata.model_validate(item) for item in data["images"]]
        return []
    except (json.JSONDecodeError, S3ObjectNotFound, ValueError):
        return []


async def run_brand_get_image_list(api_key: str, standard_id: str) -> dict:
    """Return signed image URLs and manifest metadata for an indexed content entry."""
    client = await validate_key(api_key)
    index = await load_index(client)
    standard = find_entry(index, standard_id)
    require_collection_access(client, standard.group)

    if not standard.files.images or not standard.files.images.path:
        raise NotFoundError(
            f"No image folder is listed for standard '{standard_id}'.",
            details={"standardId": standard_id},
        )

    images_path = standard.files.images.path.rstrip("/")
    keys = await list_objects(client.bucket_uri, images_path)
    manifest = await _load_manifest(client.bucket_uri, images_path)
    manifest_by_name = {item.filename: item for item in manifest if item.filename}

    images = []
    for key in keys:
        name = PurePosixPath(key).name
        if name == "manifest.json":
            continue
        if PurePosixPath(name).suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        item = manifest_by_name.get(name)
        image_url = build_asset_url(client.bucket_uri, key, settings.presign_expiry)
        images.append(
            {
                "filename": name,
                "title": item.title if item else None,
                "description": item.description if item else "",
                "usage": item.usage if item else "reference",
                "path": key,
                "watermark": client.watermark,
                "imageUrl": image_url,
                "url": image_url,
                "src": image_url,
                "thumbnailUrl": image_url,
                "alt": (item.title if item and item.title else name),
                "expiresInSeconds": settings.presign_expiry,
                "assetType": item.asset_type if item else None,
                "variant": item.variant if item else None,
                "colourway": item.colourway if item else None,
                "approvedBackgrounds": item.approved_backgrounds if item else [],
                "approvedUseCases": item.approved_use_cases if item else [],
                "restrictions": item.restrictions if item else [],
                "minSize": item.min_size.model_dump(by_alias=True) if item and item.min_size else None,
                "clearspaceRule": item.clearspace_rule if item else None,
                "tags": item.tags if item else [],
                "priority": item.priority if item else None,
                "role": item.role if item else None,
            }
        )

    return {
        "ok": True,
        "clientId": client.client_id,
        "standardId": standard.id,
        "group": standard.group,
        "imagePath": images_path,
        "count": len(images),
        "images": images,
    }


def register(mcp: FastMCP):
    """Register the image-list tool with the FastMCP server."""
    @mcp.tool(
        name="brand_get_image_list",
        description="List available brand images for a guidance item, including signed URLs and any approved asset metadata.",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    )
    async def brand_get_image_list(
        standard_id: str,
        api_key: str = "",
        headers: dict[str, str] = CurrentHeaders(),
    ) -> dict:
        return await tool_error_boundary(run_brand_get_image_list(resolve_api_key(api_key, headers), standard_id))
