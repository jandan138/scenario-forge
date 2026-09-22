# Fig.1 author-v2: editable PPTX and real simulation media

Date: 2026-09-22. Baseline repository commit:
`5d4b13af86736fe70a3d3535d587c4d1fa1c9808`.

The user explicitly authorized implementation of the v2 reconstruction plan, retaining
manufacturer photographs for Request/Search, showing complete task workspaces without
robots, replacing placeholder imagery, and taking new Isaac Sim camera captures.
The authoritative visual reference is `lab2sim-from-draw-v2.png` in
`paper/venues/iclr2027/figures/lab2sim/fig1_iterations/my-try/`.

## Implementation and evidence

The figure uses a shared measured object inventory for canonical SVG and editable
PPTX. Four panels reproduce the new request/agent/interactivity/scenes hierarchy;
three task-critical close-ups and four complete workspace views replace the previous
layout. A strict skill-compatible figure-spec, named-shape geometry audit and real-media
manifest accompany the deck. Core package APIs, schemas, adapters and scene behavior
are unchanged. New simulator code is figure tooling, outside pure package layers.

The exact-reconstruction workflow from `build-scientific-figures` was applied. Reference
text ink boxes are recorded; character tracking and positions were calibrated against
fresh raster exports. Actual PPTX round-trips exposed an Office autofit-centering issue;
disabling autofit corrected it. Robot glyph eyes/antenna, source panel fills and the
balance title were refined in subsequent rounds.

Rounds r13 onward are appended under the existing `rounds/`. No r03–r12 artifact is
rewritten. The original composer remains available. Each new round carries the source
snapshot, photo inputs and their hashes, geometry/spec, comparison evidence and exports.
`LATEST.json` and the final QA report identify the delivered round and exact bytes.

## Image sourcing and rendering scope

Ten photograph/render slots have explicit source identity. Request/Search reuse the
IKA manufacturer photos already present in the project. Build uses a new isolated
current-delivery OVEN 125 render. The controls and force-balance panels retain original
simulator LCD values (64.8 and 30.0 g); no numbers are painted over them. The burette
close-up is newly captured from the r1.7 scene with its stopcock and receiver neck.

Four table/workstation views use a common camera azimuth (−100°), elevation (30°),
focal length (38 mm), studio illumination and neutral background. Distance and aim
adjust to the task's extent. The existing oven/cart layout is preserved. Source USD
hashes before/after capture match. Only session-layer cameras, lighting, background
visibility and the specifically documented replay state are authored; no source is saved.

- Fehling: exact-scene passing r10 report, `t30` tube/beaker pose and retained five-layer
  material/geometry state. The image does not claim color visibility through glass at
  every viewpoint or a new reaction/runtime validation.
- Powder: r4 recorded frame 960 (32.004 s), including particle positions/orientations
  and body/link poses, replayed statically. The recorded spoon is above the powder bottle.
- Titration: existing r1.7 `after_end_scale` visual-state recipe (25 mL), computed using
  the existing task color policy. This is an illustrative saved-policy state, not a new
  observed fluid-transfer episode, measured chemical result or robot success.
- Oven: existing hinge actuation opens the original articulated oven before pausing
  for the camera capture. Static views do not establish successful robotic handling.

The September 20 colleague-composed packages were inspected first. Their lock status
was not treated as new ConvertAsset/runtime admission. Black surfaces/frames and
insufficient powder-task content in initial candidate captures prompted use of the
current task-delivery sources. Initial studio lighting also exposed competing dome
lights; deactivating original lights in the session layer allowed a single controlled
lighting setup. Rejected captures remain under `outputs/fig1_v2_20260922/`.

## Standards synchronization

Normative sources read: `docs/standards/README.md`, asset-intake,
validation-and-delivery, materials-and-liquids, task-state and maintenance.
Applicable rules: ASSET-001/002/003/004, MAT-001/002/004, STATE-004/007,
VAL-001/002/003/004/005/006/007. Runtime/physics qualifications remain bound to their
original source and environment; visual replay does not broaden them.

**规范无需变更**：本次只更新论文图的版式、可编辑交付和有来源的静态/状态回放拍摄，
未改变准入、USD 组织、物理、任务状态规则或包契约。同步本记录、图目录 README、
figure-spec、素材清单、轮次说明及最终 QA。没有需要修改的核心设计契约或运行操作教程。

## Validation

The initial v2 contract tests failed because the implementation did not exist. After
implementation, original-round and v2 regression tests passed. Repository `make check`
completed successfully; the exact test count and log hash are bound in the final QA
report. Final strict spec validation, PPTX geometry/portability audit, source identity
checks and visual review are recorded there against the delivered files.

The acceptance boundary separates photographic replacements from reference chrome.
Font metrics/antialiasing and simplified vector glyphs retain minor differences; no
whole-image pixel-identity or Microsoft PowerPoint-specific rendering claim is made.
The tested office backend is LibreOffice 7.3.7.2 with Poppler PDF rasterization.

Final delivery: **r19-final-office-review**. `make check`: **1201 passed, 1 skipped**
(549.56 s); final targeted regression **11 passed**. Strict spec: 0 errors/warnings.
Named PPTX geometry: **123 objects checked**, 51 editable texts, 10 real photo slots;
portability violations: 0. Canonical label-ink audit: 45 labels, maximum bbox component
error 2 px; the actual native-size Office export independently meets the same 2 px
budget after the r18–r19 font-ascent corrections. Visual review: 94/100, no Critical/Major findings; remaining Minor font,
icon/fill and small-glass contrast differences are listed in the final QA.
Final crops keep task apparatus in frame while removing table legs, empty background
and nonessential context supplies. All four physical camera orientations remain unchanged.
