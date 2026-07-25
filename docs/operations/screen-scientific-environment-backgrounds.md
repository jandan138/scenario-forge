# Screen Scientific-Environment Backgrounds

This workflow reduces the complete-scene inventory to a small, visually useful
ConvertAsset admission batch. It does not normalize assets and does not make a
source scene eligible for package generation by itself.

The stages are deliberately separate:

1. inventory every complete source scene and its canonical USD thumbnail;
2. inspect the full inventory as contact sheets;
3. retake only the visually relevant candidates in the pinned Isaac Sim runtime;
4. bind the final review to exact source, thumbnail, and retake hashes;
5. emit a non-executable ConvertAsset admission request for 5–10 candidates.

Do not send the complete source inventory to ConvertAsset. Automatic image
complexity is only a triage hint: a visually busy bar or classroom can score
high while being unsuitable for a wet-laboratory task.

## Runtime

Run from the Scenario Forge repository root. Use the existing EOS environments;
this workflow neither creates nor edits conda environments.

```bash
TEST_ENV=/cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/embodied-eval-os-sim-newton-ebench-experimental-py310
ISAAC_ENV=/cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/embodied-eval-os-sim-isaacsim41-genmanip-py310
DATASET=/cpfs/shared/simulation/zhuzihou/dev/_datasets/LabUtopia-Dataset
OUT="$PWD/outputs/scientific_environment_background_screening_$(date -u +%Y%m%d)"
```

Pillow is a development dependency because cataloging creates PNG contact
sheets. Isaac/Omni/PXR imports occur only inside the renderer worker, after
`SimulationApp` starts. The pure catalog path has no simulator or ConvertAsset
implementation dependency.

## Inventory all complete scenes

```bash
"$TEST_ENV/bin/python" scripts/catalog_scientific_environment_backgrounds.py \
  catalog \
  --dataset-root "$DATASET" \
  --out "$OUT" \
  --expected-count 92 \
  --shortlist-size 20 \
  --sheet-columns 5 \
  --sheet-rows 5
```

Discovery is intentionally exact:

```text
Labs/lab_NNN/lab_NNN.usd
Labs/lab_NNN/.thumbs/256x256/lab_NNN.usd.png
```

The raw upstream names remain provenance only; public Scenario Forge candidate
IDs use `scientific_environment_NNN`. An unrelated thumbnail or an instrument
USD cannot enter the catalog.

Outputs:

- `catalog.json`: source and thumbnail paths, SHA-256 values, image metrics, and
  deterministic triage ranks;
- `contact_sheets/all_*.png`: every candidate in source-ID order;
- `shortlist/contact_sheet.png`: automatic triage only;
- `thumbnails/*.png`: local copies of the canonical USD renders.

The canonical thumbnails are adequate for first-pass rejection, but their
cameras are not standardized. Do not interpret the automatic score as semantic
laboratory quality or as ConvertAsset evidence.

## Review and retake the leading candidates

Create a review document bound to `catalog_digest` and each canonical thumbnail
SHA. Mark obvious wrong-room candidates `FAIL`; use `PASS` or `WARN` for scenes
worth a standardized retake.

```bash
"$TEST_ENV/bin/python" scripts/ebench/render_scientific_environment_previews.py \
  batch \
  --catalog "$OUT/catalog.json" \
  --reviews "$OUT/visual_reviews.yaml" \
  --isaac-python "$ISAAC_ENV/bin/python" \
  --out "$OUT/isaac41_retakes" \
  --max-scenes 10 \
  --timeout-seconds 600 \
  --width 640 \
  --height 360
```

The worker requires Isaac Sim 4.1.x and rechecks every source hash before
opening it. It preserves the authored Perspective view and adds two low-angle
orbit probes. Those probes are diagnostic and may land behind a wall; they are
not guaranteed indoor cameras. Each candidate directory contains three images,
a contact sheet, a render manifest, and the complete runtime log.

`render_status: pass` in the v0.1 preview manifest means that image capture
completed. It does not mean materials, references, geometry, physics, or the
source asset passed admission. The final reviewer must inspect the images, and
ConvertAsset must inspect the runtime signals.

## Final visual decision

Use an implementation-independent visual review of the retake contact sheets.
The target is a complete, credible wet laboratory around a dual-arm tabletop
task. For every selected scene record:

- `status`: `PASS` or `WARN`;
- `selected_for_admission: true`;
- explicit selection rank;
- canonical thumbnail SHA;
- visible evidence;
- one chosen retake image path, SHA, and view;
- concrete `producer_attention` items.

`WARN` is allowed into the producer request only when the environment is
visually valuable and the observed defect is an explicit ConvertAsset admission
question. `FAIL` cannot be selected.

## Prepare the ConvertAsset batch

```bash
"$TEST_ENV/bin/python" scripts/catalog_scientific_environment_backgrounds.py \
  admission \
  --catalog "$OUT/catalog.json" \
  --reviews "$OUT/final_visual_reviews.yaml" \
  --out "$OUT/convertasset_batch_admission.yaml" \
  --max-items 10
```

Before writing the request, the tool recomputes the catalog digest, rehashes
each selected source, and verifies the chosen retake image. The result contains
no ConvertAsset command and performs no conversion. Give the YAML plus its
referenced retake images and logs to the ConvertAsset owner.

For every item, ConvertAsset must return its producer-owned package and
`evidence/manifest.json` with an Isaac 4.1 `visual_static_environment` pass and a
post-normalization render. Scenario Forge must subsequently consume that
delivery through its existing strict ConvertAsset handoff loader. Do not add
scene-specific USD, MDL, mesh, collider, mass, inertia, or warning-suppression
repairs here.

## Artifact policy

All PNGs, runtime logs, raw source USDs, and generated requests stay under
`outputs/` or another documented external artifact root. Commit only scripts,
tests, the runbook, a dated evidence summary, and a small external-artifact
index.
