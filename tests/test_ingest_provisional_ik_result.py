from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts/ingest_provisional_ik_result.py"


def _script_module():
    spec = importlib.util.spec_from_file_location("ingest_provisional_ik_result", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ingest_provisional_ik_result_validates_the_package_local_request(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    module = _script_module()
    package = tmp_path / "package"
    request = package / "adapters/ebench/genmanip/provisional_ik_preflight/request.yaml"
    result = tmp_path / "external-result.yaml"
    request.parent.mkdir(parents=True)
    request.write_text("request: true\n", encoding="utf-8")
    result.write_text("result: true\n", encoding="utf-8")
    expected_evidence = package / "evidence/provisional_ik_preflight.yaml"

    received: dict[str, Path] = {}

    def validate(request_path: Path, result_path: Path) -> Path:
        received["request"] = request_path
        received["result"] = result_path
        return expected_evidence

    monkeypatch.setattr(module, "validate_provisional_ik_result", validate)

    assert module.main(["--package", str(package), "--result", str(result)]) == 0
    assert received == {"request": request, "result": result}
    assert str(expected_evidence) in capsys.readouterr().out
