# Scientific-Environment Background Screening

Date: 2026-07-23

## Outcome

The complete-scene inventory was reduced from 92 source USDs to seven
ConvertAsset admission candidates:

| Rank | Candidate | Raw visual decision | Chosen view | Why it remains |
| ---: | --- | --- | --- | --- |
| 1 | `scientific_environment_081` | PASS | `eye_left` | Most complete equipment-dense wet laboratory; all three views are useful. |
| 2 | `scientific_environment_067` | PASS | `authored` | Large wet laboratory with islands, sinks, utilities, and clear aisles. |
| 3 | `scientific_environment_084` | PASS | `authored` | Complete long laboratory with a central sink island and service structures. |
| 4 | `scientific_environment_085` | WARN | `authored` | Strong room and sink context; requires a better post-normalization standing view. |
| 5 | `scientific_environment_059` | WARN | `authored` | Rich, occupied-looking room; ceiling and exposure require producer inspection. |
| 6 | `scientific_environment_083` | WARN | `authored` | Clear sink island and usable floor; overhead material/geometry needs inspection. |
| 7 | `scientific_environment_066` | WARN | `authored` | Strong liquid-task cues; exposure and ceiling structure need inspection. |

`scientific_environment_061`, `scientific_environment_093`, and
`scientific_environment_054` were rejected after the standardized retake.
Respectively, they showed an incomplete dark room boundary, severe
overexposure/blocked views, and only roofless dollhouse views.

## Evidence produced

The immutable source root was:

```text
/cpfs/shared/simulation/zhuzihou/dev/_datasets/LabUtopia-Dataset
```

All 92 exact complete-scene entries already had upstream 256 × 256 canonical USD
renders. Scenario Forge copied and hash-indexed those renders instead of spending
simulator time reproducing identical first-pass thumbnails. It generated four
full-inventory contact sheets, then retook only the 10 semantically suitable
candidates in the EOS Isaac Sim 4.1.0.0 environment at 640 × 360 with three
camera probes each.

The retake batch captured all 10 candidates successfully. That count is capture
completion only. It is not an asset-pass count. A clean-room visual review,
performed without code or log context, selected the seven candidates above.

The exact external artifact root is:

```text
/cpfs/user/zhuzihou/dev/scenario-forge/outputs/scientific_environment_background_screening_20260723
```

Key identifiers:

- catalog digest:
  `d60b1a9e87b36fb4669b7d7959bf01230d28c29ee10edc030a19156871a9b787`;
- catalog file SHA-256:
  `6b7f3202742020a538ac53f50d1770460e3430282de037e605c73b6e6d54f3c9`;
- retake batch-manifest SHA-256:
  `4b0fea4548497b4438ad5a74af15ee07988cb4c88f50c53e246896f4b16cfabb`;
- final review SHA-256:
  `3766999f55a05fa53c65cbc6d105fcfa4f24369680ae5d97315a3fc14375a86c`;
- ConvertAsset request SHA-256:
  `183e75a8fb210acc11c1c9b59660c05314b198974db51c5967d3b1dfe0d0bbc3`.

## Producer boundary

The generated `convertasset_batch_admission.yaml` is a request, not seven
qualified packages. It binds each request item to its current source SHA, the
catalog digest, the canonical thumbnail SHA, and the selected Isaac retake SHA.
Each item also carries visible defects and raw-runtime concerns for producer
inspection.

The raw previews exposed MDL compilation or texture-coordinate problems in
several visually valuable sources. Scenario Forge did not repair or suppress
them. ConvertAsset remains responsible for dependency/material/mesh closure,
source-bound packaging, visual-static admission, and post-normalization rendering.
Only returned packages whose producer manifests pass the existing strict inbound
contract can later become Scenario Forge inputs.

No upstream source USD was modified. No scene is yet integrated into the eBench
task package, and this screening makes no claim about physics, robot placement,
collision-free operation, benchmark metrics, oracle execution, or liquid
transfer.
