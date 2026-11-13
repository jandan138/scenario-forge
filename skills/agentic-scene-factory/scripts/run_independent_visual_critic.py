#!/usr/bin/env python3
"""Cross-host Independent Blind-Review Visual Critic harness.

Ensures AntigravitySwarm, Claude Code (`.claude/agents/visual-critic.md`),
Codex CLI (`codex exec`), and OpenCode (`opencode run`) share one deterministic
blind-review gate contract:
  - ``author_agent`` and ``critic_agent`` are non-empty and ``author_agent != critic_agent``
  - ``verdict == "PASS"``
  - Every scored dimension / scene / patch meets ``>= --min-score`` (default ``8.0``)
  - Optional SHA-256 verification of bound USD / PNG evidence artifacts
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[3]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _normalize_hex(digest: str) -> str:
    return digest.strip().lower().removeprefix("sha256:")


def validate_visual_critique_payload(
    payload: Mapping[str, Any],
    *,
    min_score: float = 8.0,
    expected_author: str | None = None,
    verify_hashes: bool = False,
    base_dir: Path | None = None,
) -> dict[str, Any]:
    author = str(payload.get("author_agent", "")).strip()
    critic = str(payload.get("critic_agent", "")).strip()
    if not author or not critic:
        raise ValueError("visual_critique_report requires non-empty 'author_agent' and 'critic_agent'")
    if author == critic:
        raise ValueError(f"blind-review isolation violated: author_agent == critic_agent ({author!r})")
    if expected_author is not None and author != expected_author:
        raise ValueError(f"author_agent {author!r} does not match expected {expected_author!r}")

    verdict = str(payload.get("verdict", "")).strip().upper()
    if verdict and verdict != "PASS":
        raise ValueError(f"visual critique verdict is {verdict!r}, expected 'PASS'")

    scores_checked = 0
    min_observed = float("inf")

    dims = payload.get("dimensions") or payload.get("scores")
    if isinstance(dims, Mapping) and dims:
        for name, raw_val in dims.items():
            val = float(raw_val)
            scores_checked += 1
            min_observed = min(min_observed, val)
            if val < min_score:
                raise ValueError(f"dimension {name!r}={val:.2f} is below threshold {min_score:.2f}")

    scenes = payload.get("scenes")
    if isinstance(scenes, list) and scenes:
        for scene in scenes:
            sid = scene.get("scenario_id", "scene")
            if str(scene.get("verdict", "PASS")).strip().upper() != "PASS":
                raise ValueError(f"scene {sid!r} verdict is not PASS")
            s_dims = scene.get("scores") or scene.get("dimensions") or {}
            for name, raw_val in s_dims.items():
                val = float(raw_val)
                scores_checked += 1
                min_observed = min(min_observed, val)
                if val < min_score:
                    raise ValueError(f"scene {sid!r} dimension {name!r}={val:.2f} < {min_score:.2f}")

    patches = payload.get("patches")
    if isinstance(patches, list) and patches:
        for patch in patches:
            pid = patch.get("surface_id", "patch")
            val = float(patch.get("patch_score", patch.get("score", 0.0)))
            scores_checked += 1
            min_observed = min(min_observed, val)
            if val < min_score:
                raise ValueError(f"patch {pid!r} score={val:.2f} < {min_score:.2f}")

    if scores_checked == 0:
        raise ValueError("visual_critique_report contains no scored dimensions, scenes, or patches")

    if verify_hashes:
        roots = [r for r in (base_dir, REPO_ROOT) if r is not None]

        def _check_ref(ref: Mapping[str, Any]) -> None:
            raw_p = str(ref["path"])
            exp = _normalize_hex(str(ref["sha256"]))
            p = Path(raw_p)
            cand = p if p.is_absolute() else next(((r / p).resolve() for r in roots if (r / p).is_file()), p)
            if not cand.is_file():
                raise ValueError(f"referenced evidence file missing: {raw_p}")
            if _sha256(cand) != exp:
                raise ValueError(f"SHA-256 mismatch on referenced evidence: {raw_p}")

        if isinstance(payload.get("source_usd"), Mapping):
            _check_ref(payload["source_usd"])
        for item in payload.get("reviewed_renders", []) or []:
            if isinstance(item, Mapping) and "path" in item and "sha256" in item:
                _check_ref(item)

    return {
        "status": "pass",
        "author_agent": author,
        "critic_agent": critic,
        "scores_checked": scores_checked,
        "min_observed_score": round(min_observed, 4),
        "threshold": min_score,
    }


def _invoke_external_driver(
    *,
    driver: str,
    report_path: Path,
    prompt: str,
    images: list[Path],
) -> None:
    if driver == "codex_cli":
        binary = shutil.which("codex")
        if binary is None:
            raise RuntimeError("codex CLI binary not found on PATH for --driver codex_cli")
        cmd = [binary, "exec", "--skip-git-repo-check"]
        for img in images:
            cmd.extend(["--image", str(img.resolve())])
        cmd.append(f"{prompt}\nWrite the final JSON report to: {report_path.resolve()}")
    elif driver == "opencode_cli":
        binary = shutil.which("opencode")
        if binary is None:
            raise RuntimeError("opencode CLI binary not found on PATH for --driver opencode_cli")
        img_list = ", ".join(str(p.resolve()) for p in images)
        cmd = [
            binary,
            "run",
            f"{prompt}\nInspect images: [{img_list}]. Write the final JSON report to: {report_path.resolve()}",
        ]
    else:
        raise ValueError(f"unsupported driver: {driver}")

    proc = subprocess.run(cmd, check=False, text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"external critic driver {driver} exited {proc.returncode}: {proc.stderr.strip()}"
        )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True, help="Path to visual_critique_report.json.")
    parser.add_argument(
        "--driver",
        choices=("validate_only", "codex_cli", "opencode_cli"),
        default="validate_only",
        help="Execution driver: validate an existing report or spawn an isolated CLI critic session.",
    )
    parser.add_argument("--min-score", "--threshold", dest="min_score", type=float, default=8.0)
    parser.add_argument("--expected-author", default=None)
    parser.add_argument("--verify-hashes", action="store_true")
    parser.add_argument("--prompt", default="Perform an independent blind visual critique and output JSON.")
    parser.add_argument("--prompt-file", type=Path, default=None)
    parser.add_argument("--images", nargs="*", type=Path, default=[])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report_path = args.report.resolve()

    if args.driver in {"codex_cli", "opencode_cli"}:
        prompt_text = (
            args.prompt_file.resolve().read_text(encoding="utf-8")
            if args.prompt_file is not None
            else args.prompt
        )
        _invoke_external_driver(
            driver=args.driver,
            report_path=report_path,
            prompt=prompt_text,
            images=list(args.images),
        )

    if not report_path.is_file():
        raise FileNotFoundError(f"visual critique report not found: {report_path}")
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    summary = validate_visual_critique_payload(
        payload,
        min_score=float(args.min_score),
        expected_author=args.expected_author,
        verify_hashes=bool(args.verify_hashes),
        base_dir=report_path.parent,
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
