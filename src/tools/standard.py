from fastmcp import FastMCP
from fastmcp.dependencies import CurrentHeaders

from src.auth import resolve_api_key, validate_key
from src.errors import NotFoundError, tool_error_boundary
from src.policy.entitlements import require_collection_access, require_format
from src.s3 import S3ObjectNotFound, get_object
from src.tools.common import find_entry, find_standard, load_index


async def run_brand_get_standard(api_key: str, standard_id: str, format: str = "markdown") -> dict:
    client = await validate_key(api_key)
    require_format(client, format)
    index = await load_index(client)
    try:
        standard = find_standard(index, standard_id)
    except NotFoundError:
        standard = find_entry(index, standard_id)
    require_collection_access(client, standard.group)

    if format == "markdown":
        path = standard.files.markdown
    elif format == "yaml":
        path = standard.files.yaml
    elif format == "json":
        path = standard.files.json_file
    else:
        raise ValueError("Invalid format. Must be one of: markdown, yaml, json")

    if not path:
        raise NotFoundError(
            f"No {format} file is listed for standard '{standard_id}'.",
            details={"standardId": standard_id, "format": format},
        )

    try:
        content = await get_object(client.bucket_uri, path)
    except S3ObjectNotFound as exc:
        raise NotFoundError(
            f"The {format} file for standard '{standard_id}' was not found in storage.",
            details={"standardId": standard_id, "format": format, "path": path},
        ) from exc

    return {
        "ok": True,
        "clientId": client.client_id,
        "standardId": standard.id,
        "name": standard.name,
        "format": format,
        "path": path,
        "keyRules": standard.key_rules,
        "related": standard.related,
        "content": content,
    }


def register(mcp: FastMCP):
    @mcp.tool(
        name="brand_get_standard",
        description="Fetch a specific brand standard by ID. Returns content, key rules and metadata.",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    )
    async def brand_get_standard(
        standard_id: str,
        format: str = "markdown",
        api_key: str = "",
        headers: dict[str, str] = CurrentHeaders(),
    ) -> dict:
        return await tool_error_boundary(
            run_brand_get_standard(resolve_api_key(api_key, headers), standard_id, format)
        )
