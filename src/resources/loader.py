"""Helpers for loading runtime content such as Markdown and JSON sidecars."""

import json

from src.s3 import S3ObjectNotFound, get_object


async def load_markdown_excerpt(bucket_uri: str, path: str | None, *, max_chars: int = 1200) -> str:
    """Load and lightly compress Markdown into a bounded excerpt."""
    if not path:
        return ""
    try:
        content = await get_object(bucket_uri, path)
    except S3ObjectNotFound:
        return ""
    cleaned = "\n".join(line.strip() for line in content.splitlines() if line.strip())
    return cleaned[:max_chars]


async def load_json_document(bucket_uri: str, path: str | None) -> dict | None:
    """Load a JSON document when present and return only dict payloads."""
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

