"""Question-answering tool that blends BGML metadata with structured sidecars."""

from fastmcp import FastMCP
from fastmcp.dependencies import CurrentHeaders
from fastmcp.server.context import Context

from src.auth import resolve_api_key, validate_key
from src.errors import tool_error_boundary
from src.workflows.answer import run_answer_workflow
from src.workflows.tasking import optional_task_config


async def run_brand_answer_question(
    api_key: str,
    question: str,
    mode: str = "detailed",
    include_sources: bool = True,
    ctx: Context | None = None,
) -> dict:
    """Answer a question from index metadata, preferring standards JSON sidecars when available."""
    client = await validate_key(api_key)
    return await run_answer_workflow(client, question, mode=mode, include_sources=include_sources, ctx=ctx)


def register(mcp: FastMCP):
    """Register the question-answering tool with the FastMCP server."""
    @mcp.tool(
        name="brand_answer_question",
        description="Answer a brand governance question using the client's approved brand guidance, indexed standards, and structured content.",
        task=optional_task_config(),
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    )
    async def brand_answer_question(
        question: str,
        mode: str = "detailed",
        include_sources: bool = True,
        api_key: str = "",
        headers: dict[str, str] = CurrentHeaders(),
        ctx: Context | None = None,
    ) -> dict:
        return await tool_error_boundary(
            run_brand_answer_question(resolve_api_key(api_key, headers), question, mode, include_sources, ctx)
        )
