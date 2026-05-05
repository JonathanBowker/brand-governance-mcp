"""Formatting helpers for brand question-answer responses."""


def render_structured_candidate(kind: str, item: dict) -> str:
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


def render_answer_section(
    *,
    name: str,
    description: str,
    key_rules: list[str],
    structured_summary: str,
    excerpt: str,
    is_concise: bool,
    include_markdown_excerpt: bool,
) -> str:
    """Render one matched entry into the final answer text block."""
    if is_concise:
        return f"{name}: {description}"

    rules = "; ".join(key_rules[:6]) if key_rules else "No indexed key rules."
    details = f" Structured guidance: {structured_summary}" if structured_summary else ""
    excerpt_text = f" Source excerpt: {excerpt}" if excerpt and include_markdown_excerpt else ""
    return f"{name}: {description} Key rules: {rules}.{details}{excerpt_text}"

