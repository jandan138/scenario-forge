from __future__ import annotations

from pathlib import Path

import yaml

from scenario_forge.cli import main
from scenario_forge.package import validate_package
from tests.test_convert_asset_adapter import _write_source_bound_handoff
from tests.test_scenario_package_compiler import _write_source_scene
from tests.test_scenario_spec import _scenario_mapping


def _write_yaml(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _local_binding_payload(source_usd: Path, binding_root: Path) -> dict[str, object]:
    return {
        "schema_version": "scenario-source-bindings/v0.1",
        "bindings": {
            "scientific_workbench_environment": {
                "resolver": "local_usd",
                "source_usd": source_usd.relative_to(binding_root).as_posix(),
                "role": "environment",
                "license": "CC-BY-NC-4.0",
                "source_uri": f"file:{source_usd}",
                "attribution": ["LabUtopia fixture"],
                "redistributable": False,
            }
        },
    }


def _file_tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(item for item in root.rglob("*") if item.is_file())
    }


def test_package_compile_cli_builds_portable_package_and_optional_genmanip_export(
    tmp_path: Path,
    capsys,
) -> None:
    input_root = tmp_path / "inputs"
    source_usd = _write_source_scene(input_root)
    scenario = _scenario_mapping()
    spec_path = _write_yaml(input_root / "scenario.yaml", scenario)
    bindings_path = _write_yaml(
        input_root / "source_bindings.yaml",
        _local_binding_payload(source_usd, input_root),
    )
    package_root = tmp_path / "package"

    exit_code = main(
        [
            "package",
            "compile",
            "--spec",
            str(spec_path),
            "--source-bindings",
            str(bindings_path),
            "--out",
            str(package_root),
            "--export-genmanip",
        ]
    )

    assert exit_code == 0
    assert validate_package(package_root, require_asset_lock=True).ok
    assert yaml.safe_load(
        (package_root / "scenario.yaml").read_text(encoding="utf-8")
    ) == scenario
    collected = package_root / "adapters/ebench/genmanip"
    assert (collected / "tasks/config.yaml").is_file()
    assert (
        collected
        / "tasks/scenario_forge/scientific_workbench_bimanual_pour/000/episode_metadata.json"
    ).is_file()

    local_root = str(tmp_path)
    for relative_path in (
        "scenario.yaml",
        "assets/asset_manifest.yaml",
        "generation/plan.yaml",
        "provenance/provenance.yaml",
    ):
        assert local_root not in (package_root / relative_path).read_text(encoding="utf-8")

    output = capsys.readouterr().out
    assert f"Portable package: {package_root}" in output
    assert f"GenManip collected package: {collected}" in output


def test_package_compile_cli_validates_all_bindings_before_replacing_output(
    tmp_path: Path,
    capsys,
) -> None:
    input_root = tmp_path / "inputs"
    source_usd = _write_source_scene(input_root)
    _, convert_package, convert_manifest, _ = _write_source_bound_handoff(
        input_root / "handoff",
        source_usd=source_usd,
    )
    scenario = _scenario_mapping()
    scenario["schema_version"] = "scenario-spec/v0.2"
    scene = dict(scenario["scene"])  # type: ignore[arg-type]
    scene["overlay_asset_ids"] = ["scientific_workbench_dryingbox_03_dynamic"]
    scenario["scene"] = scene
    spec_path = _write_yaml(input_root / "scenario.yaml", scenario)
    bindings = _local_binding_payload(source_usd, input_root)
    raw_bindings = bindings["bindings"]
    assert isinstance(raw_bindings, dict)
    raw_bindings["scientific_workbench_dryingbox_03_dynamic"] = {
        "resolver": "convert_asset_package",
        "source_usd": source_usd.relative_to(input_root).as_posix(),
        "package_dir": convert_package.relative_to(input_root).as_posix(),
        "manifest_path": convert_manifest.relative_to(input_root).as_posix(),
        "producer_revision": "324ce6e6d4395ccfda1e59e5ae89de9389cdf225",
        "expected_scope_prims": ["/World/DryingBox_03"],
        "license": "CC-BY-NC-4.0",
        "redistributable": False,
        "exclude_relative_paths": ["evidence"],
    }
    bindings_path = _write_yaml(input_root / "source_bindings.yaml", bindings)
    source_usd.write_text(
        source_usd.read_text(encoding="utf-8") + "\n# changed after handoff\n",
        encoding="utf-8",
    )
    package_root = tmp_path / "package"
    package_root.mkdir()
    marker = package_root / "keep.txt"
    marker.write_text("existing output", encoding="utf-8")

    exit_code = main(
        [
            "package",
            "compile",
            "--spec",
            str(spec_path),
            "--source-bindings",
            str(bindings_path),
            "--out",
            str(package_root),
        ]
    )

    assert exit_code == 1
    assert marker.read_text(encoding="utf-8") == "existing output"
    assert "source SHA-256" in capsys.readouterr().out


def test_package_compile_cli_preserves_existing_output_on_late_compile_failure(
    tmp_path: Path,
    capsys,
) -> None:
    input_root = tmp_path / "inputs"
    source_usd = _write_source_scene(input_root)
    scenario = _scenario_mapping()
    scene = dict(scenario["scene"])  # type: ignore[arg-type]
    scene["root_prim_path"] = "World"
    scenario["scene"] = scene
    spec_path = _write_yaml(input_root / "scenario.yaml", scenario)
    bindings_path = _write_yaml(
        input_root / "source_bindings.yaml",
        _local_binding_payload(source_usd, input_root),
    )
    package_root = tmp_path / "package"
    package_root.mkdir()
    marker = package_root / "keep.txt"
    marker.write_text("existing output", encoding="utf-8")

    exit_code = main(
        [
            "package",
            "compile",
            "--spec",
            str(spec_path),
            "--source-bindings",
            str(bindings_path),
            "--out",
            str(package_root),
        ]
    )

    assert exit_code == 1
    assert marker.read_text(encoding="utf-8") == "existing output"
    assert "absolute USD prim path" in capsys.readouterr().out
    assert not list(tmp_path.glob(".package.staging-*"))


def test_package_compile_cli_preserves_existing_output_on_adapter_export_failure(
    tmp_path: Path,
    capsys,
) -> None:
    input_root = tmp_path / "inputs"
    source_usd = _write_source_scene(input_root)
    scenario = _scenario_mapping()
    robot = dict(scenario["robot"])  # type: ignore[arg-type]
    robot["profile_ref"] = "manip/lift2/unsupported"
    scenario["robot"] = robot
    spec_path = _write_yaml(input_root / "scenario.yaml", scenario)
    bindings_path = _write_yaml(
        input_root / "source_bindings.yaml",
        _local_binding_payload(source_usd, input_root),
    )
    package_root = tmp_path / "package"
    package_root.mkdir()
    marker = package_root / "keep.txt"
    marker.write_text("existing output", encoding="utf-8")

    exit_code = main(
        [
            "package",
            "compile",
            "--spec",
            str(spec_path),
            "--source-bindings",
            str(bindings_path),
            "--out",
            str(package_root),
            "--export-genmanip",
        ]
    )

    assert exit_code == 1
    assert marker.read_text(encoding="utf-8") == "existing output"
    assert "GenManip collected-package export supports" in capsys.readouterr().out
    assert not list(tmp_path.glob(".package.staging-*"))


def test_package_compile_cli_output_is_independent_of_output_directory_basename(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "inputs"
    source_usd = _write_source_scene(input_root)
    spec_path = _write_yaml(input_root / "scenario.yaml", _scenario_mapping())
    bindings_path = _write_yaml(
        input_root / "source_bindings.yaml",
        _local_binding_payload(source_usd, input_root),
    )
    first = tmp_path / "first-build-name"
    second = tmp_path / "unrelated-second-name"

    for output in (first, second):
        exit_code = main(
            [
                "package",
                "compile",
                "--spec",
                str(spec_path),
                "--source-bindings",
                str(bindings_path),
                "--out",
                str(output),
                "--export-genmanip",
            ]
        )
        assert exit_code == 0

    assert _file_tree(first) == _file_tree(second)
    lock = yaml.safe_load((first / "locks/asset_lock.yaml").read_text(encoding="utf-8"))
    assert lock["lock_id"] == "scientific_workbench_bimanual_pour_asset_lock"
