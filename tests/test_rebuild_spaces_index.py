"""Tests for the Spaces BGML index rebuild helpers."""

import importlib.util
from pathlib import Path


def _load_rebuild_module():
    """Load the rebuild_spaces_index script as a module for direct helper tests."""
    module_path = Path(__file__).resolve().parents[1] / "tools" / "rebuild_spaces_index.py"
    spec = importlib.util.spec_from_file_location("rebuild_spaces_index", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_index_from_local_includes_grid_system_images(tmp_path):
    module = _load_rebuild_module()
    source_dir = tmp_path / "advanced-user"
    grid_dir = source_dir / "standards" / "grid-system"
    grid_dir.mkdir(parents=True)
    (grid_dir / "page.md").write_text("# Grid system\n", encoding="utf-8")
    (grid_dir / "page.json").write_text(
        '{"standard":{"title":"Grid system"},"markdown":{"summary":"Grid layout guidance."}}',
        encoding="utf-8",
    )
    images_dir = grid_dir / "images"
    images_dir.mkdir()
    (images_dir / "grid-example.png").write_bytes(b"fake")
    (images_dir / "manifest.json").write_text("{}", encoding="utf-8")
    (images_dir / "notes.txt").write_text("ignore me", encoding="utf-8")
    (grid_dir / "screenshot.png").write_bytes(b"fake")

    index = module.build_index_from_local(
        source_dir=source_dir,
        prefix="brand-pwc/advanced-user",
        brand_name="PwC",
        client_id="pwc",
        bucket="brand-store",
    )

    standards = index["bgml"]["standards"]
    assert len(standards) == 1
    entry = standards[0]
    assert entry["id"] == "standards/grid-system"
    assert entry["name"] == "Grid System"
    assert entry["description"] == "Grid layout guidance."
    assert entry["files"]["markdown"] == "brand-pwc/advanced-user/standards/grid-system/page.md"
    assert entry["files"]["json"] == "brand-pwc/advanced-user/standards/grid-system/page.json"
    assert entry["files"]["images"]["path"] == "brand-pwc/advanced-user/standards/grid-system/images/"
    assert entry["files"]["images"]["count"] == 1
    assert entry["files"]["screenshot"] == "brand-pwc/advanced-user/standards/grid-system/screenshot.png"


def test_build_entry_counts_only_real_image_assets():
    module = _load_rebuild_module()
    entry = module.build_entry(
        "brand-pwc/advanced-user/",
        "brand-pwc/advanced-user/standards/grid-system",
        {
            "brand-pwc/advanced-user/standards/grid-system/page.md",
            "brand-pwc/advanced-user/standards/grid-system/images/grid-example.png",
            "brand-pwc/advanced-user/standards/grid-system/images/manifest.json",
            "brand-pwc/advanced-user/standards/grid-system/images/readme.txt",
            "brand-pwc/advanced-user/standards/grid-system/images/diagram.svg",
        },
        {"standard": {"title": "Grid system"}, "markdown": {"summary": "Grid layout guidance."}},
    )

    assert entry["files"]["images"]["count"] == 2


def test_build_index_from_local_discovers_json_only_pages(tmp_path):
    module = _load_rebuild_module()
    source_dir = tmp_path / "advanced-user"
    page_dir = source_dir / "standards" / "json-only-standard"
    page_dir.mkdir(parents=True)
    (page_dir / "page.json").write_text(
        '{"standard":{"title":"JSON only"},"description":"Structured-only guidance."}',
        encoding="utf-8",
    )

    index = module.build_index_from_local(
        source_dir=source_dir,
        prefix="brand-pwc/advanced-user",
        brand_name="PwC",
        client_id="pwc",
        bucket="brand-store",
    )

    standards = index["bgml"]["standards"]
    assert len(standards) == 1
    entry = standards[0]
    assert entry["id"] == "standards/json-only-standard"
    assert entry["files"]["markdown"] is None
    assert entry["files"]["json"] == "brand-pwc/advanced-user/standards/json-only-standard/page.json"
