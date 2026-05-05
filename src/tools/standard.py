"""Standard retrieval tool with format resolution and JSON-sidecar preference."""

from fastmcp import FastMCP
from fastmcp.dependencies import CurrentHeaders

from src.auth import resolve_api_key, validate_key
from src.errors import NotFoundError, tool_error_boundary
from src.policy.entitlements import has_format_access, require_collection_access, require_format
from src.s3 import S3ObjectNotFound, get_object
from src.tools.common import find_entry, find_standard, load_index


def _resolve_standard_format(standard, client, requested_format: str) -> tuple[str, str | None]:
    """Resolve the concrete file format and path for a standard request.

    `auto` prefers the JSON sidecar for standards when the client has Layer 3
    access and a JSON file is indexed. Otherwise it falls back to Markdown.
    """
    if requested_format == "auto":
        if (standard.group or "standards") == "standards" and standard.files.json_file and has_format_access(client, "json"):
            return "json", standard.files.json_file
        return "markdown", standard.files.markdown

    if requested_format == "markdown":
        return "markdown", standard.files.markdown
    if requested_format == "yaml":
        return "yaml", standard.files.yaml
    if requested_format == "json":
        return "json", standard.files.json_file
    raise ValueError("Invalid format. Must be one of: auto, markdown, yaml, json")


async def run_brand_get_standard(api_key: str, standard_id: str, format: str = "auto") -> dict:
    """Fetch a standard in the requested format, with `auto` preferring JSON sidecars."""
    client = await validate_key(api_key)
    index = await load_index(client)
    try:
        standard = find_standard(index, standard_id)
    except NotFoundError:
        standard = find_entry(index, standard_id)
    require_collection_access(client, standard.group)
    if format != "auto":
        require_format(client, format)

    resolved_format, path = _resolve_standard_format(standard, client, format)

    if not path:
        raise NotFoundError(
            f"No {resolved_format} file is listed for standard '{standard_id}'.",
            details={"standardId": standard_id, "format": resolved_format, "requestedFormat": format},
        )

    try:
        content = await get_object(client.bucket_uri, path)
    except S3ObjectNotFound as exc:
        raise NotFoundError(
            f"The {resolved_format} file for standard '{standard_id}' was not found in storage.",
            details={"standardId": standard_id, "format": resolved_format, "requestedFormat": format, "path": path},
        ) from exc

    return {
        "ok": True,
        "clientId": client.client_id,
        "standardId": standard.id,
        "name": standard.name,
        "format": resolved_format,
        "requestedFormat": format,
        "path": path,
        "keyRules": standard.key_rules,
        "related": standard.related,
        "content": content,
    }


def register(mcp: FastMCP):
    """Register the standard retrieval tool with the FastMCP server."""
    @mcp.tool(
        name="brand_get_standard",
        description="Get a specific brand standard by ID, returning the most structured version available and Markdown when fuller context is needed.",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    )
    async def brand_get_standard(
        standard_id: str,
        format: str = "auto",
        api_key: str = "",
        headers: dict[str, str] = CurrentHeaders(),
    ) -> dict:
        return await tool_error_boundary(
            run_brand_get_standard(resolve_api_key(api_key, headers), standard_id, format)
        )
