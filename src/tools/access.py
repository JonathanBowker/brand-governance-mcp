"""Access-state tool for reporting key entitlements and expiry details."""

from fastmcp import FastMCP
from fastmcp.dependencies import CurrentHeaders

from src.auth import resolve_api_key, validate_key
from src.errors import tool_error_boundary


async def run_brand_check_access(api_key: str) -> dict:
    """Return the validated client's current access tier and capability flags."""
    client = await validate_key(api_key)
    return {
        "ok": True,
        "clientId": client.client_id,
        "clientName": client.client_name,
        "tier": client.tier,
        "status": client.status,
        "expires": client.expires.isoformat(),
        "accessControl": client.access_control.model_dump(by_alias=True),
        "watermark": client.watermark,
        "assetsRedacted": client.assets_redacted,
    }


def register(mcp: FastMCP):
    """Register the access inspection tool with the FastMCP server."""
    @mcp.tool(
        name="brand_check_access",
        description="Show the client's current access tier, enabled capabilities, and expiry status for this brand.",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    )
    async def brand_check_access(api_key: str = "", headers: dict[str, str] = CurrentHeaders()) -> dict:
        return await tool_error_boundary(run_brand_check_access(resolve_api_key(api_key, headers)))
