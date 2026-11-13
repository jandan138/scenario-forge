# skills/

External agent tooling packages used during asset **production** (the producer
role), kept under version control so that agent sessions in this repo can
invoke them directly.

Boundary:

- Skills here are not core package layers. Nothing under `src/` may import
  them, and they are outside the scope of the architecture-boundary tests,
  ruff, mypy, pytest, and `make check` (all of which cover only `src/`,
  `tests/`, and the top-level `scripts/`).
- Each skill lives in its own subdirectory with its original internal
  structure preserved. A skill's internal `scripts/` directory is **not** the
  repo `scripts/` directory; skill scripts may require external runtimes
  (e.g. Isaac Kit Python) and must always be invoked by full path, e.g.
  `skills/hunyuan-isaac-articulation-assets/scripts/check_articulation_usd.py`.
- Skills are externally maintained. To update one, replace its whole
  subdirectory, re-apply any local amendments listed below, and update the
  recorded archive SHA-256 in `external_artifacts/README.md`.
- A skill's presence here confers no qualification on any asset. Generated
  assets enter the pipeline only through the existing ConvertAsset admission
  boundary (see `docs/standards/asset-intake.md`).

## Inventory

| Skill | Source archive | Archive SHA-256 | Intake date | Provenance |
|---|---|---|---|---|
| `hunyuan-isaac-articulation-assets` | `external_artifacts/incoming/from_xinyu/hunyuan-isaac-articulation-assets.7z` | `d112b48cb2d5a855d313af51f13a23376548f9521ae915ba624ce233a0ea59cb` | 2026-09-17 | `external_artifacts/incoming/from_xinyu/provenance.json` |

## Local amendments

Local amendments are repo-owned edits on top of an external skill. They are
marked inline with `local amendment <date>` and must be re-applied after any
wholesale skill update.

- 2026-09-17 `hunyuan-isaac-articulation-assets`: source-route fallback — if
  Hunyuan3D is unavailable, allow Blender-only procedural modeling driven by
  the frozen asset spec, with additional iteration rounds
  (`SKILL.md`, `references/hunyuan-isaac-workflow.md`).
- 2026-11-13 `hunyuan-isaac-articulation-assets` & `agentic-scene-factory`:
  codify `GEN-008` (`G1..G8 + G9a + G9b`) IKA-grade hero acceptance and
  independent blind-review visual critic loop; promote reusable CAD OpenUSD
  and Cycles `AgX` 4-view studio rendering helpers into
  `skills/hunyuan-isaac-articulation-assets/scripts/{cad_usd_kit.py,blender_usd_studio_render.py}`
  with portable Blender binary discovery (`SKILL.md`,
  `references/ika-grade-acceptance-and-visual-critic.md`,
  `skills/agentic-scene-factory/SKILL.md`).
- 2026-11-13 `agentic-scene-factory`: internalize native Scenario Forge
  `room-source-v2` exporter (`scripts/export_room_source_v2.py`), deterministic
  6-view Cycles `AgX` room gate (`scripts/verify_and_render_room_pack.py`),
  cross-host blind visual critic harness
  (`scripts/run_independent_visual_critic.py`, `.claude/agents/visual-critic.md`),
  and Real-to-Sim 1:1 Texture Twin & reprojection CLIs
  (`scripts/{build_texture_twin_ledger,verify_texture_patch_pairs,render_reprojection_comparison}.py`,
  `references/internalized-room-exporter-and-critic.md`).
