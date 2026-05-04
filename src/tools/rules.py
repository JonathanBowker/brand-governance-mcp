from fastmcp import FastMCP

from src.auth import validate_key
from src.errors import tool_error_boundary
from src.policy.entitlements import require_collection_access
from src.tools.common import find_entry, load_index


async def run_brand_get_rules(api_key: str, standard_id: str) -> dict:
    client = await validate_key(api_key)
    index = await load_index(client)
    standard = find_entry(index, standard_id)
    require_collection_access(client, standard.group)
    return {
        "ok": True,
        "clientId": client.client_id,
        "standardId": standard.id,
        "group": standard.group,
        "name": standard.name,
        "keyRules": standard.key_rules,
        "related": standard.related,
    }


def register(mcp: FastMCP):
    @mcp.tool(
        name="brand_get_rules",
        description="Return indexed key rules for a brand standard.",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    )
    async def brand_get_rules(standard_id: str, api_key: str = "") -> dict:
        return await tool_error_boundary(run_brand_get_rules(api_key, standard_id))
