#!/usr/bin/env python3
"""Verify 1:1 Texture Twin patch-pair SHA-256 bindings, CIE76 Delta-E, and blind critique."""

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
    TextureTwinLedger,
    compute_cie76_delta_e,
    sha256_file,
    validate_patch_critique_report,
)


def _resolve_artifact(raw_path: str, roots: list[Path]) -> Path:
    p = Path(raw_path)
    if p.is_absolute() and p.is_file():
        return p
    for root in roots:
        cand = (root / p).resolve()
        if cand.is_file():
            return cand
    raise FileNotFoundError(f"cannot resolve ledger artifact {raw_path!r} under {roots}")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger-manifest", type=Path, required=True)
    parser.add_argument("--base-dir", type=Path, default=None)
    parser.add_argument("--critique-report", type=Path, default=None)
    parser.add_argument("--max-delta-e", type=float, default=12.0)
    parser.add_argument("--min-score", type=float, default=8.0)
    parser.add_argument("--out-report", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    manifest_path = args.ledger_manifest.resolve()
    raw_ledger = json.loads(manifest_path.read_text(encoding="utf-8"))
    ledger = TextureTwinLedger.from_mapping(raw_ledger)
    ledger.validate(max_delta_e_ab=float(args.max_delta_e))

    roots = []
    if args.base_dir is not None:
        roots.append(args.base_dir.resolve())
    roots.extend([manifest_path.parent, manifest_path.parent.parent, REPO_ROOT])

    src_img_file = _resolve_artifact(ledger.source_image_path, roots)
    if sha256_file(src_img_file) != ledger.source_image_sha256:
        raise ValueError(f"source_image SHA-256 mismatch: {src_img_file}")

    verified_entries = []
    for entry in ledger.entries:
        ref_file = _resolve_artifact(entry.reference_crop_path, roots)
        twin_file = _resolve_artifact(entry.twin_texture_path, roots)
        if sha256_file(ref_file) != entry.reference_crop_sha256:
            raise ValueError(f"reference_crop SHA-256 mismatch for {entry.surface_id}")
        if sha256_file(twin_file) != entry.twin_texture_sha256:
            raise ValueError(f"twin_texture SHA-256 mismatch for {entry.surface_id}")
        live_de = compute_cie76_delta_e(Image.open(ref_file), Image.open(twin_file))
        if live_de > float(args.max_delta_e):
            raise ValueError(
                f"live CIE76 Delta-E {live_de:.3f} exceeds {args.max_delta_e:.3f} for {entry.surface_id}"
            )
        verified_entries.append(
            {
                "surface_id": entry.surface_id,
                "mode": entry.mode,
                "declared_delta_e_ab": entry.delta_e_ab,
                "live_delta_e_ab": round(live_de, 4),
            }
        )

    critique_status = "not_requested"
    if args.critique_report is not None:
        raw_critique = json.loads(args.critique_report.resolve().read_text(encoding="utf-8"))
        validate_patch_critique_report(
            raw_critique,
            max_delta_e_ab=float(args.max_delta_e),
            min_patch_score=float(args.min_score),
        )
        critique_status = "pass"

    summary = {
        "status": "pass",
        "ledger_id": ledger.ledger_id,
        "entry_count": len(verified_entries),
        "max_live_delta_e_ab": max((e["live_delta_e_ab"] for e in verified_entries), default=0.0),
        "critique_status": critique_status,
        "entries": verified_entries,
    }
    if args.out_report is not None:
        args.out_report.resolve().parent.mkdir(parents=True, exist_ok=True)
        args.out_report.resolve().write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(
        f"verified {len(verified_entries)} texture patch pairs "
        f"(max dE={summary['max_live_delta_e_ab']:.2f}, critique={critique_status})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
