"""Collection-aware content listing and retrieval tools."""

from fastmcp import FastMCP
from fastmcp.dependencies import CurrentHeaders

from src.auth import resolve_api_key, validate_key
from src.errors import NotFoundError, tool_error_boundary
from src.policy.entitlements import require_collection_access, require_format
from src.s3 import S3ObjectNotFound, get_object
from src.tools.common import find_entry, load_index, summarise_entry


async def run_brand_list_content(api_key: str, group: str = "all", category: str = "all") -> dict:
    """List accessible indexed content across one or more BGML collection groups."""
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
    """Fetch one indexed content entry in the explicitly requested storage format."""
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
    """Register collection listing and retrieval tools with the FastMCP server."""
    @mcp.tool(
        name="brand_list_content",
        description="List available brand guidance and resources across standards, toolkits, asset libraries, digital guidance, and other accessible collections.",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    )
    async def brand_list_content(
        api_key: str = "",
        group: str = "all",
        category: str = "all",
        headers: dict[str, str] = CurrentHeaders(),
    ) -> dict:
        return await tool_error_boundary(run_brand_list_content(resolve_api_key(api_key, headers), group, category))

    @mcp.tool(
        name="brand_get_content",
        description="Get a specific brand guidance item or resource by ID from any accessible collection.",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    )
    async def brand_get_content(
        content_id: str,
        format: str = "markdown",
        api_key: str = "",
        headers: dict[str, str] = CurrentHeaders(),
    ) -> dict:
        return await tool_error_boundary(run_brand_get_content(resolve_api_key(api_key, headers), content_id, format))
