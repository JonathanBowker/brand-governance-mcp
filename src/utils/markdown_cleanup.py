import re


SHARED_HEADER_TITLE = "## Welcome to the Brand Site for advanced users"
SHARED_HEADER_MARKER = "READ AND AGREE BEFORE YOU ENTER THE SITE"


def strip_shared_header_block(markdown: str) -> tuple[str, bool]:
    text = markdown.lstrip("\ufeff")
    if SHARED_HEADER_TITLE not in text or SHARED_HEADER_MARKER not in text:
        return markdown, False

    start_idx = text.find(SHARED_HEADER_TITLE)
    if start_idx == -1:
        return markdown, False

    heading_match = re.search(r"(?m)^#(?!#)\s+.+$", text)
    if not heading_match:
        return markdown, False

    cleaned = text[heading_match.start() :].lstrip()
    return cleaned, cleaned != markdown
