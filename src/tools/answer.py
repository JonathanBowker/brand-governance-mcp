from fastmcp import FastMCP
from fastmcp.dependencies import CurrentHeaders

from src.auth import resolve_api_key, validate_key
from src.errors import NotFoundError, tool_error_boundary
from src.policy.entitlements import require_collection_access
from src.s3 import S3ObjectNotFound, get_object
from src.tools.common import best_matches, load_index

MAX_EXCERPT_CHARS = 1200


async def _markdown_excerpt(bucket_uri: str, path: str | None) -> str:
    if not path:
        return ""
    try:
        content = await get_object(bucket_uri, path)
    except S3ObjectNotFound:
        return ""
    cleaned = "\n".join(line.strip() for line in content.splitlines() if line.strip())
    return cleaned[:MAX_EXCERPT_CHARS]


async def run_brand_answer_question(
    api_key: str,
    question: str,
    mode: str = "detailed",
    include_sources: bool = True,
) -> dict:
    client = await validate_key(api_key)
    index = await load_index(client)
    allowed_groups = set()
    for group in ["standards", *index.collections.keys()]:
        try:
            require_collection_access(client, group)
        except Exception:
            continue
        allowed_groups.add(group)

    matches = best_matches(index, question, limit=3, groups=allowed_groups)
    if not matches:
        raise NotFoundError(
            "No relevant standard was found for this question in the BGML index.",
            details={"question": question},
        )

    used = []
    answer_parts = []
    for standard in matches:
        excerpt = await _markdown_excerpt(client.bucket_uri, standard.files.markdown)
        used.append(
            {
                "standardId": standard.id,
                "group": standard.group,
                "name": standard.name,
                "sourceFile": standard.files.markdown,
                "keyRules": standard.key_rules,
                "related": standard.related,
            }
        )
        if mode == "concise":
            answer_parts.append(f"{standard.name}: {standard.description}")
        else:
            rules = "; ".join(standard.key_rules[:6]) if standard.key_rules else "No indexed key rules."
            excerpt_text = f" Source excerpt: {excerpt}" if excerpt and mode != "strict" else ""
            answer_parts.append(f"{standard.name}: {standard.description} Key rules: {rules}.{excerpt_text}")

    return {
        "ok": True,
        "clientId": client.client_id,
        "question": question,
        "mode": mode,
        "answer": "\n\n".join(answer_parts),
        "standardsUsed": used if include_sources else [],
        "limitations": [
            "Layer 1 answers use BGML metadata and Markdown narrative only.",
            "This is guidance, not full governed validation. YAML sidecars are required for Layer 2 validation.",
        ],
    }


def register(mcp: FastMCP):
    @mcp.tool(
        name="brand_answer_question",
        description="Answer a brand question from BGML metadata and Markdown source content.",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    )
    async def brand_answer_question(
        question: str,
        mode: str = "detailed",
        include_sources: bool = True,
        api_key: str = "",
        headers: dict[str, str] = CurrentHeaders(),
    ) -> dict:
        return await tool_error_boundary(
            run_brand_answer_question(resolve_api_key(api_key, headers), question, mode, include_sources)
        )
