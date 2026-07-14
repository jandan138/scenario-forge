from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import stat
import sys
import textwrap
import types

import pytest
import yaml

from scenario_forge.adapters.ebench.genmanip import export_genmanip_collected_package
from tests.test_ebench_genmanip_export import _build_package


REPO_ROOT = Path(__file__).resolve().parents[1]
PURE_ORCHESTRATION = (
    REPO_ROOT / "src/scenario_forge/adapters/ebench/preview.py"
)
ISAAC_RENDERER = (
    REPO_ROOT / "scripts/ebench/render_genmanip_initial_preview.py"
)
EVIDENCE_DIR = Path("evidence/initial_scene")
GATE_PATH = EVIDENCE_DIR / "visual_ready_gate.yaml"


def test_preview_orchestration_uses_argv_and_supports_paths_with_spaces(
    tmp_path: Path,
) -> None:
    collected_root = _build_collected_package(tmp_path / "package workspace")
    request = _load_yaml(collected_root / "evidence/render_request.yaml")
    preset = collected_root / "fake preset evidence"
    _write_passing_preview_evidence(collected_root, request).rename(preset)

    runtime_dir = tmp_path / "fake isaac runtime"
    isaac_python = _write_python_forwarder(runtime_dir / "fake isaac python")
    renderer_script = _write_fake_renderer(
        tmp_path / "renderer scripts" / "fake preview renderer.py",
        mode="success",
    )
    genmanip_root = tmp_path / "GenManip checkout with spaces"
    genmanip_root.mkdir(parents=True)

    _run_preview(
        collected_root,
        isaac_python=isaac_python,
        renderer_script=renderer_script,
        genmanip_root=genmanip_root,
        timeout_seconds=5.0,
    )

    argv = json.loads((collected_root / "fake_renderer_argv.json").read_text())
    assert argv == [
        "--collected-root",
        str(collected_root),
        "--genmanip-root",
        str(genmanip_root),
        "--request",
        "evidence/render_request.yaml",
    ]
    assert _load_yaml(collected_root / GATE_PATH)["status"] == "passed"
    assert (collected_root / EVIDENCE_DIR / "workspace_closeup.png").is_file()
    assert (collected_root / EVIDENCE_DIR / "scene_overview.png").is_file()


def test_preview_orchestration_resolves_package_before_changing_runtime_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    collected_root = _build_collected_package(Path("relative package"))
    request = _load_yaml(collected_root / "evidence/render_request.yaml")
    preset = collected_root / "fake preset evidence"
    _write_passing_preview_evidence(collected_root, request).rename(preset)

    isaac_python = _write_python_forwarder(tmp_path / "runtime" / "isaac python")
    renderer_script = _write_fake_renderer(
        tmp_path / "renderer" / "fake preview renderer.py",
        mode="success",
    )
    genmanip_root = tmp_path / "GenManip"
    genmanip_root.mkdir()

    _run_preview(
        collected_root,
        isaac_python=isaac_python,
        renderer_script=renderer_script,
        genmanip_root=genmanip_root,
        timeout_seconds=5.0,
    )

    argv = json.loads((collected_root / "fake_renderer_argv.json").read_text())
    assert argv[1] == str(collected_root.resolve())
    assert (collected_root / GATE_PATH).is_file()


def test_preview_orchestration_nonzero_invalidates_old_pass_gate(
    tmp_path: Path,
) -> None:
    collected_root = _build_collected_package(tmp_path / "package")
    _write_old_passing_gate(collected_root)
    isaac_python = _write_python_forwarder(tmp_path / "runtime" / "isaac-python")
    renderer_script = _write_fake_renderer(
        tmp_path / "renderer" / "nonzero.py",
        mode="nonzero",
    )
    genmanip_root = tmp_path / "GenManip"
    genmanip_root.mkdir()

    with pytest.raises(
        _preview_error_type(),
        match=r"(?i)(exit|status|failed).*(23)|23.*(exit|status|failed)",
    ):
        _run_preview(
            collected_root,
            isaac_python=isaac_python,
            renderer_script=renderer_script,
            genmanip_root=genmanip_root,
            timeout_seconds=5.0,
        )

    assert not (collected_root / GATE_PATH).exists()


def test_preview_orchestration_rejects_blocking_signal_from_captured_stderr(
    tmp_path: Path,
) -> None:
    collected_root = _build_collected_package(tmp_path / "package")
    request = _load_yaml(collected_root / "evidence/render_request.yaml")
    preset = collected_root / "fake preset evidence"
    _write_passing_preview_evidence(collected_root, request).rename(preset)
    isaac_python = _write_python_forwarder(tmp_path / "runtime" / "isaac-python")
    renderer_script = _write_fake_renderer(
        tmp_path / "renderer" / "blocking.py",
        mode="blocking_log",
    )
    genmanip_root = tmp_path / "GenManip"
    genmanip_root.mkdir()

    with pytest.raises(_preview_error_type(), match="blocking material signal"):
        _run_preview(
            collected_root,
            isaac_python=isaac_python,
            renderer_script=renderer_script,
            genmanip_root=genmanip_root,
            timeout_seconds=5.0,
        )

    manifest = json.loads(
        (collected_root / EVIDENCE_DIR / "render_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["runtime_log_scan"]["status"] == "failed"
    assert manifest["runtime_log_scan"]["blocking_signal_count"] == 1
    assert not (collected_root / GATE_PATH).exists()


def test_preview_orchestration_timeout_invalidates_old_pass_gate(
    tmp_path: Path,
) -> None:
    collected_root = _build_collected_package(tmp_path / "package")
    _write_old_passing_gate(collected_root)
    isaac_python = _write_python_forwarder(tmp_path / "runtime" / "isaac-python")
    renderer_script = _write_fake_renderer(
        tmp_path / "renderer" / "timeout.py",
        mode="timeout",
    )
    genmanip_root = tmp_path / "GenManip"
    genmanip_root.mkdir()

    with pytest.raises(_preview_error_type(), match=r"(?i)timed?\s*out|timeout"):
        _run_preview(
            collected_root,
            isaac_python=isaac_python,
            renderer_script=renderer_script,
            genmanip_root=genmanip_root,
            timeout_seconds=0.05,
        )

    assert not (collected_root / GATE_PATH).exists()


def test_pure_preview_orchestration_never_imports_simulator_sdks() -> None:
    assert PURE_ORCHESTRATION.is_file(), "the pure preview orchestration module is missing"
    tree = ast.parse(PURE_ORCHESTRATION.read_text(encoding="utf-8"))

    imported_modules = _all_imported_modules(tree)
    forbidden = {
        module
        for module in imported_modules
        if module == "isaacsim"
        or module.startswith("isaacsim.")
        or module == "omni"
        or module.startswith("omni.")
        or module == "genmanip"
        or module.startswith("genmanip.")
    }
    assert forbidden == set()

    for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
        call_name = _call_name(call.func)
        assert call_name not in {"os.system", "os.popen"}
        if call_name.startswith("subprocess."):
            shell_keywords = [item for item in call.keywords if item.arg == "shell"]
            assert not shell_keywords or all(
                isinstance(item.value, ast.Constant) and item.value.value is False
                for item in shell_keywords
            )


def test_isaac_renderer_has_deferred_sdk_imports_and_only_resets_then_renders() -> None:
    assert ISAAC_RENDERER.is_file(), "the one-shot Isaac/GenManip renderer is missing"
    source = ISAAC_RENDERER.read_text(encoding="utf-8")
    tree = ast.parse(source)

    module_imports = _module_execution_imports(tree)
    forbidden_top_level = {
        module
        for module in module_imports
        if module == "isaacsim"
        or module.startswith("isaacsim.")
        or module == "omni"
        or module.startswith("omni.")
        or module == "genmanip"
        or module.startswith("genmanip.")
    }
    assert forbidden_top_level == set()

    string_literals = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert "workspace_closeup" in string_literals
    assert "scene_overview" in string_literals

    calls = [_call_name(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call)]
    assert "recovery_scene" in calls
    assert all(not name.endswith("recovery_scene_render") for name in calls)
    assert "recovery_scene_render" not in source
    assert all("metric" not in name.lower() for name in calls)
    assert all("policy" not in name.lower() for name in calls)
    assert all("parse_action" not in name.lower() for name in calls)
    assert "visible_runtime_ids" not in source
    assert "present_runtime_ids" in source
    assert "material_runtime_preflight" not in source

    for loop in (
        node for node in ast.walk(tree) if isinstance(node, (ast.For, ast.AsyncFor))
    ):
        target_text = ast.unparse(loop.target).lower()
        iterator_text = ast.unparse(loop.iter).lower()
        assert "action" not in target_text
        assert "action" not in iterator_text
    for loop in (node for node in ast.walk(tree) if isinstance(node, ast.While)):
        assert "action" not in ast.unparse(loop.test).lower()


def test_isaac_renderer_disables_fast_shutdown_so_python_failures_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = importlib.util.spec_from_file_location(
        "scenario_forge_preview_renderer_shutdown", ISAAC_RENDERER
    )
    assert spec is not None and spec.loader is not None
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)

    launch_config: dict[str, object] = {}
    closed = False

    class FakeSimulationApp:
        def __init__(self, config: dict[str, object]) -> None:
            launch_config.update(config)

        def close(self) -> None:
            nonlocal closed
            closed = True

    fake_isaacsim = types.ModuleType("isaacsim")
    fake_isaacsim.SimulationApp = FakeSimulationApp  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "isaacsim", fake_isaacsim)
    monkeypatch.setitem(sys.modules, "genmanip", None)
    monkeypatch.setattr(sys, "path", list(sys.path))
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()

    with pytest.raises(ModuleNotFoundError, match="genmanip"):
        renderer._render_initial_scene(
            collected_root=tmp_path,
            genmanip_root=tmp_path,
            request={},
            request_sha256="0" * 64,
            staging_dir=staging_dir,
            evidence_dir=tmp_path / "evidence",
        )

    assert launch_config["fast_shutdown"] is False
    assert closed is True
    assert "render_status=failed" in (staging_dir / "runtime.log").read_text(encoding="utf-8")


def test_isaac_renderer_resolves_lift2_end_effectors_as_camera_anchors() -> None:
    spec = importlib.util.spec_from_file_location("scenario_forge_preview_renderer", ISAAC_RENDERER)
    assert spec is not None and spec.loader is not None
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)

    class FakePrim:
        def __init__(self, path: str) -> None:
            self.path = path

        def IsValid(self) -> bool:
            return True

        def IsActive(self) -> bool:
            return True

    class FakeStage:
        def __init__(self) -> None:
            self.requested: list[str] = []

        def GetPrimAtPath(self, path: str) -> FakePrim:
            self.requested.append(path)
            return FakePrim(path)

    class FakeScene:
        uuid = "task_scene"
        object_list: dict[str, object] = {}

    stage = FakeStage()
    prims = renderer._runtime_prims(stage, FakeScene(), "lift2_end_effectors")

    assert [prim.path for prim in prims] == [
        "/World/task_scene/lift2/lift2/lift2/fl/link6",
        "/World/task_scene/lift2/lift2/lift2/fr/link6",
    ]
    assert stage.requested == [prim.path for prim in prims]


def test_isaac_renderer_validates_source_bundle_tree_digest(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(
        "scenario_forge_preview_renderer_tree", ISAAC_RENDERER
    )
    assert spec is not None and spec.loader is not None
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)
    collected_root = _build_collected_package(tmp_path / "package")
    request = _load_yaml(collected_root / "evidence/render_request.yaml")

    renderer._validate_request(collected_root, request)

    source_bundle = collected_root / request["inputs"]["source_bundle"]["path"]
    source_usd = next(source_bundle.rglob("scene.usda"))
    source_usd.write_text(
        source_usd.read_text(encoding="utf-8") + "\n# changed\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="sha256"):
        renderer._validate_request(collected_root, request)


def _build_collected_package(workspace: Path) -> Path:
    workspace.mkdir(parents=True)
    package_root = _build_package(workspace)
    return export_genmanip_collected_package(package_root).output_dir


def _write_old_passing_gate(collected_root: Path) -> None:
    request = _load_yaml(collected_root / "evidence/render_request.yaml")
    evidence_dir = _write_passing_preview_evidence(collected_root, request)
    gate = {
        "schema_version": "scenario-forge-genmanip-preview-gate/v0.1",
        "status": "passed",
        "package_id": request["package_id"],
        "input_digest": request["input_digest"],
        "views": {"workspace_closeup": "passed", "scene_overview": "passed"},
        "next_stage": "clean_room_visual_review",
        "claim_boundary": "Initial visual evidence only; not task success.",
    }
    (evidence_dir / "visual_ready_gate.yaml").write_text(
        yaml.safe_dump(gate, sort_keys=True),
        encoding="utf-8",
    )


def _write_python_forwarder(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        textwrap.dedent(
            f"""\
            #!{sys.executable}
            import os
            import sys

            os.execv({sys.executable!r}, [{sys.executable!r}, *sys.argv[1:]])
            """
        ),
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _write_fake_renderer(path: Path, *, mode: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        textwrap.dedent(
            f"""\
            import argparse
            import json
            from pathlib import Path
            import shutil
            import sys
            import time

            parser = argparse.ArgumentParser()
            parser.add_argument("--collected-root", type=Path, required=True)
            parser.add_argument("--genmanip-root", type=Path, required=True)
            parser.add_argument("--request", required=True)
            args = parser.parse_args()
            (args.collected_root / "fake_renderer_argv.json").write_text(
                json.dumps(sys.argv[1:]), encoding="utf-8"
            )

            mode = {mode!r}
            if mode == "nonzero":
                raise SystemExit(23)
            if mode == "timeout":
                time.sleep(10)
                raise SystemExit(0)
            if mode == "blocking_log":
                print("Failed to create MDL shade node", file=sys.stderr)
            preset = args.collected_root / "fake preset evidence"
            output = args.collected_root / "evidence" / "initial_scene"
            if output.exists():
                shutil.rmtree(output)
            shutil.copytree(preset, output)
            """
        ),
        encoding="utf-8",
    )
    return path


def _run_preview(
    collected_root: Path,
    *,
    isaac_python: Path,
    renderer_script: Path,
    genmanip_root: Path,
    timeout_seconds: float,
) -> object:
    from scenario_forge.adapters.ebench.preview import run_genmanip_initial_preview

    return run_genmanip_initial_preview(
        collected_root,
        isaac_python,
        renderer_script,
        genmanip_root,
        timeout_seconds=timeout_seconds,
    )


def _preview_error_type() -> type[Exception]:
    from scenario_forge.adapters.ebench.preview import GenManipPreviewError

    return GenManipPreviewError


def _load_yaml(path: Path) -> dict[str, object]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _write_passing_preview_evidence(
    collected_root: Path,
    request: dict[str, object],
) -> Path:
    # Imported lazily so this orchestration test module can still collect during
    # the red phase before the preview API exists.
    from tests.test_ebench_genmanip_preview import _write_passing_evidence

    return _write_passing_evidence(collected_root, request)


def _all_imported_modules(tree: ast.AST) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


def _module_execution_imports(tree: ast.Module) -> set[str]:
    modules: set[str] = set()

    def visit(node: ast.AST) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            return
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
            return
        if isinstance(node, ast.ImportFrom):
            if node.module is not None:
                modules.add(node.module)
            return
        for child in ast.iter_child_nodes(node):
            visit(child)

    for statement in tree.body:
        visit(statement)
    return modules


def _call_name(function: ast.expr) -> str:
    if isinstance(function, ast.Name):
        return function.id
    if isinstance(function, ast.Attribute):
        prefix = _call_name(function.value)
        return f"{prefix}.{function.attr}" if prefix else function.attr
    return ""
