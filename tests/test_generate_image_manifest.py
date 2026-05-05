"""Tests for the image manifest generation helpers."""

import importlib.util
from pathlib import Path


def _load_script_module():
    """Load the generate_image_manifest script for direct helper testing."""
    module_path = Path(__file__).resolve().parents[1] / "tools" / "generate_image_manifest.py"
    spec = importlib.util.spec_from_file_location("generate_image_manifest", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_heuristic_asset_metadata_uses_standard_context(tmp_path):
    module = _load_script_module()
    image_path = tmp_path / "cq5dam.web.1280.1280.png"
    image_path.write_bytes(b"fake")

    asset = module.heuristic_asset_metadata(image_path, "grid-system", "Grid system")
    assert asset.filename == "cq5dam.web.1280.1280.png"
    assert asset.title
    assert asset.description == "Reference image from the Grid system standard."
    assert asset.usage == "reference"
    assert "grid-system" in asset.tags


def test_supports_openai_vision_excludes_svg(tmp_path):
    module = _load_script_module()
    raster = tmp_path / "grid.png"
    vector = tmp_path / "grid.svg"
    raster.write_bytes(b"fake")
    vector.write_text("<svg />", encoding="utf-8")

    assert module.supports_openai_vision(raster) is True
    assert module.supports_openai_vision(vector) is False


def test_merged_asset_metadata_preserves_existing_without_overwrite():
    module = _load_script_module()
    generated = module.ImageAssetMetadata(
        filename="grid.png",
        title="Grid reference",
        description="Generated description.",
        section="Standard grid",
        usage="reference",
        tags=["grid-system"],
    )
    existing = module.ImageAssetMetadata(
        filename="grid.png",
        title="Standard 12x12 page layout grid",
        description="Reference image showing the grid.",
        section="Standard grid",
        usage="primary reference",
        tags=["grid-system", "12x12-grid"],
    )

    merged = module.merged_asset_metadata(generated, existing, overwrite_existing=False)
    assert merged.title == "Standard 12x12 page layout grid"
    assert merged.usage == "primary reference"
    assert "12x12-grid" in merged.tags


def test_generate_main_uses_inferred_standard_id(tmp_path, monkeypatch, capsys):
    module = _load_script_module()
    standard_dir = tmp_path / "standards" / "grid-system"
    images_dir = standard_dir / "images"
    images_dir.mkdir(parents=True)
    (standard_dir / "page.md").write_text("# Grid system\n", encoding="utf-8")
    (images_dir / "grid.png").write_bytes(b"fake")

    monkeypatch.setattr(
        "sys.argv",
        [
            "generate_image_manifest.py",
            "--standard-dir",
            str(standard_dir),
            "--heuristic-only",
        ],
    )

    module.main()

    manifest_path = images_dir / "manifest.json"
    manifest = module.json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["standardId"] == "standards/grid-system"
    assert manifest["assets"][0]["filename"] == "grid.png"
    assert "Wrote manifest with 1 assets" in capsys.readouterr().out
