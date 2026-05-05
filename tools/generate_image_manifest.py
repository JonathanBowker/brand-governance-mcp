#!/usr/bin/env python
"""Generate or enrich image manifest metadata for a brand standard folder."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import re
from pathlib import Path
from urllib import error, request

from src.config import settings
from src.models.assets import ImageAssetMetadata, ImageManifest
from src.prompts.image_metadata import (
    image_metadata_system_prompt,
    image_metadata_user_prompt,
    manifest_section_from_path,
)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
OPENAI_VISION_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MAX_PAGE_CONTEXT_CHARS = 6000


def slug_to_title(value: str) -> str:
    """Convert a slug-like value into a compact human-readable title."""
    return re.sub(r"\s+", " ", value.replace("-", " ").replace("_", " ")).strip().title()


def infer_standard_context(standard_dir: Path) -> tuple[str, str, str]:
    """Return standard id, title, and page context from a standard content folder."""
    standard_id = "/".join(standard_dir.parts[-2:])
    title = slug_to_title(standard_dir.name)
    page_json = standard_dir / "page.json"
    if page_json.exists():
        try:
            data = json.loads(page_json.read_text(encoding="utf-8"))
            standard = data.get("standard")
            if isinstance(standard, dict):
                standard_id = str(standard.get("id") or standard_id)
                title = str(standard.get("title") or title)
            markdown = data.get("markdown")
            if isinstance(markdown, dict):
                summary = markdown.get("summary")
                if isinstance(summary, str) and summary.strip():
                    return standard_id, title, summary.strip()[:MAX_PAGE_CONTEXT_CHARS]
            serialized = json.dumps(data, indent=2)
            return standard_id, title, serialized[:MAX_PAGE_CONTEXT_CHARS]
        except (OSError, json.JSONDecodeError):
            pass

    page_md = standard_dir / "page.md"
    if page_md.exists():
        context = page_md.read_text(encoding="utf-8")[:MAX_PAGE_CONTEXT_CHARS]
        return standard_id, title, context
    return standard_id, title, ""


def image_paths(images_dir: Path) -> list[Path]:
    """Return supported image files from an images folder in stable order."""
    return sorted(path for path in images_dir.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS)


def infer_tags(standard_slug: str, filename: str) -> list[str]:
    """Build a conservative fallback tag set from the standard slug and filename."""
    tags = {standard_slug}
    stem = Path(filename).stem.lower()
    tokens = re.findall(r"[a-z0-9]+", stem.replace("×", "x"))
    for token in tokens:
        if len(token) >= 3:
            tags.add(token)
    return sorted(tags)


def heuristic_asset_metadata(image_path: Path, standard_slug: str, standard_title: str) -> ImageAssetMetadata:
    """Create a safe starter metadata record without model assistance."""
    filename = image_path.name
    title = slug_to_title(Path(filename).stem)
    if title.lower() == Path(filename).stem.lower():
        title = f"{standard_title} reference"
    return ImageAssetMetadata(
        filename=filename,
        title=title,
        description=f"Reference image from the {standard_title} standard.",
        section=manifest_section_from_path(image_path),
        usage="reference",
        tags=infer_tags(standard_slug, filename),
    )


def encode_image_data_url(image_path: Path) -> str:
    """Encode a local image file as a data URL for OpenAI vision input."""
    content_type = mimetypes.guess_type(str(image_path))[0] or "application/octet-stream"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


def supports_openai_vision(image_path: Path) -> bool:
    """Return whether the image file type is supported for OpenAI vision input."""
    return image_path.suffix.lower() in OPENAI_VISION_EXTENSIONS


def parse_response_text(payload: dict) -> str:
    """Extract plain text output from an OpenAI Responses API payload."""
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    for item in payload.get("output", []) or []:
        for content in item.get("content", []) or []:
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return text
    raise ValueError("OpenAI response did not contain text output.")


def generate_ai_asset_metadata(
    image_path: Path,
    *,
    standard_id: str,
    standard_title: str,
    page_context: str,
    model: str,
) -> ImageAssetMetadata:
    """Generate image metadata using OpenAI Responses with structured JSON output."""
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY or AA_OPENAI_API_KEY is required for AI image manifest generation.")
    if not supports_openai_vision(image_path):
        raise RuntimeError(
            f"OpenAI vision does not support '{image_path.suffix}' inputs for {image_path.name}. "
            "Use --heuristic-only or keep this asset on heuristic metadata."
        )

    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "filename": {"type": "string"},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "section": {"type": ["string", "null"]},
            "tags": {"type": "array", "items": {"type": "string"}},
            "usage": {"type": "string"},
        },
        "required": ["filename", "title", "description", "section", "tags", "usage"],
    }
    body = {
        "model": model,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": image_metadata_system_prompt()}]},
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": image_metadata_user_prompt(
                            standard_id=standard_id,
                            standard_title=standard_title,
                            filename=image_path.name,
                            page_context=page_context,
                        ),
                    },
                    {
                        "type": "input_image",
                        "image_url": encode_image_data_url(image_path),
                        "detail": "high",
                    },
                ],
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "image_manifest_asset",
                "schema": schema,
                "strict": True,
            }
        },
    }
    req = request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI request failed: {exc.code} {details}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"OpenAI request failed: {exc.reason}") from exc

    asset = json.loads(parse_response_text(payload))
    asset["filename"] = image_path.name
    if asset.get("section") is None:
        asset["section"] = manifest_section_from_path(image_path)
    return ImageAssetMetadata.model_validate(asset)


def load_existing_assets(manifest_path: Path) -> dict[str, ImageAssetMetadata]:
    """Load an existing manifest into a filename-keyed lookup."""
    if not manifest_path.exists():
        return {}
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = ImageManifest.model_validate(data)
    return {asset.filename: asset for asset in manifest.assets}


def merged_asset_metadata(
    generated: ImageAssetMetadata,
    existing: ImageAssetMetadata | None,
    *,
    overwrite_existing: bool,
) -> ImageAssetMetadata:
    """Merge generated asset metadata with an existing manifest entry."""
    if existing is None:
        return generated
    if overwrite_existing:
        base = existing.model_dump(by_alias=True)
        base.update({key: value for key, value in generated.model_dump(by_alias=True).items() if value not in (None, "", [])})
        return ImageAssetMetadata.model_validate(base)

    base = generated.model_dump(by_alias=True)
    for key, value in existing.model_dump(by_alias=True).items():
        if value not in (None, "", [], {}):
            base[key] = value
    return ImageAssetMetadata.model_validate(base)


def main() -> None:
    """Generate or enrich a manifest.json file for one standard images folder."""
    parser = argparse.ArgumentParser(description="Generate image manifest metadata for a brand standard folder.")
    parser.add_argument("--standard-dir", required=True, help="Path to a standard folder containing page.md/page.json and images/")
    parser.add_argument("--output", help="Optional output path. Defaults to <standard-dir>/images/manifest.json")
    parser.add_argument("--model", default=settings.openai_model)
    parser.add_argument("--heuristic-only", action="store_true")
    parser.add_argument("--overwrite-existing", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    standard_dir = Path(args.standard_dir).resolve()
    images_dir = standard_dir / "images"
    if not images_dir.exists():
        raise SystemExit(f"Images directory not found: {images_dir}")

    standard_id, standard_title, page_context = infer_standard_context(standard_dir)
    standard_slug = standard_dir.name
    manifest_path = Path(args.output).resolve() if args.output else images_dir / "manifest.json"
    existing_assets = load_existing_assets(manifest_path)

    assets: list[ImageAssetMetadata] = []
    for image_path in image_paths(images_dir)[: args.limit]:
        generated = heuristic_asset_metadata(image_path, standard_slug, standard_title)
        if not args.heuristic_only and supports_openai_vision(image_path):
            generated = generate_ai_asset_metadata(
                image_path,
                standard_id=standard_id,
                standard_title=standard_title,
                page_context=page_context,
                model=args.model,
            )
        assets.append(
            merged_asset_metadata(
                generated,
                existing_assets.get(image_path.name),
                overwrite_existing=args.overwrite_existing,
            )
        )

    manifest = ImageManifest(standard_id=standard_id, assets=assets)
    manifest_path.write_text(json.dumps(manifest.model_dump(by_alias=True), indent=2), encoding="utf-8")
    print(f"Wrote manifest with {len(assets)} assets to {manifest_path}")
    print(f"wrote {manifest_path}")
    print(f"assets: {len(assets)}")
    print(f"mode: {'heuristic' if args.heuristic_only else 'openai'}")


if __name__ == "__main__":
    main()
