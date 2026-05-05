#!/usr/bin/env python
"""Rebuild and upload a BGML index from Spaces or a local source-of-truth tree."""

import argparse
import json
import mimetypes
from collections import defaultdict
from pathlib import Path, PurePosixPath

import boto3
from botocore.config import Config

from src.config import settings

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


def slug_to_title(slug: str) -> str:
    """Convert a slug-like folder name into a human-readable title."""
    return slug.replace("_q_", " ").replace("-", " ").replace("_", " ").title()


def build_client():
    """Create the S3-compatible client used to read and write Spaces content."""
    endpoint_url = settings.s3_endpoint
    if endpoint_url and "digitaloceanspaces.com" in endpoint_url and endpoint_url.count("/") >= 2:
        endpoint_url = f"https://{settings.s3_region}.digitaloceanspaces.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4"),
    )


def list_keys(client, bucket: str, prefix: str) -> list[str]:
    """List all object keys under a prefix in the target bucket."""
    keys: list[str] = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for item in page.get("Contents", []):
            keys.append(item["Key"])
    return keys


def read_json(client, bucket: str, key: str) -> dict | None:
    """Read a JSON object from storage, returning None when it is missing or unreadable."""
    try:
        response = client.get_object(Bucket=bucket, Key=key)
    except Exception:
        return None
    return json.loads(response["Body"].read().decode("utf-8"))


def read_local_json(path: Path) -> dict | None:
    """Read a local JSON file, returning None when it is missing or unreadable."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _entry_title(slug: str, page_json: dict | None) -> str:
    """Choose the best available human-readable title for an index entry."""
    if not isinstance(page_json, dict):
        return slug
    for key in ("title", "name"):
        value = page_json.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    standard = page_json.get("standard")
    if isinstance(standard, dict):
        for key in ("title", "name", "id"):
            value = standard.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return slug


def _entry_description(slug: str, page_json: dict | None) -> str:
    """Choose the best available description for an index entry."""
    if not isinstance(page_json, dict):
        return f"Index entry for {slug_to_title(slug)}."
    for key in ("notes", "description", "summary"):
        value = page_json.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    standard = page_json.get("standard")
    if isinstance(standard, dict):
        for key in ("summary", "description"):
            value = standard.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    markdown = page_json.get("markdown")
    if isinstance(markdown, dict):
        summary = markdown.get("summary")
        if isinstance(summary, str) and summary.strip():
            return summary.strip()
    return f"Index entry for {slug_to_title(slug)}."


def is_image_asset_name(name: str) -> bool:
    """Return whether a filename should count as a real image asset in BGML image stats."""
    if name == "manifest.json":
        return False
    return PurePosixPath(name).suffix.lower() in IMAGE_EXTENSIONS


def build_entry(prefix: str, folder: str, keys_set: set[str], page_json: dict | None) -> dict:
    """Build one BGML index entry from a content folder discovered in Spaces."""
    folder_path = PurePosixPath(folder)
    relative_folder = folder.removeprefix(prefix).strip("/")
    relative_parts = PurePosixPath(relative_folder).parts
    group = relative_parts[0] if relative_parts else "root"
    category = relative_parts[1] if len(relative_parts) > 1 else group
    slug = folder_path.name
    title = _entry_title(slug, page_json)
    images_prefix = f"{folder}/images/"
    image_count = sum(
        1
        for key in keys_set
        if key.startswith(images_prefix) and is_image_asset_name(PurePosixPath(key).name)
    )

    entry = {
        "id": relative_folder or "root",
        "slug": slug,
        "category": category,
        "group": group,
        "status": (page_json or {}).get("status", "active"),
        "name": slug_to_title(title),
        "description": _entry_description(slug, page_json),
        "files": {
            "markdown": f"{folder}/page.md" if f"{folder}/page.md" in keys_set else None,
            "yaml": f"{folder}/page.yaml" if f"{folder}/page.yaml" in keys_set else None,
            "json": f"{folder}/page.json" if f"{folder}/page.json" in keys_set else None,
            "images": {"path": images_prefix, "count": image_count} if image_count else None,
            "screenshot": f"{folder}/screenshot.png" if f"{folder}/screenshot.png" in keys_set else None,
        },
        "tags": [part for part in relative_folder.split("/") if part],
    }
    return entry


def discover_local_folders(source_dir: Path) -> list[Path]:
    """Discover content folders from a local source tree using Markdown or JSON pages."""
    folders = {
        page.parent
        for pattern in ("**/page.md", "**/page.json")
        for page in source_dir.glob(pattern)
    }
    return sorted(folders)


def build_local_entry(source_dir: Path, folder: Path, prefix: str) -> dict:
    """Build one BGML index entry from a local source folder."""
    relative_folder = folder.relative_to(source_dir).as_posix()
    relative_parts = PurePosixPath(relative_folder).parts
    group = relative_parts[0] if relative_parts else "root"
    category = relative_parts[1] if len(relative_parts) > 1 else group
    slug = folder.name
    page_json = read_local_json(folder / "page.json")
    images_dir = folder / "images"
    image_count = 0
    if images_dir.exists():
        image_count = sum(1 for path in images_dir.rglob("*") if path.is_file() and is_image_asset_name(path.name))

    folder_key = f"{prefix.rstrip('/')}/{relative_folder}".strip("/")
    images_prefix = f"{folder_key}/images/"
    return {
        "id": relative_folder or "root",
        "slug": slug,
        "category": category,
        "group": group,
        "status": (page_json or {}).get("status", "active"),
        "name": slug_to_title(_entry_title(slug, page_json)),
        "description": _entry_description(slug, page_json),
        "files": {
            "markdown": f"{folder_key}/page.md" if (folder / "page.md").exists() else None,
            "yaml": f"{folder_key}/page.yaml" if (folder / "page.yaml").exists() else None,
            "json": f"{folder_key}/page.json" if (folder / "page.json").exists() else None,
            "images": {"path": images_prefix, "count": image_count} if image_count else None,
            "screenshot": f"{folder_key}/screenshot.png" if (folder / "screenshot.png").exists() else None,
        },
        "tags": [part for part in relative_folder.split("/") if part],
    }


def build_index(brand_name: str, client_id: str, bucket: str, prefix: str, entries: list[dict]) -> dict:
    """Assemble the final BGML envelope from discovered index entries."""
    entries_by_group: dict[str, list[dict]] = defaultdict(list)
    standards: list[dict] = []
    for entry in entries:
        group = entry["group"]
        entries_by_group[group].append(entry)
        if group == "standards":
            standards.append(entry)

    return {
        "bgml": {
            "version": "1.0",
            "schema": "https://brandsemantics.com/schema/bgml/1.0",
            "meta": {
                "brand": brand_name,
                "clientId": client_id,
                "layer": 1,
                "sourceBucket": bucket,
                "sourcePrefix": f"{prefix.strip('/')}/",
            },
            "precedence": [
                "safety",
                "regulatory",
                "legal",
                "core-brand",
                "standards",
                "applications",
                "audiences",
                "markets",
                "exceptions",
            ],
            "standards": standards,
            "collections": dict(sorted(entries_by_group.items())),
            "stats": {
                "totalPages": len(entries),
                "standards": len(entries_by_group.get("standards", [])),
                "toolkits": len(entries_by_group.get("toolkits", [])),
                "assetLibrary": len(entries_by_group.get("asset-library", [])),
                "digital": len(entries_by_group.get("digital", [])),
            },
        }
    }


def upload_source_tree(client, bucket: str, prefix: str, source_dir: Path) -> None:
    """Upload a local source tree so Spaces content and the rebuilt index stay aligned."""
    for path in sorted(source_dir.rglob("*")):
        if path.is_dir():
            continue
        relative = path.relative_to(source_dir).as_posix()
        key = f"{prefix.rstrip('/')}/{relative}".strip("/")
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        client.upload_file(str(path), bucket, key, ExtraArgs={"ContentType": content_type})


def build_index_from_spaces(client, bucket: str, prefix: str, brand_name: str, client_id: str) -> dict:
    """Build a BGML index from content already uploaded into Spaces."""
    full_prefix = f"{prefix.strip('/')}/"
    keys = list_keys(client, bucket, full_prefix)
    keys_set = set(keys)

    folders = {
        str(PurePosixPath(key).parent)
        for key in keys
        if key.endswith("/page.md") or key.endswith("/page.json")
    }

    entries = []
    for folder in sorted(folders):
        page_json = read_json(client, bucket, f"{folder}/page.json")
        entries.append(build_entry(full_prefix, folder, keys_set, page_json))

    return build_index(brand_name, client_id, bucket, prefix, entries)


def build_index_from_local(source_dir: Path, prefix: str, brand_name: str, client_id: str, bucket: str) -> dict:
    """Build a BGML index from a local source tree."""
    entries = [build_local_entry(source_dir, folder, prefix) for folder in discover_local_folders(source_dir)]
    return build_index(brand_name, client_id, bucket, prefix, entries)


def main() -> None:
    """Rebuild a comprehensive BGML index and upload the result."""
    parser = argparse.ArgumentParser(description="Rebuild a comprehensive BGML index from Spaces or a local source tree.")
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--brand-name", required=True)
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--source-dir")
    parser.add_argument("--sync-source", action="store_true")
    parser.add_argument("--skip-upload", action="store_true")
    parser.add_argument("--output-key", default="page-index.json")
    parser.add_argument("--write-local", default="dist/page-index.json")
    args = parser.parse_args()

    prefix = args.prefix.strip("/")
    client = build_client()
    source_dir = Path(args.source_dir).resolve() if args.source_dir else None

    if source_dir and args.sync_source:
        upload_source_tree(client, args.bucket, prefix, source_dir)

    if source_dir:
        index = build_index_from_local(source_dir, prefix, args.brand_name, args.client_id, args.bucket)
    else:
        index = build_index_from_spaces(client, args.bucket, prefix, args.brand_name, args.client_id)

    local_path = Path(args.write_local)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(json.dumps(index, indent=2), encoding="utf-8")

    output_key = args.output_key.strip("/")
    if "/" not in output_key:
        output_key = f"{prefix.rstrip('/')}/{output_key}".strip("/")

    print(f"wrote {local_path}")
    if not args.skip_upload:
        client.put_object(
            Bucket=args.bucket,
            Key=output_key,
            Body=json.dumps(index, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        print(f"uploaded s3://{args.bucket}/{output_key}")
    else:
        print("skipped upload")
    print(json.dumps(index["bgml"]["stats"], indent=2))


if __name__ == "__main__":
    main()
