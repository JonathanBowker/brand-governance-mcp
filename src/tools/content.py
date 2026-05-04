from fastmcp import FastMCP

from src.auth import validate_key
from src.errors import NotFoundError, tool_error_boundary
from src.policy.entitlements import require_collection_access, require_format
from src.s3 import S3ObjectNotFound, get_object
from src.tools.common import find_entry, load_index, summarise_entry


async def run_brand_list_content(api_key: str, group: str = "all", category: str = "all") -> dict:
    client = await validate_key(api_key)
    index = await load_index(client)

    if group == "all":
        allowed_groups = []
        for collection_group in sorted(index.collections):
            try:
                require_collection_access(client, collection_group)
            except Exception:
                continue
            allowed_groups.append(collection_group)
        content = []
        for collection_group in allowed_groups:
            entries = index.collections.get(collection_group, [])
            if category != "all":
                entries = [entry for entry in entries if entry.category == category]
            content.extend(entries)
    else:
        require_collection_access(client, group)
        content = index.collections.get(group, [])
        if group == "standards" and not content:
            content = index.standards
        if category != "all":
            content = [entry for entry in content if entry.category == category]

    return {
        "ok": True,
        "clientId": client.client_id,
        "group": group,
        "category": category,
        "count": len(content),
        "content": [summarise_entry(entry) for entry in content],
    }


async def run_brand_get_content(api_key: str, content_id: str, format: str = "markdown") -> dict:
    client = await validate_key(api_key)
    require_format(client, format)
    index = await load_index(client)
    entry = find_entry(index, content_id)
    require_collection_access(client, entry.group)

    if format == "markdown":
        path = entry.files.markdown
    elif format == "yaml":
        path = entry.files.yaml
    elif format == "json":
        path = entry.files.json_file
    else:
        raise ValueError("Invalid format. Must be one of: markdown, yaml, json")

    if not path:
        raise NotFoundError(
            f"No {format} file is listed for content '{content_id}'.",
            details={"contentId": content_id, "format": format},
        )

    try:
        content = await get_object(client.bucket_uri, path)
    except S3ObjectNotFound as exc:
        raise NotFoundError(
            f"The {format} file for content '{content_id}' was not found in storage.",
            details={"contentId": content_id, "format": format, "path": path},
        ) from exc

    return {
        "ok": True,
        "clientId": client.client_id,
        "contentId": entry.id,
        "group": entry.group,
        "name": entry.name,
        "format": format,
        "path": path,
        "keyRules": entry.key_rules,
        "related": entry.related,
        "content": content,
    }


def register(mcp: FastMCP):
    @mcp.tool(
        name="brand_list_content",
        description="List available indexed brand content across standards, toolkits, asset-library, digital, and other collections.",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    )
    async def brand_list_content(api_key: str = "", group: str = "all", category: str = "all") -> dict:
        return await tool_error_boundary(run_brand_list_content(api_key, group, category))

    @mcp.tool(
        name="brand_get_content",
        description="Fetch indexed brand content by ID from any available collection.",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    )
    async def brand_get_content(content_id: str, format: str = "markdown", api_key: str = "") -> dict:
        return await tool_error_boundary(run_brand_get_content(api_key, content_id, format))
