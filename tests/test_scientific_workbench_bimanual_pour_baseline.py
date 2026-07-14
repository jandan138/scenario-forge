from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = (
    REPO_ROOT
    / "docs/records/evidence/2026-07-14-scientific-workbench-bimanual-pour-oracle-baseline"
    / "package_baseline.yaml"
)


def test_exact_oracle_baseline_is_hash_bound_and_reproducible() -> None:
    baseline = yaml.safe_load(BASELINE_PATH.read_text(encoding="utf-8"))

    assert baseline["schema_version"] == "scenario-forge-package-baseline/v0.1"
    assert baseline["status"] == "frozen_for_oracle_preflight"
    assert baseline["package"]["package_id"] == "scientific_workbench_bimanual_pour"
    assert baseline["package"]["file_count"] == 198
    assert baseline["package"]["file_content_bytes"] == 120_066_353
    assert baseline["package"]["sha256sum_stream_sha256"] == (
        "59d6024db27db865be103fd2ddeb7b9a66672238b0f628149d5a065d77cdebe4"
    )
    assert baseline["package"]["digest_algorithm"] == (
        "sha256(sorted sha256sum records for ./ relative regular-file paths)"
    )

    sources = baseline["sources"]
    assert sources["scenario_forge_revision"] == (
        "d481713b5a507d4e4948f359fbdb2271174996d9"
    )
    assert sources["convert_asset_revision"] == (
        "324ce6e6d4395ccfda1e59e5ae89de9389cdf225"
    )
    assert sources["base_usd_sha256"] == (
        "b3861b5a17945abe401062a04125969c3a63b0f8a0a5ce0026a461dbdfc935f2"
    )
    assert sources["convert_asset_manifest_sha256"] == (
        "be988683935c2e107335fff3cbe4b562aee186a0c076d7445a2b907f07412dc9"
    )

    frozen = baseline["frozen_artifacts"]
    assert frozen["asset_lock.yaml"] == (
        "1a0ba9a19fbd4e42e2bed7d6589ee80bbcdbe6fb54061b50b102d20caeedd955"
    )
    assert frozen["robot"] == (
        "a2ff8964c558cd9b4a08b2fb39d9563285bbe83d251f3edacb62de41e65f7e7c"
    )
    assert frozen["genmanip_task_config"] == (
        "6d6a75836a49506a38da9435761edba488870b9e38742fcf8dc797dcce1f1e97"
    )
    assert frozen["genmanip_scene"] == (
        "19a24e880460e80a2d7264d64503cb60f20c9c78ef453b469a6dff5bf4da0b30"
    )

    claims = baseline["claim_boundary"]
    assert claims["runtime_reset"] == "not_established_by_this_record"
    assert claims["five_stage_oracle"] == "blocked_by_preflight"
    assert claims["fluid_transfer"] == "out_of_scope_kinematic_proxy"
    blockers = baseline["oracle_preflight"]["blocking_findings"]
    assert {item["id"] for item in blockers} == {
        "runtime_body_identity_mismatch",
        "opening_metric_mismatch",
    }
