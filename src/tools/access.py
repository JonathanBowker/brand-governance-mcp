from fastmcp import FastMCP
from fastmcp.dependencies import CurrentHeaders

from src.auth import resolve_api_key, validate_key
from src.errors import tool_error_boundary


async def run_brand_check_access(api_key: str) -> dict:
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
    @mcp.tool(
        name="brand_check_access",
        description="Return current access control state for the client's key.",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    )
    async def brand_check_access(api_key: str = "", headers: dict[str, str] = CurrentHeaders()) -> dict:
        return await tool_error_boundary(run_brand_check_access(resolve_api_key(api_key, headers)))
