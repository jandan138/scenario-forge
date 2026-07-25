#!/usr/bin/env python3
"""Catalog complete scientific-environment USDs from existing render thumbnails.

The script is intentionally simulator-neutral.  It inventories immutable
upstream USD roots and their canonical thumbnails, builds contact sheets for
visual screening, and emits a request for ConvertAsset after an explicit visual
review.  It does not convert, normalize, or admit USD assets.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import shutil
from typing import Any, Mapping, NamedTuple, Sequence

import yaml


CATALOG_SCHEMA = "scenario-forge-scientific-environment-thumbnail-catalog/v0.1"
ADMISSION_SCHEMA = "scenario-forge-convertasset-batch-admission-request/v0.1"
SOURCE_ID_PATTERN = re.compile(r"^lab_(\d{3})$")
THUMBNAIL_SIZE = (256, 256)


class Candidate(NamedTuple):
    source_id: str
    candidate_id: str
    source_usd: Path
    thumbnail: Path


def discover_candidates(dataset_root: Path) -> list[Candidate]:
    """Return canonical complete-scene roots and their exact matching thumbnails."""

    root = dataset_root.resolve()
    labs_root = root / "Labs"
    candidates: list[Candidate] = []
    if not labs_root.is_dir():
        raise ValueError(f"complete-scene directory does not exist: {labs_root}")

    for source_usd in sorted(labs_root.glob("lab_*/lab_*.usd")):
        source_id = source_usd.parent.name
        match = SOURCE_ID_PATTERN.fullmatch(source_id)
        if match is None or source_usd.stem != source_id:
            continue
        thumbnail = (
            source_usd.parent
            / ".thumbs"
            / f"{THUMBNAIL_SIZE[0]}x{THUMBNAIL_SIZE[1]}"
            / f"{source_usd.name}.png"
        )
        if not thumbnail.is_file():
            raise ValueError(
                f"canonical thumbnail is missing for {source_id}: {thumbnail}"
            )
        candidates.append(
            Candidate(
                source_id=source_id,
                candidate_id=f"scientific_environment_{match.group(1)}",
                source_usd=source_usd.resolve(),
                thumbnail=thumbnail.resolve(),
            )
        )

    if not candidates:
        raise ValueError(f"no complete scientific environments found under {labs_root}")
    return candidates


def build_catalog(
    *,
    dataset_root: Path,
    output_root: Path,
    expected_count: int | None = 92,
    shortlist_size: int = 20,
    sheet_columns: int = 5,
    sheet_rows: int = 5,
) -> dict[str, Any]:
    """Build an auditable thumbnail catalog and screening contact sheets."""

    if shortlist_size < 1:
        raise ValueError("shortlist_size must be positive")
    if sheet_columns < 1 or sheet_rows < 1:
        raise ValueError("contact-sheet rows and columns must be positive")

    candidates = discover_candidates(dataset_root)
    if expected_count is not None and len(candidates) != expected_count:
        raise ValueError(
            f"expected {expected_count} complete scenes, found {len(candidates)}"
        )

    out = output_root.resolve()
    thumbnails_dir = out / "thumbnails"
    contact_sheets_dir = out / "contact_sheets"
    shortlist_dir = out / "shortlist"
    for generated_dir in (thumbnails_dir, contact_sheets_dir, shortlist_dir):
        if generated_dir.exists():
            shutil.rmtree(generated_dir)
        generated_dir.mkdir(parents=True)

    entries: list[dict[str, Any]] = []
    for candidate in candidates:
        copied_thumbnail = thumbnails_dir / f"{candidate.candidate_id}.png"
        shutil.copy2(candidate.thumbnail, copied_thumbnail)
        metrics = _inspect_thumbnail(copied_thumbnail)
        entries.append(
            {
                "candidate_id": candidate.candidate_id,
                "source_id": candidate.source_id,
                "source_usd": str(candidate.source_usd),
                "source_scope": "/World",
                "source_size_bytes": candidate.source_usd.stat().st_size,
                "source_sha256": _file_sha256(candidate.source_usd),
                "thumbnail_source": str(candidate.thumbnail),
                "thumbnail_path": str(copied_thumbnail.relative_to(out)),
                "thumbnail_sha256": _file_sha256(copied_thumbnail),
                "thumbnail_metrics": metrics,
                "screening_score": _screening_score(metrics),
                "quality_flags": _quality_flags(metrics),
            }
        )

    ranked = sorted(
        entries,
        key=lambda entry: (
            -float(entry["screening_score"]),
            str(entry["candidate_id"]),
        ),
    )
    rank_by_id = {
        str(entry["candidate_id"]): rank
        for rank, entry in enumerate(ranked, start=1)
    }
    for entry in entries:
        entry["deterministic_rank"] = rank_by_id[str(entry["candidate_id"])]

    _write_contact_sheets(
        entries=entries,
        output_dir=contact_sheets_dir,
        catalog_root=out,
        columns=sheet_columns,
        rows=sheet_rows,
    )
    shortlist = ranked[: min(shortlist_size, len(ranked))]
    _write_single_contact_sheet(
        entries=shortlist,
        output_path=shortlist_dir / "contact_sheet.png",
        catalog_root=out,
        columns=min(5, max(1, len(shortlist))),
    )

    digest_payload = {
        "schema_version": CATALOG_SCHEMA,
        "entries": entries,
    }
    catalog: dict[str, Any] = {
        "schema_version": CATALOG_SCHEMA,
        "catalog_digest": _json_sha256(digest_payload),
        "source_dataset_root": str(dataset_root.resolve()),
        "candidate_count": len(entries),
        "thumbnail_origin": (
            "Upstream canonical USD thumbnails; suitable for visual triage, "
            "not ConvertAsset admission evidence."
        ),
        "selection_policy": {
            "screening_score_role": "deterministic_triage_only",
            "manual_visual_review_required": True,
            "shortlist_size": min(shortlist_size, len(entries)),
            "ranking_tie_break": "candidate_id_ascending",
        },
        "shortlist": [
            {
                "candidate_id": str(entry["candidate_id"]),
                "deterministic_rank": int(entry["deterministic_rank"]),
                "screening_score": float(entry["screening_score"]),
            }
            for entry in shortlist
        ],
        "entries": entries,
        "claim_boundary": (
            "The catalog proves source and thumbnail inventory only. Visual review "
            "does not establish dependency closure, material correctness, runtime "
            "compatibility, physics behavior, license clearance, or task success."
        ),
    }
    _write_json(out / "catalog.json", catalog)
    return catalog


def build_admission_request(
    *,
    catalog: Mapping[str, Any],
    review_document: Mapping[str, Any],
    output_path: Path,
    max_items: int = 10,
) -> dict[str, Any]:
    """Write a non-executable ConvertAsset request from selected visual reviews."""

    if max_items < 1:
        raise ValueError("max_items must be positive")
    catalog_digest = _validate_catalog(catalog)
    if review_document.get("catalog_digest") != catalog_digest:
        raise ValueError("visual-review catalog digest does not match catalog")
    reviews = review_document.get("reviews")
    if not isinstance(reviews, Mapping):
        raise ValueError("visual review must contain a reviews mapping")
    entries_raw = catalog.get("entries")
    if not isinstance(entries_raw, list):
        raise ValueError("catalog.entries must be a list")
    entries = {
        str(entry["candidate_id"]): entry
        for entry in entries_raw
        if isinstance(entry, Mapping) and isinstance(entry.get("candidate_id"), str)
    }

    selected_reviews: list[
        tuple[int, int, Mapping[str, Any], Mapping[str, Any], dict[str, str]]
    ] = []
    for candidate_id, review in reviews.items():
        if not isinstance(review, Mapping):
            raise ValueError(f"review must be a mapping: {candidate_id}")
        if candidate_id not in entries:
            raise ValueError(f"review references unknown candidate: {candidate_id}")
        entry = entries[candidate_id]
        expected_hash = entry.get("thumbnail_sha256")
        if review.get("thumbnail_sha256") != expected_hash:
            raise ValueError(f"review thumbnail hash is stale for {candidate_id}")
        status = str(review.get("status", "")).upper()
        if status not in {"PASS", "WARN", "FAIL"}:
            raise ValueError(f"invalid visual review status for {candidate_id}: {status}")
        visible_evidence = review.get("visible_evidence")
        if not isinstance(visible_evidence, str) or not visible_evidence.strip():
            raise ValueError(f"visual review evidence is missing for {candidate_id}")
        selected = review.get("selected_for_admission", status == "PASS")
        if not isinstance(selected, bool):
            raise ValueError(
                f"selected_for_admission must be boolean for {candidate_id}"
            )
        if not selected:
            continue
        if status == "FAIL":
            raise ValueError(f"failed visual review cannot be selected: {candidate_id}")
        render_evidence = _validate_render_evidence(
            review.get("render_evidence"),
            candidate_id=str(candidate_id),
        )
        source_path = Path(str(entry.get("source_usd", ""))).resolve()
        if not source_path.is_file() or _file_sha256(source_path) != entry.get(
            "source_sha256"
        ):
            raise ValueError(f"catalog source hash is stale for {candidate_id}")
        selection_rank = int(
            review.get("selection_rank", entry.get("deterministic_rank", 10**9))
        )
        deterministic_rank = int(entry.get("deterministic_rank", 10**9))
        selected_reviews.append(
            (selection_rank, deterministic_rank, entry, review, render_evidence)
        )

    selected_reviews.sort(
        key=lambda item: (item[0], item[1], str(item[2]["candidate_id"]))
    )
    selected_items = selected_reviews[:max_items]

    request: dict[str, Any] = {
        "schema_version": ADMISSION_SCHEMA,
        "request_id": (
            f"scientific_environment_visual_static_{catalog_digest[:12]}"
        ),
        "catalog_digest": catalog_digest,
        "target": {
            "consumer_profile": "scenario-forge",
            "runtime_profile": "isaac41",
            "asset_role": "visual_static_environment",
        },
        "items": [
            {
                "candidate_id": str(entry["candidate_id"]),
                "source_usd": str(entry["source_usd"]),
                "source_sha256": str(entry["source_sha256"]),
                "source_scope": str(entry["source_scope"]),
                "visual_review": {
                    "selection_rank": selection_rank,
                    "status": str(review["status"]).upper(),
                    "thumbnail_sha256": str(entry["thumbnail_sha256"]),
                    "visible_evidence": str(review["visible_evidence"]),
                    "render_evidence": render_evidence,
                },
                "producer_attention": _producer_attention(review, entry),
                "required_return": {
                    "overall_status": "pass",
                    "runtime_profile": "isaac41",
                    "asset_role": "visual_static_environment",
                    "package_manifest": "evidence/manifest.json",
                    "post_normalization_render": "pass",
                },
            }
            for selection_rank, _, entry, review, render_evidence in selected_items
        ],
        "claim_boundary": (
            "This non-executable file requests producer-owned admission work and does "
            "not make any listed source an admitted Scenario Forge asset."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        yaml.safe_dump(request, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return request


def _validate_catalog(catalog: Mapping[str, Any]) -> str:
    schema_version = catalog.get("schema_version")
    if schema_version != CATALOG_SCHEMA:
        raise ValueError(f"unsupported catalog schema: {schema_version}")
    entries = catalog.get("entries")
    if not isinstance(entries, list):
        raise ValueError("catalog.entries must be a list")
    candidate_ids: list[str] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ValueError("catalog entries must be mappings")
        candidate_id = entry.get("candidate_id")
        if not isinstance(candidate_id, str) or not candidate_id:
            raise ValueError("catalog candidate_id must be a non-empty string")
        candidate_ids.append(candidate_id)
        for field in ("source_sha256", "thumbnail_sha256"):
            digest = entry.get(field)
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError(f"invalid {field} for {candidate_id}")
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("catalog candidate IDs must be unique")

    catalog_digest = str(catalog.get("catalog_digest", ""))
    expected_digest = _json_sha256(
        {
            "schema_version": schema_version,
            "entries": entries,
        }
    )
    if catalog_digest != expected_digest:
        raise ValueError("catalog digest does not match catalog entries")
    return catalog_digest


def _validate_render_evidence(
    raw_evidence: object,
    *,
    candidate_id: str,
) -> dict[str, str]:
    if not isinstance(raw_evidence, Mapping):
        raise ValueError(f"render evidence is missing for {candidate_id}")
    raw_path = raw_evidence.get("path")
    expected_sha256 = raw_evidence.get("sha256")
    view = raw_evidence.get("view")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError(f"render-evidence path is missing for {candidate_id}")
    if not isinstance(expected_sha256, str) or not re.fullmatch(
        r"[0-9a-f]{64}", expected_sha256
    ):
        raise ValueError(f"render-evidence hash is invalid for {candidate_id}")
    if not isinstance(view, str) or not view.strip():
        raise ValueError(f"render-evidence view is missing for {candidate_id}")
    path = Path(raw_path).resolve()
    if not path.is_file():
        raise ValueError(f"render-evidence file does not exist for {candidate_id}: {path}")
    if _file_sha256(path) != expected_sha256:
        raise ValueError(f"render-evidence hash is stale for {candidate_id}")
    return {
        "path": str(path),
        "sha256": expected_sha256,
        "view": view,
    }


def _producer_attention(
    review: Mapping[str, Any],
    entry: Mapping[str, Any],
) -> list[str]:
    raw_attention = review.get("producer_attention", [])
    if not isinstance(raw_attention, list) or not all(
        isinstance(item, str) and item.strip() for item in raw_attention
    ):
        raise ValueError(
            f"producer_attention must be a list of strings for {entry['candidate_id']}"
        )
    return [str(item) for item in raw_attention]


def _inspect_thumbnail(path: Path) -> dict[str, Any]:
    from PIL import Image, ImageFilter, ImageStat

    with Image.open(path) as source:
        image = source.convert("RGB")
        width, height = image.size
        sample = image.resize((128, 128))
        gray = sample.convert("L")
        stat = ImageStat.Stat(gray)
        histogram = gray.histogram()
        pixel_count = sum(histogram)
        entropy = 0.0
        if pixel_count:
            for count in histogram:
                if count:
                    probability = count / pixel_count
                    entropy -= probability * math.log2(probability)
        non_dark = sum(histogram[13:])
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edge_mean = float(ImageStat.Stat(edges).mean[0]) / 255.0
        return {
            "width": width,
            "height": height,
            "mean_luminance": round(float(stat.mean[0]), 4),
            "luminance_stddev": round(float(stat.stddev[0]), 4),
            "entropy_bits": round(entropy, 6),
            "non_dark_fraction": round(non_dark / max(1, pixel_count), 6),
            "edge_strength": round(edge_mean, 6),
        }


def _screening_score(metrics: Mapping[str, Any]) -> float:
    coverage = min(1.0, max(0.0, float(metrics["non_dark_fraction"])))
    entropy = min(1.0, max(0.0, float(metrics["entropy_bits"]) / 8.0))
    contrast = min(1.0, max(0.0, float(metrics["luminance_stddev"]) / 64.0))
    edges = min(1.0, max(0.0, float(metrics["edge_strength"]) / 0.25))
    score = 100.0 * (
        0.35 * coverage + 0.30 * entropy + 0.20 * contrast + 0.15 * edges
    )
    return round(score, 4)


def _quality_flags(metrics: Mapping[str, Any]) -> list[str]:
    flags: list[str] = []
    if (int(metrics["width"]), int(metrics["height"])) != THUMBNAIL_SIZE:
        flags.append("unexpected_resolution")
    if float(metrics["non_dark_fraction"]) < 0.20:
        flags.append("low_visible_content")
    if float(metrics["mean_luminance"]) < 18.0:
        flags.append("underexposed")
    if float(metrics["luminance_stddev"]) < 10.0:
        flags.append("low_contrast")
    return flags


def _write_contact_sheets(
    *,
    entries: Sequence[Mapping[str, Any]],
    output_dir: Path,
    catalog_root: Path,
    columns: int,
    rows: int,
) -> None:
    page_size = columns * rows
    for page_index, start in enumerate(range(0, len(entries), page_size), start=1):
        _write_single_contact_sheet(
            entries=entries[start : start + page_size],
            output_path=output_dir / f"all_{page_index:03d}.png",
            catalog_root=catalog_root,
            columns=columns,
        )


def _write_single_contact_sheet(
    *,
    entries: Sequence[Mapping[str, Any]],
    output_path: Path,
    catalog_root: Path,
    columns: int,
) -> None:
    from PIL import Image, ImageDraw, ImageFont

    if not entries:
        raise ValueError("cannot create an empty contact sheet")
    columns = min(max(1, columns), len(entries))
    rows = math.ceil(len(entries) / columns)
    cell_width = 272
    cell_height = 292
    sheet = Image.new(
        "RGB",
        (columns * cell_width, rows * cell_height),
        (24, 24, 24),
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, entry in enumerate(entries):
        row, column = divmod(index, columns)
        x = column * cell_width
        y = row * cell_height
        image_path = catalog_root / str(entry["thumbnail_path"])
        with Image.open(image_path) as source:
            thumbnail = source.convert("RGB")
        sheet.paste(thumbnail, (x + 8, y + 8))
        label = (
            f"{entry['source_id']}  rank {entry['deterministic_rank']}  "
            f"score {float(entry['screening_score']):.1f}"
        )
        draw.text((x + 8, y + 268), label, fill=(245, 245, 245), font=font)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(16 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _json_sha256(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Catalog complete scientific-environment USD backgrounds."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    catalog_parser = subparsers.add_parser(
        "catalog", help="Inventory canonical thumbnails and build contact sheets."
    )
    catalog_parser.add_argument("--dataset-root", type=Path, required=True)
    catalog_parser.add_argument("--out", type=Path, required=True)
    catalog_parser.add_argument("--expected-count", type=int, default=92)
    catalog_parser.add_argument("--shortlist-size", type=int, default=20)
    catalog_parser.add_argument("--sheet-columns", type=int, default=5)
    catalog_parser.add_argument("--sheet-rows", type=int, default=5)

    admission_parser = subparsers.add_parser(
        "admission", help="Create a ConvertAsset request from visual reviews."
    )
    admission_parser.add_argument("--catalog", type=Path, required=True)
    admission_parser.add_argument("--reviews", type=Path, required=True)
    admission_parser.add_argument("--out", type=Path, required=True)
    admission_parser.add_argument("--max-items", type=int, default=10)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "catalog":
        catalog = build_catalog(
            dataset_root=args.dataset_root,
            output_root=args.out,
            expected_count=args.expected_count,
            shortlist_size=args.shortlist_size,
            sheet_columns=args.sheet_columns,
            sheet_rows=args.sheet_rows,
        )
        print(
            f"Cataloged {catalog['candidate_count']} environments: "
            f"{args.out.resolve() / 'catalog.json'}"
        )
        return 0

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    review_document = yaml.safe_load(args.reviews.read_text(encoding="utf-8"))
    if not isinstance(review_document, Mapping):
        raise ValueError("review document must be a mapping")
    request = build_admission_request(
        catalog=catalog,
        review_document=review_document,
        output_path=args.out,
        max_items=args.max_items,
    )
    print(
        f"Prepared {len(request['items'])} ConvertAsset admission items: "
        f"{args.out.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
