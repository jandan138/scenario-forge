# Fig.1: colleague-final gallery replacement

Date: 2026-09-22. Baseline commit: `5d4b13af86736fe70a3d3535d587c4d1fa1c9808`.

User authorization: use the colleague's final scene versions for the four already
selected experiments, keep lighting as consistent as possible, and implement the
agreed plan. This change starts from r19 and changes only the four Robot-ready Isaac
scenes photographs. The request/search/build pipeline and the three interactivity
close-ups remain byte-identical as staged images; all slide shape/text XML is retained.

## Source selection

Source root: `/cpfs/shared/simulation/chenjiantong/scene_usds/scientific_experiments`.
The capture manifest uses `source_root_id: colleague-scientific-experiments` and a
`scene` path relative to this root rather than embedding machine paths in the deck.

| Slot | Selected source |
| --- | --- |
| Fehling | `task_12_fehling_test/seen_scene_4/scene.usd` |
| Powder | `task_09_solid_weighing/seen_scene_4/scene.usd` |
| Titration | `task_10_titration_experiment/seen_scene_4/scene.usd` |
| OVEN 125 | `task_11_remove_container_from_oven/seen_scene_4/scene.usd` |

All 80 scene files match the September 20 packaged-copy hashes. All 20 variants per
family were rendered and reviewed as contact sheets. The consistent neutral-grey
seen-4 material family was selected over near-white low-contrast variants and darker
or colored alternatives. Input inventory, the 80 preview records, contact sheets,
selection rationale and high-resolution captures are under
`outputs/fig1_colleague_20260922/`.

## Capture and preservation

The dedicated figure renderer uses Isaac Sim 4.5 RayTracedLighting. All four cameras
use azimuth −100°, elevation 30°, 38 mm focal length and 36 mm horizontal aperture;
a distance/target calculated from task-apparatus bounds keeps the relevant equipment
in frame. The top slots are captured at 1668×846 and the lower slots at 1668×1008,
so the final figure does not need an additional camera-aspect crop.

Shared neutral-white dome intensity is 700; distant key intensity is 1400 with
rotation −35/−20/35° and angular size 14°. Automatic exposure is disabled at the
actual RTX histogram setting, with ACES, ISO 100, 1/60 s, f/5.6 and neutral white point
explicitly set after loading each stage. Their effective values are read back and
compared across captures. Setting identities were checked against the installed
NVIDIA RTX settings UI and Replicator source, rather than assuming the older AA
setting names controlled exposure.

Source USD hashes are unchanged after capture. Only the session layer receives
cameras, lights, room visibility and graph-disable edits. Authored equipment poses,
geometry, materials, initial liquid states and the closed oven door are preserved.
No r19 legacy task states, old powder particles, old reaction colors or door actuation
are transferred into the colleague scene. This is a static visualization, not a new
runtime-admission or robot-execution result. Material differences are retained even
when they produce different reflectance under the same lighting.

## Validation and standards

The new regression first failed because the old gallery did not identify colleague
sources. After replacement it checks the four intended experiment identities,
authored-state preservation, common lighting/camera orientation and unchanged other
six staged images. `audit_gallery_swap.py` additionally verifies exact slide shape/text
XML equality to r19, exactly four changed named pictures, zero canonical pixel changes
outside those slots, current source hashes and the effective exposure settings.

Strict spec validation, native PPTX geometry/portability audits, actual Office export
review and repository `make check` results are bound to the final round in its QA
report. Each round includes a frozen asset manifest and renderer/source snapshots.

Read standards: asset intake, validation/delivery and maintenance through the scene
standards entry point. Applicable rules: ASSET-001/002/003/004 and
VAL-001/002/003/004/005/006/007. Existing package qualification remains `asset_locked`
where documented; the paper picture does not strengthen that qualification.

**规范无需变更**：本次仅替换论文图的四张场景照片，统一取景与照明并保留来源证据；
不修改原始 USD、场景包、准入规则、物理、任务状态、核心 schema/API 或适配器契约。
同步本记录、图目录 README、选图清单、来源清单及最终 QA；不改写旧轮次和历史交付。

## Final result

Delivered **r20-colleague-final-scenes** and promoted its exact reviewed bytes to the
`my-try` top-level PPTX/SVG/PNG/PDF. Repository `make check`: **1202 passed, 1 skipped**
(536.61 s); targeted old/new figure regression: **12 passed**. Ruff, package smoke,
phase10x smoke and diff check passed. Strict figure-spec validation: 0 errors/warnings.
PPTX portability violations: 0; 123 named object geometries checked.

The slide shape/text XML is byte-identical to r19. Exactly the four named gallery
pictures changed; canonical pixels outside those slots are identical. Actual Office
exports also match outside a one-pixel image-edge band; within that band only 674
pixels differ by one RGB level due to image-edge antialiasing. All 80 original USD
source hashes were rechecked unchanged. Effective exposure and lighting identities
match across the four selected captures. Final visual review has no Critical/Major
finding; selection, source and validation details are bound in the final QA report.
