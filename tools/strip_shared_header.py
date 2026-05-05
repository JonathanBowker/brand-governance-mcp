#!/usr/bin/env python
"""Remove the repeated shared advanced-user header from page Markdown files."""

import argparse
from pathlib import Path

from src.utils.markdown_cleanup import strip_shared_header_block


def process_file(path: Path, write: bool) -> bool:
    """Strip the shared header from one file and optionally write the cleaned content."""
    original = path.read_text(encoding="utf-8")
    cleaned, changed = strip_shared_header_block(original)
    if changed and write:
        path.write_text(cleaned, encoding="utf-8")
    return changed


def iter_markdown_files(root: Path) -> list[Path]:
    """Return either the target file or all nested page.md files under a directory."""
    if root.is_file():
        return [root]
    return sorted(path for path in root.rglob("page.md") if path.is_file())


def main() -> None:
    """Run the shared-header cleanup in dry-run or write mode."""
    parser = argparse.ArgumentParser(
        description="Remove the shared advanced-user header block from markdown files."
    )
    parser.add_argument(
        "target",
        help="A page.md file or a directory to scan recursively for page.md files.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write cleaned content back to disk. Without this flag the script runs as a dry run.",
    )
    args = parser.parse_args()

    target = Path(args.target)
    files = iter_markdown_files(target)
    changed = 0

    for path in files:
        file_changed = process_file(path, write=args.write)
        if file_changed:
            changed += 1
            action = "cleaned" if args.write else "would clean"
            print(f"{action}: {path}")

    mode = "updated" if args.write else "matched"
    print(f"{mode} {changed} of {len(files)} file(s)")


if __name__ == "__main__":
    main()
