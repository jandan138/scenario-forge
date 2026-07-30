from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest
import yaml

from scenario_forge.generation.source_resolver import (
    ScenarioSourceBindingError,
    resolve_scenario_source_bindings,
)
from tests.test_convert_asset_adapter import (
    _write_articulated_handoff,
    _write_source_bound_handoff,
    _write_visual_static_handoff,
)
from tests.test_scenario_package_compiler import _write_source_scene


REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_bindings(
    path: Path,
    bindings: dict[str, object],
    *,
    schema_version: str = "scenario-source-bindings/v0.1",
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": schema_version,
                "bindings": bindings,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def test_source_bindings_schema_artifact_exists_and_declares_two_resolvers() -> None:
    schema_path = (
        REPO_ROOT
        / "src/scenario_forge/schemas/jsonschema/scenario-source-bindings-v0.1.schema.json"
    )

    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["schema_version"]["const"] == (
        "scenario-source-bindings/v0.1"
    )
    resolver_variants = schema["$defs"]["binding"]["oneOf"]
    assert {
        variant["properties"]["resolver"]["const"] for variant in resolver_variants
    } == {"local_usd", "convert_asset_package"}


def test_source_bindings_v02_schema_requires_explicit_convert_asset_usage() -> None:
    schema_path = (
        REPO_ROOT
        / "src/scenario_forge/schemas/jsonschema/scenario-source-bindings-v0.2.schema.json"
    )

    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == (
        "scenario-source-bindings/v0.2"
    )
    convert_asset = next(
        variant
        for variant in schema["$defs"]["binding"]["oneOf"]
        if variant["properties"]["resolver"]["const"] == "convert_asset_package"
    )
    assert "usage" in convert_asset["required"]
    assert convert_asset["properties"]["usage"]["enum"] == [
        "scene_overlay",
        "rigid_object",
        "articulated_object",
        "visual_static_environment",
        "visual_static_object",
    ]


def test_local_usd_binding_resolves_paths_relative_to_the_binding_file(
    tmp_path: Path,
) -> None:
    binding_root = tmp_path / "portable-build-input"
    source_usd = _write_source_scene(binding_root)
    digest = sha256(source_usd.read_bytes()).hexdigest()
    bindings_path = _write_bindings(
        binding_root / "bindings.yaml",
        {
            "scientific_workbench_environment": {
                "resolver": "local_usd",
                "source_usd": "source/scene.usda",
                "role": "environment",
                "license": "CC-BY-NC-4.0",
                "source_uri": "LabUtopia:lab_001_fixture",
                "attribution": ["LabUtopia fixture"],
                "redistributable": False,
                "exclude_relative_paths": ["_reports"],
                "root_prim_path": "/World",
                "expected_sha256": f"sha256:{digest}",
            }
        },
    )

    sources = resolve_scenario_source_bindings(bindings_path)

    source = sources["scientific_workbench_environment"]
    assert source.asset_id == "scientific_workbench_environment"
    assert source.source_usd == source_usd
    assert source.role == "environment"
    assert source.source_uri == "LabUtopia:lab_001_fixture"
    assert source.attribution == ("LabUtopia fixture",)
    assert source.redistributable is False
    assert source.exclude_relative_paths == ("_reports",)
    assert source.root_prim_path == "/World"
    assert source.expected_sha256 == f"sha256:{digest}"
    assert source.upstream_package is None


def test_convert_asset_binding_uses_the_existing_source_bound_handoff_adapter(
    tmp_path: Path,
) -> None:
    source_usd = _write_source_scene(tmp_path)
    _, package_dir, manifest_path, _ = _write_source_bound_handoff(
        tmp_path / "handoff",
        source_usd=source_usd,
    )
    bindings_path = _write_bindings(
        tmp_path / "bindings.yaml",
        {
            "scientific_workbench_dryingbox_03_dynamic": {
                "resolver": "convert_asset_package",
                "source_usd": source_usd.relative_to(tmp_path).as_posix(),
                "package_dir": package_dir.relative_to(tmp_path).as_posix(),
                "manifest_path": manifest_path.relative_to(tmp_path).as_posix(),
                "producer_revision": "324ce6e6d4395ccfda1e59e5ae89de9389cdf225",
                "expected_scope_prims": ["/World/DryingBox_03"],
                "license": "CC-BY-NC-4.0",
                "attribution": ["ConvertAsset source-bound dynamic package"],
                "redistributable": False,
                "exclude_relative_paths": ["evidence"],
            }
        },
    )

    sources = resolve_scenario_source_bindings(bindings_path)

    source = sources["scientific_workbench_dryingbox_03_dynamic"]
    assert source.role == "scene_overlay"
    assert source.root_prim_path == "/World"
    assert source.exclude_relative_paths == ("evidence",)
    assert source.upstream_package is not None
    assert source.upstream_package.producer == "ConvertAsset"
    assert source.upstream_package.revision == (
        "324ce6e6d4395ccfda1e59e5ae89de9389cdf225"
    )
    assert source.upstream_package.metadata["scope_prims"] == [
        "/World/DryingBox_03"
    ]


def test_v02_convert_asset_rigid_object_binding_requires_task_ready_interaction(
    tmp_path: Path,
) -> None:
    source_usd = _write_source_scene(tmp_path)
    _, package_dir, manifest_path, _ = _write_source_bound_handoff(
        tmp_path / "handoff",
        source_usd=source_usd,
        with_interaction_contract=True,
    )
    bindings_path = _write_bindings(
        tmp_path / "bindings.yaml",
        {
            "qualified_vessel": {
                "resolver": "convert_asset_package",
                "usage": "rigid_object",
                "source_usd": source_usd.relative_to(tmp_path).as_posix(),
                "package_dir": package_dir.relative_to(tmp_path).as_posix(),
                "manifest_path": manifest_path.relative_to(tmp_path).as_posix(),
                "producer_revision": "324ce6e",
                "expected_scope_prims": ["/World/DryingBox_03"],
                "license": "CC-BY-NC-4.0",
                "redistributable": False,
            }
        },
        schema_version="scenario-source-bindings/v0.2",
    )

    source = resolve_scenario_source_bindings(bindings_path)["qualified_vessel"]

    assert source.role == "rigid_object"
    assert source.exclude_relative_paths == ()
    assert source.upstream_package is not None
    assert source.upstream_package.metadata["interaction_contract"][
        "asset_entry_prim"
    ] == "/World/DryingBox_03"


def test_v02_convert_asset_articulated_object_binding_preserves_device_contract(
    tmp_path: Path,
) -> None:
    source_usd, package_dir, manifest_path, _ = _write_articulated_handoff(
        tmp_path / "handoff"
    )
    bindings_path = _write_bindings(
        tmp_path / "bindings.yaml",
        {
            "qualified_centrifuge": {
                "resolver": "convert_asset_package",
                "usage": "articulated_object",
                "source_usd": source_usd.relative_to(tmp_path).as_posix(),
                "package_dir": package_dir.relative_to(tmp_path).as_posix(),
                "manifest_path": manifest_path.relative_to(tmp_path).as_posix(),
                "producer_revision": "convertasset-articulation-r1",
                "expected_scope_prims": ["/World/Centrifuge"],
                "license": "LicenseRef-Internal-Restricted",
                "redistributable": False,
            }
        },
        schema_version="scenario-source-bindings/v0.2",
    )

    source = resolve_scenario_source_bindings(bindings_path)["qualified_centrifuge"]

    assert source.role == "articulated_object"
    assert source.upstream_package is not None
    contract = source.upstream_package.metadata["articulation_contract"]
    assert contract["joints"]["start_button"]["part_prim"] == (
        "/World/Centrifuge/start_button"
    )


def test_v02_convert_asset_visual_static_binding_keeps_it_nonphysical(
    tmp_path: Path,
) -> None:
    source_usd, package_dir, manifest_path, _ = _write_visual_static_handoff(
        tmp_path / "handoff"
    )
    bindings_path = _write_bindings(
        tmp_path / "bindings.yaml",
        {
            "scene1_hard_environment": {
                "resolver": "convert_asset_package",
                "usage": "visual_static_environment",
                "source_usd": source_usd.relative_to(tmp_path).as_posix(),
                "package_dir": package_dir.relative_to(tmp_path).as_posix(),
                "manifest_path": manifest_path.relative_to(tmp_path).as_posix(),
                "producer_revision": "f81e953",
                "expected_scope_prims": ["/World/lab_015"],
                "license": "CC-BY-NC-4.0",
                "redistributable": False,
            }
        },
        schema_version="scenario-source-bindings/v0.2",
    )

    source = resolve_scenario_source_bindings(bindings_path)["scene1_hard_environment"]

    assert source.role == "environment"
    assert source.upstream_package is not None
    assert source.upstream_package.metadata["consumer_usage"] == (
        "visual_static_environment"
    )


def test_v01_convert_asset_binding_remains_scene_overlay_without_usage(
    tmp_path: Path,
) -> None:
    source_usd = _write_source_scene(tmp_path)
    _, package_dir, manifest_path, _ = _write_source_bound_handoff(
        tmp_path / "handoff",
        source_usd=source_usd,
    )
    bindings_path = _write_bindings(
        tmp_path / "bindings.yaml",
        {
            "legacy_overlay": {
                "resolver": "convert_asset_package",
                "source_usd": source_usd.relative_to(tmp_path).as_posix(),
                "package_dir": package_dir.relative_to(tmp_path).as_posix(),
                "manifest_path": manifest_path.relative_to(tmp_path).as_posix(),
                "producer_revision": "324ce6e",
                "expected_scope_prims": ["/World/DryingBox_03"],
                "license": "CC-BY-NC-4.0",
            }
        },
    )

    assert resolve_scenario_source_bindings(bindings_path)["legacy_overlay"].role == (
        "scene_overlay"
    )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            {"schema_version": "scenario-source-bindings/v9", "bindings": {}},
            "schema_version",
        ),
        (
            {
                "schema_version": "scenario-source-bindings/v0.1",
                "bindings": {
                    "asset": {
                        "resolver": "invented_converter",
                    }
                },
            },
            "resolver",
        ),
        (
            {
                "schema_version": "scenario-source-bindings/v0.1",
                "bindings": {
                    "asset": {
                        "resolver": "local_usd",
                        "source_usd": "asset.usd",
                        "role": "environment",
                        "source_uri": "example://asset",
                    }
                },
            },
            "license",
        ),
    ],
    ids=["schema-version", "resolver", "required-field"],
)
def test_source_binding_errors_name_the_invalid_contract_field(
    tmp_path: Path,
    payload: dict[str, object],
    message: str,
) -> None:
    path = tmp_path / "bindings.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(ScenarioSourceBindingError, match=message):
        resolve_scenario_source_bindings(path)


def test_source_bindings_reject_unknown_fields_instead_of_ignoring_typos(
    tmp_path: Path,
) -> None:
    source_usd = tmp_path / "asset.usd"
    source_usd.write_text("#usda 1.0\n", encoding="utf-8")
    path = _write_bindings(
        tmp_path / "bindings.yaml",
        {
            "asset": {
                "resolver": "local_usd",
                "source_usd": "asset.usd",
                "role": "environment",
                "license": "CC-BY-4.0",
                "source_uri": "example://asset",
                "licence": "typo-must-not-be-ignored",
            }
        },
    )

    with pytest.raises(ScenarioSourceBindingError, match="unexpected.*licence"):
        resolve_scenario_source_bindings(path)


def test_source_bindings_reject_duplicate_string_array_entries(
    tmp_path: Path,
) -> None:
    source_usd = tmp_path / "asset.usd"
    source_usd.write_text("#usda 1.0\n", encoding="utf-8")
    path = _write_bindings(
        tmp_path / "bindings.yaml",
        {
            "asset": {
                "resolver": "local_usd",
                "source_usd": "asset.usd",
                "role": "environment",
                "license": "CC-BY-4.0",
                "source_uri": "example://asset",
                "attribution": ["same", "same"],
            }
        },
    )

    with pytest.raises(ScenarioSourceBindingError, match="attribution.*unique"):
        resolve_scenario_source_bindings(path)
