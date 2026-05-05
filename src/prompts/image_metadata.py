"""Prompt helpers for AI-generated image manifest metadata."""

from pathlib import Path


def image_metadata_system_prompt() -> str:
    """Return the system guidance for image metadata generation."""
    return (
        "You generate factual metadata for brand-governance reference images. "
        "Use the supplied page context and the image itself. "
        "Do not invent governance rules, dimensions, or usage constraints that are not visually obvious or "
        "explicitly described in the provided context. "
        "Prefer concise, searchable titles, descriptions, section labels, and tags. "
        "If a field is unclear, return a cautious generic value rather than guessing."
    )


def image_metadata_user_prompt(
    *,
    standard_id: str,
    standard_title: str,
    filename: str,
    page_context: str,
) -> str:
    """Build the user prompt for one image metadata generation request."""
    return (
        f"Standard ID: {standard_id}\n"
        f"Standard title: {standard_title}\n"
        f"Image filename: {filename}\n\n"
        "Generate metadata for this brand reference image.\n"
        "Return a concise title, a factual description, the most relevant section name if you can infer one from "
        "the page context or image, a set of searchable tags, and a short usage label.\n"
        "Use the provided filename exactly.\n\n"
        "Page context:\n"
        f"{page_context}"
    )


def manifest_section_from_path(image_path: Path) -> str | None:
    """Infer a fallback section label from the parent path when no better cue is available."""
    parent = image_path.parent.name.strip()
    if parent and parent != "images":
        return parent.replace("-", " ").replace("_", " ").title()
    return None
