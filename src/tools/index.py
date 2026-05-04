from fastmcp import FastMCP
from fastmcp.dependencies import CurrentHeaders

from src.auth import resolve_api_key, validate_key
from src.errors import tool_error_boundary
from src.policy.entitlements import require_standards
from src.tools.common import load_index


async def run_brand_get_index(api_key: str) -> dict:
    client = await validate_key(api_key)
    require_standards(client)
    index = await load_index(client)
    return {
        "ok": True,
        "clientId": client.client_id,
        "brand": index.meta.get("brand"),
        "index": index.model_dump(by_alias=True),
    }


def register(mcp: FastMCP):
    @mcp.tool(
        name="brand_get_index",
        description="Return the full BGML index for the client's brand.",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    )
    async def brand_get_index(api_key: str = "", headers: dict[str, str] = CurrentHeaders()) -> dict:
        return await tool_error_boundary(run_brand_get_index(resolve_api_key(api_key, headers)))
