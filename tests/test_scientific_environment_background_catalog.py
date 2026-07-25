from __future__ import annotations

import ast
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw
import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_SCRIPT = (
    REPO_ROOT / "scripts/catalog_scientific_environment_backgrounds.py"
)


def test_catalog_script_stays_simulator_and_converter_neutral() -> None:
    tree = ast.parse(CATALOG_SCRIPT.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    forbidden = {
        name
        for name in imported
        if name == "pxr"
        or name.startswith("pxr.")
        or name == "omni"
        or name.startswith("omni.")
        or name == "isaacsim"
        or name.startswith("isaacsim.")
        or name == "convert_asset"
        or name.startswith("convert_asset.")
    }
    assert forbidden == set()


def test_catalog_discovers_only_matching_complete_scene_thumbnails(
    tmp_path: Path,
) -> None:
    dataset = tmp_path / "upstream"
    _write_candidate(dataset, "lab_001", foreground=(30, 90, 160))
    _write_candidate(dataset, "lab_003", foreground=(160, 80, 30))
    extra = dataset / "Labs/lab_003/.thumbs/256x256/unrelated.usd.png"
    Image.new("RGB", (256, 256), "red").save(extra)
    instrument = dataset / "Instruments/beaker/beaker.usd"
    instrument.parent.mkdir(parents=True)
    instrument.write_bytes(b"instrument")

    module = _load_catalog_module()
    candidates = module.discover_candidates(dataset)

    assert [candidate.source_id for candidate in candidates] == [
        "lab_001",
        "lab_003",
    ]
    assert candidates[0].source_usd.name == "lab_001.usd"
    assert candidates[0].thumbnail.name == "lab_001.usd.png"


def test_catalog_writes_auditable_inventory_and_contact_sheets(
    tmp_path: Path,
) -> None:
    dataset = tmp_path / "upstream"
    _write_candidate(dataset, "lab_001", foreground=(30, 90, 160))
    _write_candidate(dataset, "lab_003", foreground=(160, 80, 30))
    out = tmp_path / "catalog"

    module = _load_catalog_module()
    catalog = module.build_catalog(
        dataset_root=dataset,
        output_root=out,
        expected_count=2,
        shortlist_size=1,
        sheet_columns=2,
        sheet_rows=1,
    )

    assert catalog["schema_version"] == (
        "scenario-forge-scientific-environment-thumbnail-catalog/v0.1"
    )
    assert catalog["candidate_count"] == 2
    assert [entry["candidate_id"] for entry in catalog["entries"]] == [
        "scientific_environment_001",
        "scientific_environment_003",
    ]
    assert sorted(entry["deterministic_rank"] for entry in catalog["entries"]) == [
        1,
        2,
    ]
    assert all(
        len(entry["source_sha256"]) == 64
        and len(entry["thumbnail_sha256"]) == 64
        for entry in catalog["entries"]
    )
    assert (out / "catalog.json").is_file()
    assert (out / "contact_sheets/all_001.png").is_file()
    assert (out / "shortlist/contact_sheet.png").is_file()
    assert len(list((out / "thumbnails").glob("*.png"))) == 2

    persisted = json.loads((out / "catalog.json").read_text(encoding="utf-8"))
    assert persisted == catalog


def test_admission_request_contains_only_hash_bound_visual_passes(
    tmp_path: Path,
) -> None:
    dataset = tmp_path / "upstream"
    _write_candidate(dataset, "lab_001", foreground=(30, 90, 160))
    _write_candidate(dataset, "lab_003", foreground=(160, 80, 30))
    out = tmp_path / "catalog"
    module = _load_catalog_module()
    catalog = module.build_catalog(
        dataset_root=dataset,
        output_root=out,
        expected_count=2,
        shortlist_size=2,
    )
    by_id = {entry["candidate_id"]: entry for entry in catalog["entries"]}
    evidence = tmp_path / "scientific_environment_001.png"
    evidence.write_bytes(b"hash-bound render evidence")
    review_document: dict[str, Any] = {
        "catalog_digest": catalog["catalog_digest"],
        "reviews": {
            "scientific_environment_001": {
                "status": "PASS",
                "selected_for_admission": True,
                "selection_rank": 1,
                "thumbnail_sha256": by_id["scientific_environment_001"][
                    "thumbnail_sha256"
                ],
                "visible_evidence": (
                    "Complete furnished room with useful work surfaces."
                ),
                "render_evidence": {
                    "path": str(evidence),
                    "sha256": sha256(evidence.read_bytes()).hexdigest(),
                    "view": "authored",
                },
            },
            "scientific_environment_003": {
                "status": "WARN",
                "selected_for_admission": False,
                "thumbnail_sha256": by_id["scientific_environment_003"][
                    "thumbnail_sha256"
                ],
                "visible_evidence": "Room is visible but framing is too distant.",
            },
        },
    }
    request_path = out / "convertasset_batch_admission.yaml"

    request = module.build_admission_request(
        catalog=catalog,
        review_document=review_document,
        output_path=request_path,
        max_items=10,
    )

    assert request["schema_version"] == (
        "scenario-forge-convertasset-batch-admission-request/v0.1"
    )
    assert request["target"] == {
        "consumer_profile": "scenario-forge",
        "runtime_profile": "isaac41",
        "asset_role": "visual_static_environment",
    }
    assert [item["candidate_id"] for item in request["items"]] == [
        "scientific_environment_001"
    ]
    assert request["items"][0]["source_scope"] == "/World"
    assert request["items"][0]["source_usd"].endswith(
        "/Labs/lab_001/lab_001.usd"
    )
    assert request["items"][0]["visual_review"]["status"] == "PASS"
    assert request["items"][0]["visual_review"]["render_evidence"] == {
        "path": str(evidence),
        "sha256": sha256(evidence.read_bytes()).hexdigest(),
        "view": "authored",
    }
    assert "command" not in yaml.safe_dump(request)
    assert yaml.safe_load(request_path.read_text(encoding="utf-8")) == request


def test_admission_request_accepts_explicitly_selected_visual_warning(
    tmp_path: Path,
) -> None:
    dataset = tmp_path / "upstream"
    _write_candidate(dataset, "lab_001", foreground=(30, 90, 160))
    module = _load_catalog_module()
    catalog = module.build_catalog(
        dataset_root=dataset,
        output_root=tmp_path / "catalog",
        expected_count=1,
        shortlist_size=1,
    )
    entry = catalog["entries"][0]
    evidence = tmp_path / "retake.png"
    evidence.write_bytes(b"warning render")

    request = module.build_admission_request(
        catalog=catalog,
        review_document={
            "catalog_digest": catalog["catalog_digest"],
            "reviews": {
                entry["candidate_id"]: {
                    "status": "WARN",
                    "selected_for_admission": True,
                    "selection_rank": 1,
                    "thumbnail_sha256": entry["thumbnail_sha256"],
                    "visible_evidence": "Rich room with an overexposed ceiling.",
                    "producer_attention": [
                        "Recover ceiling detail in the post-normalization render."
                    ],
                    "render_evidence": {
                        "path": str(evidence),
                        "sha256": sha256(evidence.read_bytes()).hexdigest(),
                        "view": "authored",
                    },
                }
            },
        },
        output_path=tmp_path / "request.yaml",
        max_items=1,
    )

    assert [item["candidate_id"] for item in request["items"]] == [
        "scientific_environment_001"
    ]
    assert request["items"][0]["visual_review"]["status"] == "WARN"
    assert request["items"][0]["producer_attention"] == [
        "Recover ceiling detail in the post-normalization render."
    ]


def test_admission_rejects_stale_review_thumbnail_hash(tmp_path: Path) -> None:
    dataset = tmp_path / "upstream"
    _write_candidate(dataset, "lab_001", foreground=(30, 90, 160))
    module = _load_catalog_module()
    catalog = module.build_catalog(
        dataset_root=dataset,
        output_root=tmp_path / "catalog",
        expected_count=1,
        shortlist_size=1,
    )

    with pytest.raises(ValueError, match="thumbnail hash"):
        module.build_admission_request(
            catalog=catalog,
            review_document={
                "catalog_digest": catalog["catalog_digest"],
                "reviews": {
                    "scientific_environment_001": {
                        "status": "PASS",
                        "thumbnail_sha256": "0" * 64,
                        "visible_evidence": "Visible room.",
                    }
                },
            },
            output_path=tmp_path / "request.yaml",
            max_items=1,
        )


def test_admission_rejects_stale_catalog_or_render_evidence(
    tmp_path: Path,
) -> None:
    dataset = tmp_path / "upstream"
    _write_candidate(dataset, "lab_001", foreground=(30, 90, 160))
    module = _load_catalog_module()
    catalog = module.build_catalog(
        dataset_root=dataset,
        output_root=tmp_path / "catalog",
        expected_count=1,
        shortlist_size=1,
    )
    entry = catalog["entries"][0]
    evidence = tmp_path / "retake.png"
    evidence.write_bytes(b"render")
    review = {
        "catalog_digest": "0" * 64,
        "reviews": {
            entry["candidate_id"]: {
                "status": "PASS",
                "selected_for_admission": True,
                "thumbnail_sha256": entry["thumbnail_sha256"],
                "visible_evidence": "Visible room.",
                "render_evidence": {
                    "path": str(evidence),
                    "sha256": sha256(evidence.read_bytes()).hexdigest(),
                    "view": "authored",
                },
            }
        },
    }

    with pytest.raises(ValueError, match="catalog digest"):
        module.build_admission_request(
            catalog=catalog,
            review_document=review,
            output_path=tmp_path / "request.yaml",
        )

    review["catalog_digest"] = catalog["catalog_digest"]
    review["reviews"][entry["candidate_id"]]["render_evidence"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="render-evidence hash"):
        module.build_admission_request(
            catalog=catalog,
            review_document=review,
            output_path=tmp_path / "request.yaml",
        )


def test_admission_rejects_tampered_catalog_or_selected_source(
    tmp_path: Path,
) -> None:
    dataset = tmp_path / "upstream"
    _write_candidate(dataset, "lab_001", foreground=(30, 90, 160))
    module = _load_catalog_module()
    catalog = module.build_catalog(
        dataset_root=dataset,
        output_root=tmp_path / "catalog",
        expected_count=1,
        shortlist_size=1,
    )
    entry = catalog["entries"][0]
    evidence = tmp_path / "retake.png"
    evidence.write_bytes(b"render")
    review = {
        "catalog_digest": catalog["catalog_digest"],
        "reviews": {
            entry["candidate_id"]: {
                "status": "PASS",
                "selected_for_admission": True,
                "thumbnail_sha256": entry["thumbnail_sha256"],
                "visible_evidence": "Visible room.",
                "render_evidence": {
                    "path": str(evidence),
                    "sha256": sha256(evidence.read_bytes()).hexdigest(),
                    "view": "authored",
                },
            }
        },
    }

    entry["source_scope"] = "/Tampered"
    with pytest.raises(ValueError, match="catalog digest"):
        module.build_admission_request(
            catalog=catalog,
            review_document=review,
            output_path=tmp_path / "request.yaml",
        )

    catalog = json.loads(
        (tmp_path / "catalog/catalog.json").read_text(encoding="utf-8")
    )
    review["catalog_digest"] = catalog["catalog_digest"]
    Path(catalog["entries"][0]["source_usd"]).write_bytes(b"changed source")
    with pytest.raises(ValueError, match="source hash is stale"):
        module.build_admission_request(
            catalog=catalog,
            review_document=review,
            output_path=tmp_path / "request.yaml",
        )


def _write_candidate(
    dataset: Path,
    source_id: str,
    *,
    foreground: tuple[int, int, int],
) -> None:
    scene_dir = dataset / "Labs" / source_id
    scene_dir.mkdir(parents=True)
    (scene_dir / f"{source_id}.usd").write_bytes(
        "#usda 1.0\n(defaultPrim = \"World\")\ndef Xform \"World\" {}\n".encode(
            "utf-8"
        )
    )
    thumbnail_dir = scene_dir / ".thumbs/256x256"
    thumbnail_dir.mkdir(parents=True)
    image = Image.new("RGB", (256, 256), (238, 238, 238))
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 30, 235, 230), fill=foreground)
    draw.line((20, 30, 235, 230), fill=(255, 255, 255), width=6)
    image.save(thumbnail_dir / f"{source_id}.usd.png")


def _load_catalog_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "scenario_forge_scientific_environment_catalog",
        CATALOG_SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
