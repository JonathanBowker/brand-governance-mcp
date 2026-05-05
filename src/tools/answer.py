"""Question-answering tool that blends BGML metadata with structured sidecars."""

import json

from fastmcp import FastMCP
from fastmcp.dependencies import CurrentHeaders

from src.auth import resolve_api_key, validate_key
from src.errors import NotFoundError, tool_error_boundary
from src.policy.entitlements import has_format_access, require_collection_access
from src.s3 import S3ObjectNotFound, get_object
from src.tools.common import best_matches, load_index, tokenize

MAX_EXCERPT_CHARS = 1200
MAX_STRUCTURED_ITEMS = 4


async def _markdown_excerpt(bucket_uri: str, path: str | None) -> str:
    """Load and lightly compress Markdown into a bounded excerpt for fallback answers."""
    if not path:
        return ""
    try:
        content = await get_object(bucket_uri, path)
    except S3ObjectNotFound:
        return ""
    cleaned = "\n".join(line.strip() for line in content.splitlines() if line.strip())
    return cleaned[:MAX_EXCERPT_CHARS]


async def _load_json_sidecar(bucket_uri: str, path: str | None) -> dict | None:
    """Load a JSON sidecar when present and return only dict payloads."""
    if not path:
        return None
    try:
        raw = await get_object(bucket_uri, path)
    except S3ObjectNotFound:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _applicability_terms(sidecar: dict) -> set[str]:
    """Collect applicability terms used to route and score standards answers."""
    applicability = sidecar.get("applicability") or {}
    terms: set[str] = set()
    for field in ("relationship_types", "use_cases", "scopes", "channels", "audiences", "exceptions"):
        for value in applicability.get(field, []) or []:
            if isinstance(value, str):
                terms.add(value)
    contexts = applicability.get("contexts") or {}
    if isinstance(contexts, dict):
        for values in contexts.values():
            for value in values or []:
                if isinstance(value, str):
                    terms.add(value)
    return terms


def _matching_terms(question_tokens: set[str], sidecar: dict) -> list[str]:
    """Return applicability terms whose tokens overlap the incoming question."""
    matches: list[str] = []
    for term in sorted(_applicability_terms(sidecar)):
        if tokenize(term) & question_tokens:
            matches.append(term)
    return matches


def _item_text(item: dict) -> str:
    """Flatten a structured rules or token item into searchable text."""
    parts: list[str] = []
    for key in ("name", "statement", "description", "token_group", "type", "source_section"):
        value = item.get(key)
        if isinstance(value, str):
            parts.append(value)
    for key in ("usage", "restrictions", "applies_to"):
        values = item.get(key)
        if isinstance(values, list):
            parts.extend(str(value) for value in values if isinstance(value, str))
    values = item.get("values")
    if isinstance(values, dict):
        for nested in values.values():
            if isinstance(nested, list):
                parts.extend(str(value) for value in nested if isinstance(value, (str, int, float)))
            elif isinstance(nested, (str, int, float)):
                parts.append(str(nested))
    return " ".join(parts)


def _score_item(item: dict, question_tokens: set[str], sidecar_terms: set[str]) -> int:
    """Score a structured item by text overlap plus applies-to alignment."""
    score = len(tokenize(_item_text(item)) & question_tokens)
    for applies_to in item.get("applies_to", []) or []:
        if not isinstance(applies_to, str):
            continue
        applies_tokens = tokenize(applies_to)
        overlap = applies_tokens & question_tokens
        if overlap:
            score += len(overlap) + 2
        if applies_to in sidecar_terms and overlap:
            score += 1
    return score


def _render_candidate(kind: str, item: dict) -> str:
    """Render a structured sidecar item into a short answer-ready line."""
    if kind == "rule":
        return f"Rule: {item.get('statement', '').strip()}"
    if kind == "restriction":
        return f"Restriction: {item.get('statement', '').strip()}"
    if kind == "token":
        name = item.get("name", "Unnamed token")
        usage = item.get("usage", []) or []
        summary = usage[0] if usage else item.get("type", "")
        return f"Token {name}: {summary}".strip()
    if kind == "example":
        return f"Example: {item.get('description', '').strip()}"
    return ""


def _structured_summary(sidecar: dict, question: str) -> tuple[str, list[str]]:
    """Build a concise structured answer summary from a standards JSON sidecar."""
    question_tokens = tokenize(question)
    sidecar_terms = _applicability_terms(sidecar)
    matches = _matching_terms(question_tokens, sidecar)

    candidates: list[tuple[int, str]] = []
    for kind, items_key in (
        ("rule", "rules"),
        ("restriction", "restrictions"),
        ("token", "tokens"),
        ("example", "examples"),
    ):
        for item in sidecar.get(items_key, []) or []:
            if not isinstance(item, dict):
                continue
            score = _score_item(item, question_tokens, sidecar_terms)
            if score <= 0:
                continue
            rendered = _render_candidate(kind, item)
            if rendered:
                candidates.append((score, rendered))

    lines: list[str] = []
    if matches:
        lines.append("Matched applicability: " + ", ".join(matches[:6]))
    for _, rendered in sorted(candidates, key=lambda item: item[0], reverse=True)[:MAX_STRUCTURED_ITEMS]:
        if rendered not in lines:
            lines.append(rendered)

    return "\n".join(lines), matches


async def run_brand_answer_question(
    api_key: str,
    question: str,
    mode: str = "detailed",
    include_sources: bool = True,
) -> dict:
    """Answer a question from index metadata, preferring standards JSON sidecars when available."""
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
        sidecar = None
        structured_summary = ""
        matched_terms: list[str] = []
        source_file = standard.files.markdown
        source_type = "markdown"

        if (standard.group or "standards") == "standards" and has_format_access(client, "json"):
            sidecar = await _load_json_sidecar(client.bucket_uri, standard.files.json_file)
            if sidecar:
                structured_summary, matched_terms = _structured_summary(sidecar, question)
                if structured_summary:
                    source_file = standard.files.json_file
                    source_type = "json"

        excerpt = ""
        if not structured_summary or mode == "strict":
            excerpt = await _markdown_excerpt(client.bucket_uri, standard.files.markdown)
            if not source_file:
                source_file = standard.files.markdown
                source_type = "markdown"

        related = standard.related
        if source_type == "json" and sidecar:
            related = (sidecar.get("bgml") or {}).get("related_standards") or standard.related

        used.append(
            {
                "standardId": standard.id,
                "group": standard.group,
                "name": standard.name,
                "sourceFile": source_file,
                "sourceType": source_type,
                "keyRules": standard.key_rules,
                "related": related,
                "matchedApplicability": matched_terms,
            }
        )
        if mode == "concise":
            answer_parts.append(f"{standard.name}: {standard.description}")
        else:
            rules = "; ".join(standard.key_rules[:6]) if standard.key_rules else "No indexed key rules."
            details = f" Structured guidance: {structured_summary}" if structured_summary else ""
            excerpt_text = f" Source excerpt: {excerpt}" if excerpt and mode != "strict" else ""
            answer_parts.append(f"{standard.name}: {standard.description} Key rules: {rules}.{details}{excerpt_text}")

    return {
        "ok": True,
        "clientId": client.client_id,
        "question": question,
        "mode": mode,
        "answer": "\n\n".join(answer_parts),
        "standardsUsed": used if include_sources else [],
        "limitations": [
            "Answers use BGML index metadata and prefer standards JSON sidecars when the key can access them.",
            "This is guidance, not full governed validation. YAML sidecars are required for Layer 2 validation.",
        ],
    }


def register(mcp: FastMCP):
    """Register the question-answering tool with the FastMCP server."""
    @mcp.tool(
        name="brand_answer_question",
        description="Answer a brand governance question using the client's approved brand guidance, indexed standards, and structured content.",
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
