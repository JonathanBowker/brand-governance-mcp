#!/usr/bin/env python
import argparse
import json
from collections import defaultdict
from pathlib import PurePosixPath

import boto3
from botocore.config import Config

from src.config import settings


def slug_to_title(slug: str) -> str:
    return slug.replace("_q_", " ").replace("-", " ").replace("_", " ").title()


def build_client():
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
    keys: list[str] = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for item in page.get("Contents", []):
            keys.append(item["Key"])
    return keys


def read_json(client, bucket: str, key: str) -> dict | None:
    try:
        response = client.get_object(Bucket=bucket, Key=key)
    except Exception:
        return None
    return json.loads(response["Body"].read().decode("utf-8"))


def build_entry(prefix: str, folder: str, keys_set: set[str], page_json: dict | None) -> dict:
    folder_path = PurePosixPath(folder)
    relative_folder = folder.removeprefix(prefix).strip("/")
    relative_parts = PurePosixPath(relative_folder).parts
    slug = folder_path.name
    title = (page_json or {}).get("title") or slug
    images_prefix = f"{folder}/images/"
    image_count = sum(1 for key in keys_set if key.startswith(images_prefix))

    entry = {
        "id": relative_folder,
        "slug": slug,
        "category": relative_parts[1] if len(relative_parts) > 1 else relative_parts[0],
        "group": relative_parts[0] if relative_parts else "root",
        "status": (page_json or {}).get("status", "active"),
        "name": slug_to_title(title),
        "description": (page_json or {}).get("notes") or f"Index entry for {slug_to_title(slug)}.",
        "files": {
            "markdown": f"{folder}/page.md",
            "yaml": f"{folder}/page.yaml" if f"{folder}/page.yaml" in keys_set else None,
            "json": f"{folder}/page.json" if f"{folder}/page.json" in keys_set else None,
            "images": {"path": images_prefix, "count": image_count} if image_count else None,
            "screenshot": f"{folder}/screenshot.png" if f"{folder}/screenshot.png" in keys_set else None,
        },
        "tags": [part for part in relative_folder.split("/") if part],
    }
    return entry


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild a comprehensive page-index.json from a Spaces prefix.")
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--brand-name", required=True)
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--output-key", default="page-index.json")
    parser.add_argument("--write-local", default="dist/page-index.json")
    args = parser.parse_args()

    prefix = args.prefix.strip("/")
    full_prefix = f"{prefix}/"
    client = build_client()
    keys = list_keys(client, args.bucket, full_prefix)
    keys_set = set(keys)

    page_md_keys = sorted(key for key in keys if key.endswith("/page.md"))
    entries_by_group: dict[str, list[dict]] = defaultdict(list)
    standards: list[dict] = []

    for page_md_key in page_md_keys:
        folder = str(PurePosixPath(page_md_key).parent)
        page_json = read_json(client, args.bucket, f"{folder}/page.json")
        entry = build_entry(full_prefix, folder, keys_set, page_json)
        group = entry["group"]
        entries_by_group[group].append(entry)
        if group == "standards":
            standards.append(entry)

    index = {
        "bgml": {
            "version": "1.0",
            "schema": "https://brandsemantics.com/schema/bgml/1.0",
            "meta": {
                "brand": args.brand_name,
                "clientId": args.client_id,
                "layer": 1,
                "sourceBucket": args.bucket,
                "sourcePrefix": full_prefix,
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
                "totalPages": len(page_md_keys),
                "standards": len(entries_by_group.get("standards", [])),
                "toolkits": len(entries_by_group.get("toolkits", [])),
                "assetLibrary": len(entries_by_group.get("asset-library", [])),
                "digital": len(entries_by_group.get("digital", [])),
            },
        }
    }

    local_path = PurePosixPath(args.write_local)
    Path(str(local_path)).parent.mkdir(parents=True, exist_ok=True)
    Path(str(local_path)).write_text(json.dumps(index, indent=2), encoding="utf-8")

    output_key = args.output_key.strip("/")
    if "/" not in output_key:
        output_key = f"{full_prefix}{output_key}"

    client.put_object(
        Bucket=args.bucket,
        Key=output_key,
        Body=json.dumps(index, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
    print(f"wrote {local_path}")
    print(f"uploaded s3://{args.bucket}/{output_key}")
    print(json.dumps(index["bgml"]["stats"], indent=2))


if __name__ == "__main__":
    from pathlib import Path

    main()
