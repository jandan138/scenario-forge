# Fehling r7 demo video: assembled from finalized replay keyframes

## Scope and standards

User requested one openable r7 MP4 showing rack extraction, water-bath entry,
the 30 s color development and withdrawal/observation, with a strict directive
to reuse existing finalized keyframes instead of recording new physics.
Applies MAT-001/002, STATE-002, VAL-001/003/004/005.

规范无需变更：视频是已有 r7 交付证据的展示剪辑，不是新的场景资格；源场景、
ZIP 与三次冷启动报告保持原字节。大型媒体按 VAL-005 留在 Git 外，提交合成脚本与记录。

## Deliverable

- Video: `outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r7_20260912/r7_demo.mp4`
- 48.034 s, 1920×1080, H.264/yuv420p, 30 fps, 1441 frames, 3,238,834 bytes, faststart.
- SHA-256: `705fb4e9038d5ecd6832a642635fcd44062d37bdb6b8ae8b0a94c34e97516d80`.
- Generator: `scripts/assemble_fehlings_r7_video.py`.
- Machine manifest: same output root, `r7_video_manifest.json`.

## Composition

Eleven labeled segments cut from the finalized 29-image replay set
(render manifest SHA256 `17f39cbdd9149ba82cf405dc48db42c328e8227c023071771cb6fd6858c94d2b`,
scene SHA256 `71e38a115fc2b1e5fa8294224d16a3cc17474bc6015196e319c7d431ed460098`):
rack initial, extraction, reinsertion, bath entry, 3/15/21/27/30 s color states,
and final observation. Total ≈48 s with straight cuts, phase labels and a scope
banner drawn onto copies of the frames; source images are not modified.

The first render used DejaVuSans and showed CJK tofu boxes; regenerated with
NotoSansCJK-Bold so Chinese phase labels render. The delivered MP4 hash above
binds the regenerated, reviewed file.

## Verification

- `ffprobe` confirms duration, codec, resolution, frame count above.
- Full `ffmpeg -i r7_demo.mp4 -f null -` decode passes with no errors.
- Extracted frames at t=12 s and t=30 s reviewed: rack/reinsert view and
  reddening closeup are correct with readable bilingual labels.
- No new simulation, physics recording or timing inference was performed.
- This is presentation/educational replay footage, not a live robot capture.

## Git closeout

Only the assembly script, this record and the docs-index entry are committed;
the MP4 stays out of Git per the artifact policy. Scene/qualification evidence
remains as committed in `a8071b6` (r7) and `994dd6c` (producer asset).
