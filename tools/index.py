#!/usr/bin/env python
"""Generate a minimal BGML index from a local brand content folder."""

import argparse
import json
from pathlib import Path


def main() -> None:
    """Scan a brand folder and write a simple standards-first BGML index."""
    parser = argparse.ArgumentParser(description="Generate a minimal BGML index from a brand folder.")
    parser.add_argument("--brand-dir", required=True)
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--brand-name", required=True)
    args = parser.parse_args()

    brand_dir = Path(args.brand_dir)
    standards = []
    for page in sorted(brand_dir.glob("standards/**/page.md")):
        folder = page.parent
        standard_id = folder.name if folder.name != "standards" else "root"
        images = folder / "images"
        standards.append(
            {
                "id": standard_id,
                "category": "visual" if standard_id not in {"writing-for-pwc", "tone-of-voice"} else "verbal",
                "tier": "standards",
                "status": "active",
                "name": standard_id.replace("-", " ").title(),
                "description": f"Brand standard for {standard_id}.",
                "files": {
                    "markdown": page.relative_to(brand_dir).as_posix(),
                    "yaml": (folder / "page.yaml").relative_to(brand_dir).as_posix(),
                    "json": (folder / "page.json").relative_to(brand_dir).as_posix() if (folder / "page.json").exists() else None,
                    "images": {"path": images.relative_to(brand_dir).as_posix() + "/", "count": 0} if images.exists() else None,
                },
                "keyRules": [],
                "related": [],
                "tags": [standard_id],
                "version": "2026.1",
                "lastModified": "2026-05-04",
            }
        )

    index = {
        "bgml": {
            "version": "1.0",
            "schema": "https://brandsemantics.com/schema/bgml/1.0",
            "meta": {"brand": args.brand_name, "clientId": args.client_id, "layer": 1},
            "precedence": ["safety", "regulatory", "legal", "core-brand", "standards", "applications", "audiences", "markets", "exceptions"],
            "standards": standards,
        }
    }
    out = brand_dir / "bgml-index.json"
    out.write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
