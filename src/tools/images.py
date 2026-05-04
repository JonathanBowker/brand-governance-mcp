import json
from pathlib import PurePosixPath

from fastmcp import FastMCP
from fastmcp.dependencies import CurrentHeaders

from src.auth import resolve_api_key, validate_key
from src.config import settings
from src.errors import NotFoundError, tool_error_boundary
from src.policy.entitlements import require_collection_access
from src.s3 import S3ObjectNotFound, get_object, get_presigned_url, list_objects, object_exists
from src.tools.common import find_entry, load_index

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


async def _load_manifest(bucket_uri: str, images_path: str) -> list[dict]:
    manifest_key = f"{images_path.rstrip('/')}/manifest.json"
    if not await object_exists(bucket_uri, manifest_key):
        return []
    try:
        raw = await get_object(bucket_uri, manifest_key)
        data = json.loads(raw)
        return data if isinstance(data, list) else data.get("images", [])
    except (json.JSONDecodeError, S3ObjectNotFound):
        return []


async def run_brand_get_image_list(api_key: str, standard_id: str) -> dict:
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
    manifest_by_name = {item.get("filename"): item for item in manifest if item.get("filename")}

    images = []
    for key in keys:
        name = PurePosixPath(key).name
        if name == "manifest.json":
            continue
        if PurePosixPath(name).suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        item = manifest_by_name.get(name, {})
        images.append(
            {
                "filename": name,
                "description": item.get("description", ""),
                "usage": item.get("usage", "reference"),
                "path": key,
                "watermark": client.watermark,
                "presignedUrl": await get_presigned_url(client.bucket_uri, key, settings.presign_expiry),
                "expiresInSeconds": settings.presign_expiry,
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
    @mcp.tool(
        name="brand_get_image_list",
        description="Return available images for a standard as short-lived presigned URLs.",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    )
    async def brand_get_image_list(
        standard_id: str,
        api_key: str = "",
        headers: dict[str, str] = CurrentHeaders(),
    ) -> dict:
        return await tool_error_boundary(run_brand_get_image_list(resolve_api_key(api_key, headers), standard_id))
