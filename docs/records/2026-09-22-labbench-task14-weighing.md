# LabBench protocol2 — task14 fixed-mass powder weighing

Date: 2026-09-22. Continues r33; new round: `r34-task14-weighing`.
User explicitly requested replacing Solid Weighing with Feishu task14, then
approved implementation of the detailed replacement plan.

## Authoritative task and selected frames

Source: https://aicarrier.feishu.cn/wiki/Og5Hw2fGGi8pIyk0SpBcrkGCnjf,
document revision 4236, task_14: 使用药匙舀取粉末进行固定重量称量.
Target: **0.20 ± 0.02 g**. Difficulty: long horizon, medium spatial difficulty,
no temporal requirement, perceptual requirement (read the balance).

All four views of the same `task_14_e130` recording were downloaded and inspected.
Selected frames:

| Slide stage | Source view | Time | Visible state |
| --- | --- | --- | --- |
| Setup / tare | overlook | 32 s | Weighing boat on scale, display zeroed |
| Scoop powder | overlook | 70 s | Spoon enters wide-mouth powder bottle |
| Dose powder | overlook | 104 s | Loaded spoon above weighing boat |
| Check mass | top | 220 s | Actual LCD reading 0.19 g |

The source camera called `top` is the useful balance-display close-up, not a
geometric overhead view. The actual 0.19 g lies within 0.18–0.22 g. No digits
were altered or composed. Cropping and whole-image brightness ×1.12 are recorded.
Media identities, token, frame time, crop, source hashes and crop hashes are
in the figure's `assets/manifest.json`. Downloaded raw videos are retained in
`outputs/labbench_real_media_20260922/videos/task14-{overlook,top}.mp4`.

## Figure changes

Title: Target-Mass Weighing. Stages: Setup / tare, Scoop powder, Dose powder,
Check mass. Tags: 0.20 ± 0.02 g, powder dosing, mass feedback.
Difficulty chips: L / M / – / ✓. Native role font sizes and the four photo-slot
boxes remain the existing values. Only the second task row changes; the other
27 photo assets are byte-identical to their r33 versions. Task09 footage remains
as historical material but is no longer used by the active figure.

## Verification and synchronization

Applicable existing standards: ASSET-002 and VAL-001/002/003/004/005. Their scope
here is source identity, faithful frame content, figure QA and artifact retention.
**规范无需变更**：本次仅替换论文图中的任务、文字、难度标记和有来源的视频帧，
未修改场景 USD、资产/包准入、物理、任务实现、schema 或公共 API。
同步生成脚本、figure-spec、素材清单、README、轮次归档与本记录。

The dedicated task14 audit checks the four expected source/time bindings,
source SHA-256, unchanged hashes for all other photos, and pixel equality outside
the second task row against r33. Existing deck audit checks font-role equality,
editable text, locked shape geometry and no full-slide raster. The strict figure
spec validator and flat/portable PPT audit are run on the final deck. Actual
LibreOffice/PDF PNG export is inspected at full-slide and row-crop scale.
Final check results and artifact SHA-256 are in the top-level figure QA report.

Final result: all figure audits and actual PPTX/SVG exports passed. `make check`
passed: 1201 tests passed, 1 skipped (546.05 s), Ruff and both smoke
workflows passed, and `git diff --check` passed.
