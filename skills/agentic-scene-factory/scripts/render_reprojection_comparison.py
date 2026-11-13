#!/usr/bin/env python3
"""Composite a [real_photo | virtual_render | 50%_edge_overlay] reprojection comparison board."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from scenario_forge.adapters.texture_twin_ledger import (  # noqa: E402
    compose_reprojection_comparison_board,
    sha256_file,
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--real-photo", "--source-image", dest="real_photo", type=Path, required=True)
    parser.add_argument("--virtual-render", "--render-image", dest="virtual_render", type=Path, required=True)
    parser.add_argument("--out-image", "--out", dest="out_image", type=Path, required=True)
    parser.add_argument("--out-metrics", type=Path, default=None)
    parser.add_argument("--panel-width", type=int, default=960)
    parser.add_argument("--alpha", type=float, default=0.5)
    parser.add_argument("--critique-report", type=Path, default=None)
    parser.add_argument("--min-score", type=float, default=8.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    real_path = args.real_photo.resolve()
    virt_path = args.virtual_render.resolve()
    out_path = args.out_image.resolve()

    real_img = Image.open(real_path).convert("RGB")
    virt_img = Image.open(virt_path).convert("RGB")
    pw = int(args.panel_width)
    ph = max(64, int(round(pw * virt_img.height / max(1, virt_img.width))))

    board, metrics = compose_reprojection_comparison_board(
        real_img,
        virt_img,
        target_size=(pw, ph),
        alpha=float(args.alpha),
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    board.save(out_path, format="PNG")

    payload = {
        "schema_version": "scenario-forge-reprojection-comparison/v1.0",
        "real_photo": {"path": str(real_path), "sha256": sha256_file(real_path)},
        "virtual_render": {"path": str(virt_path), "sha256": sha256_file(virt_path)},
        "comparison_board": {"path": str(out_path), "sha256": sha256_file(out_path)},
        "metrics": metrics,
    }

    if args.critique_report is not None:
        critique = json.loads(args.critique_report.resolve().read_text(encoding="utf-8"))
        author = str(critique.get("author_agent", "")).strip()
        critic = str(critique.get("critic_agent", "")).strip()
        if not author or not critic or author == critic:
            raise ValueError("reprojection critique requires independent author_agent != critic_agent")
        if str(critique.get("verdict", "")).strip().upper() != "PASS":
            raise ValueError("reprojection critique verdict is not PASS")
        dims = critique.get("dimensions") or critique.get("scores") or {}
        if not isinstance(dims, dict) or not dims:
            raise ValueError("reprojection critique missing dimensions/scores mapping")
        low = {k: float(v) for k, v in dims.items() if float(v) < float(args.min_score)}
        if low:
            raise ValueError(f"reprojection critique dimensions below {args.min_score}: {low}")
        payload["critique_validation"] = "pass"

    metrics_path = (
        args.out_metrics.resolve()
        if args.out_metrics is not None
        else out_path.with_name(f"{out_path.stem}_metrics.json")
    )
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"reprojection comparison board saved: {out_path} (metrics: {metrics_path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
