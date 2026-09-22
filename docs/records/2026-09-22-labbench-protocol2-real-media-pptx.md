# LabBench protocol2: typography and real-media PPTX

Date: 2026-09-22. Baseline repository commit:
`5d4b13af86736fe70a3d3535d587c4d1fa1c9808`.

User authorization: continue the exact-layout figure with uniform small text,
replace reference illustrations with real photos/simulation renders, read the
specified Feishu videos, and rerender suitable views. The user chose real-media
semantics over retaining mismatched vessel labels, and product/project photos
on visual quality. The user then requested implementation of the plan.

## Scope and result

The figure directory is
`paper/venues/iclr2027/figures/bench/protocol2/lab-bench-exact/`.
Continuation from r24 through r33: 145 editable text shapes use role-level sizes;
all 31 photo slots have real source provenance; 159 retained named nontext shapes retain
r24 EMU geometry. The takeaway-2 glyph crop is a deliberate 7 px trim to remove
neighboring lettering. Panel/arrow topology is retained. PPTX is the primary
artifact; native SVG, PNG and office-exported PDF are also retained.

The Feishu wiki is
https://aicarrier.feishu.cn/wiki/Og5Hw2fGGi8pIyk0SpBcrkGCnjf .
`docs +fetch --as user` discovered 56 videos across 14 tasks. `+media-preview`
returned HTTP 504; `+media-download` succeeded. Overlook frames from task_01,
task_09 and task_13 were chosen after comparing overlook and wrist viewpoints.
Raw videos and contact/render inputs are local external artifacts under
`outputs/labbench_real_media_20260922/`. No Feishu writes or messages occurred.

Source identities and SHA-256 hashes, frame times, source URLs, fitted crops and
brightness multipliers are in `assets/manifest.json`. Raw product/source imagery
is preserved. No generated photo or invented measured result was introduced.

## Rendering findings and boundaries

The shared 2026-09-20 composed packages were used for camera-only asset inspection.
The new scene's stirrer exhibited black-face rendering; its clear admitted-source
preview was selected. Source previews for LICHEN balance and stirrer are actual
project asset renders, not original reference-figure pixels. The oven uses the
existing current-delivery camera retake matching the supplied manufacturer's
open-door photograph. Manufacturer centrifuge/stirrer photos are category-level
counterparts, not exact model/geometry evidence; the asset title/subtitle was
reworded accordingly.

Static captures do not prove robot execution. Generalization views hide
uninitialised fluid helpers in the USD session layer for a static composition
photograph. No source USD is saved. These thumbnails illustrate object/context
factors and do not claim an isolated controlled experiment. The titration images
are saved simulator states; score boxes remain an illustrative author example,
not newly measured scores for one episode. The benchmark chart is retained from
the user reference; this task did not validate the numerical claims.

## Standards synchronization

Read `docs/standards/README.md`, asset-intake, validation-and-delivery and
maintenance. Applicable rules: ASSET-001/002/003/004 and VAL-001/002/003/004/005.
Scope: figure sourcing, source identity, static visualization and deliverable
review; no runtime capability is upgraded by the paper images.

**规范无需变更**：本次仅统一论文图字体、替换有来源的图片和另存相机拍摄结果，
未改变资产接入、场景包、schema、适配器或物理/任务规则。同步本记录、图目录 README、
figure-spec、素材 provenance 和最终导出 QA。原始 USD、历史交付包和 r01–r24 不改写。

## Validation

Strict figure-spec validation: 0 errors, 0 warnings.
`audit_delivery.py`: 31 replacement hashes, no reference-photo fallback,
role font equality (including 8.25 pt axis descriptions), one editable slide,
159 unchanged named-shape boxes, native SVG text, no full-slide raster.
PPT audit: flat effects, no external relationships or machine-specific paths.
Final PPTX and SVG are rendered and inspected; output backend and hashes are
in the round's renderer QA. Repository `make check` result is recorded in the
final `qa-report.json` after completion.

Final repository check: **passed** — 1197 tests passed, 1 skipped (553.10 s); Ruff,
package smoke, phase10x smoke and `git diff --check` passed. Final office and SVG
renderer reports passed. Masked chrome pixel difference versus r24 is **0.000102**;
deliberate text and raster replacements are excluded from that comparison.

Final enlarged review produced r32 (takeaway-title wrap and aligned body rows)
and r33 (raster No/Yes words converted to native axis legends). The final deck
has 145 text shapes, 96 pictures and 307 total shapes. Green check symbols remain
small source crops. Card-containment assertions and fresh export audits passed.
