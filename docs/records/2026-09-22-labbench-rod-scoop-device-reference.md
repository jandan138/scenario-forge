# LabBench r35: indicator transfer, spoon detail, device appearance references

Date: 2026-09-22. Baseline: r34-task14-weighing.
User requested four corrections and explicitly approved the implementation plan:
show glass-rod indicator transfer in the blue-bottle experiment, use a loaded-spoon
close-up without the balance, match centrifuge real/reference appearance, and use
the final task14 unshielded balance with a matching real/reference appearance.
User chose to retain four blue-bottle stages and authorized imagegen when suitably
matching physical equipment photographs could not be found.

## Task images

Blue-bottle source: Feishu `task_13_e130_top.mp4`, token
`YXv6bvpKao2c4RxHUqYccB1Rnsg`. The source camera is a fixed close view.
Stages: 125 s reagent mixing; 208 s glass rod transfers methylene-blue indicator,
with visibly blue solution; 242 s fading; 271 s blue recovery during shaking.
The first panel compresses the two solution additions rather than pretending to
show both operations simultaneously. No task imagery was generated.

Scoop source: task14 overlook, 84 s, crop `(395,185,505,265)`. The crop shows the
loaded spoon and powder bottle and excludes the balance. The other task14 frames,
actual 0.19 g final readout, target 0.20 ± 0.02 g and L/M/–/✓ chips remain intact.

## Device pairing and generated-image boundary

The final task14 balance was opened from the 2026-09-20 composed package at
`task_14_fixed_weight_weighing/assets/composed/seen_scene_01/scene.usd`.
Its balance subtree has 168 meshes, whereas task09's corresponding subtree has
112; equal outer dimensions were not treated as proof of identical assets.
A new camera-only capture is stored in `outputs/labbench_real_media_20260922/
renders-v4/`. Source USDs were not saved or changed. The balance has no draft shield.

Image searches included clinical round-lid centrifuges, Heraeus/Jouan/Sigma
centrifuges and Sartorius/Radwag balances. No sufficiently matching photo source
was established for the model's specific enclosure/control layout. The existing
Sigma and draft-shield LICHEN photographs were therefore replaced using the
user-authorized imagegen fallback.

The built-in `image_gen` tool generated two appearance references using inspected
simulation renders as geometric references. Original generated PNGs were copied
into `outputs/labbench_real_media_20260922/generated_refs/`; originals remain in
the tool's generated-image directory. Design briefs, reference-render hashes,
output hashes and origin are recorded in `assets/generation/manifest.json`.
Both figure labels say **Reference**, not Real. Generated images are neither
physical-equipment photographs nor experiment/validation evidence. The actual
Sim images remain simulator/source captures. No claim of commercial model identity
or manufacturer qualification is made for generated devices.

## Validation and standards synchronization

Applicable: ASSET-002, VAL-001/002/003/004/005, plus the figure skill's provenance
and exact-layout rules. Source identity and actual visibility were checked;
generated images are tracked separately from physical photographs and task frames.
**规范无需变更**：本次是论文图的帧选择、相机拍摄和外观参考图替换，未改变场景物理、
任务实现、资产准入或公共 API。同步 figure-spec、生成脚本、来源清单、README、
本记录和最终 QA；不改写历史交付及 r34 之前的归档。

The correction audit verifies exactly 8 changed image slots: a2r, a2s, a5r,
t2p2 and t3p1–t3p4. The remaining 23 images are byte-identical to r34 and pixels
outside the approved card/task regions are unchanged. Checks cover the glass rod,
loaded spoon/no balance, no draft shield, Reference labels, frame times, natural
font sizes, editable deck geometry and an actual Office-rendered PNG review.
Final strict spec, renderer, PPT portability audit and repository check results
are stored in the figure's `qa-report.json` and r35 archive.

Final validation: strict figure spec (0 errors / 0 warnings), editable PPT audit,
actual PPT/SVG renders and region-preservation audit passed. 1202 tests passed,
1 skipped (527.81 s), and Ruff passed. The initial shared-directory package
smoke failed with missing `locks/schema_lock.yaml`; directory interference is
suspected. Package smoke, phase10x and diff check passed when rerun with isolated
`/tmp/labbench-r35-*` outputs. No unrelated source-code change was required.
