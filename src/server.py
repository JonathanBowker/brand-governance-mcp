import logging
import mimetypes

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.config import settings
from src.s3 import S3ObjectNotFound, get_object_bytes
from src.tools import TOOL_MODULES
from src.utils.asset_urls import asset_route_path, resolve_asset_path_token, resolve_asset_token, verify_asset_signature

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

    @mcp.custom_route(asset_route_path(), methods=["GET"], include_in_schema=False)
    async def asset_proxy(request: Request) -> Response:
        asset = request.query_params.get("asset", "")
        sig = request.query_params.get("sig", "")

        if asset:
            resolved = resolve_asset_token(asset, sig)
            if not resolved:
                return JSONResponse({"ok": False, "error": "Invalid or expired asset signature."}, status_code=403)
            bucket_uri, path, _expires = resolved
        else:
            bucket_uri = request.query_params.get("bucket", "")
            path = request.query_params.get("path", "")
            expires = request.query_params.get("expires", "")

            if not bucket_uri or not path or not expires or not sig:
                return JSONResponse({"ok": False, "error": "Missing asset parameters."}, status_code=400)

            if not verify_asset_signature(bucket_uri, path, expires, sig):
                return JSONResponse({"ok": False, "error": "Invalid or expired asset signature."}, status_code=403)

        try:
            body, content_type = await get_object_bytes(bucket_uri, path)
        except S3ObjectNotFound:
            return JSONResponse({"ok": False, "error": "Asset not found."}, status_code=404)

        media_type = content_type or mimetypes.guess_type(path)[0] or "application/octet-stream"
        return Response(body, media_type=media_type)

    @mcp.custom_route(f"{asset_route_path()}/{{token}}/{{filename:path}}", methods=["GET"], include_in_schema=False)
    async def asset_path_proxy(request: Request) -> Response:
        token = request.path_params.get("token", "")
        resolved = resolve_asset_path_token(token)
        if not resolved:
            return JSONResponse({"ok": False, "error": "Invalid or expired asset signature."}, status_code=403)
        bucket_uri, path, _expires = resolved

        try:
            body, content_type = await get_object_bytes(bucket_uri, path)
        except S3ObjectNotFound:
            return JSONResponse({"ok": False, "error": "Asset not found."}, status_code=404)

        media_type = content_type or mimetypes.guess_type(path)[0] or "application/octet-stream"
        return Response(body, media_type=media_type)

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
