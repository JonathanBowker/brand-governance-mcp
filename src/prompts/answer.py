"""Prompt-oriented settings for the brand question-answering tool."""


def answer_mode_settings(mode: str) -> dict[str, bool]:
    """Return mode-specific flags that control how answers are assembled."""
    return {
        "is_concise": mode == "concise",
        "include_markdown_excerpt": mode != "strict",
        "prefer_structured_guidance": True,
    }


def answer_limitations() -> list[str]:
    """Return the standard limitations included with brand answer responses."""
    return [
        "Answers use BGML index metadata and prefer standards JSON sidecars when the key can access them.",
        "This is guidance, not full governed validation. YAML sidecars are required for Layer 2 validation.",
    ]

