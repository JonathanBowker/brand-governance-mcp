"""Workflow orchestration for brand question answering."""

from fastmcp.server.context import Context

from src.models.key import ClientKey
from src.errors import NotFoundError
from src.policy.entitlements import has_format_access, require_collection_access
from src.prompts.answer import answer_limitations, answer_mode_settings
from src.resources.loader import load_json_document, load_markdown_excerpt
from src.schema.bgml_reference import applicability_terms, matching_applicability_terms
from src.templates.answers import render_answer_section, render_structured_candidate
from src.tools.common import best_matches, load_index, tokenize

MAX_EXCERPT_CHARS = 1200
MAX_STRUCTURED_ITEMS = 4


async def _report_progress(
    ctx: Context | None,
    progress: int,
    total: int = 100,
    message: str | None = None,
) -> None:
    """Report workflow progress when the current execution supports it."""
    if ctx is None:
        return
    await ctx.report_progress(progress, total, message)


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


def _structured_summary(sidecar: dict, question: str) -> tuple[str, list[str]]:
    """Build a concise structured answer summary from a standards JSON sidecar."""
    question_tokens = tokenize(question)
    sidecar_terms = applicability_terms(sidecar)
    matches = matching_applicability_terms(question_tokens, sidecar)

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
            rendered = render_structured_candidate(kind, item)
            if rendered:
                candidates.append((score, rendered))

    lines: list[str] = []
    if matches:
        lines.append("Matched applicability: " + ", ".join(matches[:6]))
    for _, rendered in sorted(candidates, key=lambda item: item[0], reverse=True)[:MAX_STRUCTURED_ITEMS]:
        if rendered not in lines:
            lines.append(rendered)

    return "\n".join(lines), matches


async def run_answer_workflow(
    client: ClientKey,
    question: str,
    *,
    mode: str = "detailed",
    include_sources: bool = True,
    ctx: Context | None = None,
) -> dict:
    """Run the brand question-answering workflow with optional task progress updates."""
    await _report_progress(ctx, 10, message="Loading brand index")
    mode_settings = answer_mode_settings(mode)
    index = await load_index(client)
    allowed_groups = set()
    for group in ["standards", *index.collections.keys()]:
        try:
            require_collection_access(client, group)
        except Exception:
            continue
        allowed_groups.add(group)

    await _report_progress(ctx, 35, message="Ranking relevant guidance")
    matches = best_matches(index, question, limit=3, groups=allowed_groups)
    if not matches:
        raise NotFoundError(
            "No relevant standard was found for this question in the BGML index.",
            details={"question": question},
        )

    used = []
    answer_parts = []
    total_matches = len(matches)
    for position, standard in enumerate(matches, start=1):
        sidecar = None
        structured_summary = ""
        matched_terms: list[str] = []
        source_file = standard.files.markdown
        source_type = "markdown"

        if (
            mode_settings["prefer_structured_guidance"]
            and (standard.group or "standards") == "standards"
            and has_format_access(client, "json")
        ):
            sidecar = await load_json_document(client.bucket_uri, standard.files.json_file)
            if sidecar:
                structured_summary, matched_terms = _structured_summary(sidecar, question)
                if structured_summary:
                    source_file = standard.files.json_file
                    source_type = "json"

        excerpt = ""
        if not structured_summary or mode == "strict":
            excerpt = await load_markdown_excerpt(
                client.bucket_uri,
                standard.files.markdown,
                max_chars=MAX_EXCERPT_CHARS,
            )
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
        answer_parts.append(
            render_answer_section(
                name=standard.name,
                description=standard.description,
                key_rules=standard.key_rules,
                structured_summary=structured_summary,
                excerpt=excerpt,
                is_concise=mode_settings["is_concise"],
                include_markdown_excerpt=mode_settings["include_markdown_excerpt"],
            )
        )
        progress = 35 + int((position / total_matches) * 55)
        await _report_progress(ctx, progress, message=f"Prepared answer context for {standard.name}")

    await _report_progress(ctx, 100, message="Answer ready")
    return {
        "ok": True,
        "clientId": client.client_id,
        "question": question,
        "mode": mode,
        "answer": "\n\n".join(answer_parts),
        "standardsUsed": used if include_sources else [],
        "limitations": answer_limitations(),
    }
