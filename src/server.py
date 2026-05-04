import logging

from fastmcp import FastMCP

from src.config import settings
from src.tools import TOOL_MODULES

logger = logging.getLogger(__name__)


def create_mcp() -> FastMCP:
    mcp = FastMCP(name="Advanced Analytica Brand Governance")

    for module in TOOL_MODULES:
        module.register(mcp)

    @mcp.tool(
        name="health",
        description="Health check for the Brand Governance MCP Server.",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    )
    async def health() -> dict:
        return {"ok": True, "service": "brand-governance-mcp", "version": "1.0.0"}

    return mcp


mcp = create_mcp()


def main() -> None:
    logger.info("Starting Brand Governance MCP Server on %s:%s", settings.mcp_host, settings.mcp_port)
    try:
        mcp.run(
            transport=settings.mcp_transport,
            host=settings.mcp_host,
            port=settings.mcp_port,
            path=settings.mcp_path,
        )
    except TypeError:
        # Some FastMCP versions use stdio by default or expose different HTTP kwargs.
        # Keep a fallback so local development can still start.
        logger.warning("FastMCP run signature did not accept configured HTTP kwargs; falling back to mcp.run().")
        mcp.run()


if __name__ == "__main__":
    main()
