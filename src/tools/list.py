"""Standards listing tool for the Brand Governance MCP server."""

from fastmcp import FastMCP
from fastmcp.dependencies import CurrentHeaders

from src.auth import resolve_api_key, validate_key
from src.errors import tool_error_boundary
from src.policy.entitlements import require_standards
from src.tools.common import load_index, summarise_standard


async def run_brand_list_standards(api_key: str, category: str = "all") -> dict:
    """List standards visible to the client, optionally filtered by category."""
    client = await validate_key(api_key)
    require_standards(client)
    index = await load_index(client)
    standards = index.standards
    if category != "all":
        standards = [s for s in standards if s.category == category]
    return {
        "ok": True,
        "clientId": client.client_id,
        "category": category,
        "count": len(standards),
        "standards": [summarise_standard(s) for s in standards],
    }


def register(mcp: FastMCP):
    """Register the standards listing tool with the FastMCP server."""
    @mcp.tool(
        name="brand_list_standards",
        description="List available brand standards with their names, summaries, categories, and tags.",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    )
    async def brand_list_standards(
        api_key: str = "",
        category: str = "all",
        headers: dict[str, str] = CurrentHeaders(),
    ) -> dict:
        return await tool_error_boundary(run_brand_list_standards(resolve_api_key(api_key, headers), category))
