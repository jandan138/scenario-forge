# Out-of-Domain Round-3 (`r3`) Swarm Upgrade & `GEN-008` (`G1..G9b`) Acceptance Record

- **Date**: 2026-11-13
- **Artifact Root**: `external_artifacts/out_of_domain_factory_r3_20261113`
- **Configs**:
  - `configs/source_bindings/out_of_domain_hero_r3_20261113.yaml`
  - `configs/out_of_domain_tasks_r3/specialty_coffee_bar_creatista_prep.yaml`
  - `configs/out_of_domain_tasks_r3/electronics_qa_ingun_probe_lock.yaml`
  - `configs/out_of_domain_tasks_r3/modern_office_brother_calibrate.yaml`

## 1. Track 1 — `GEN-008` (`G1..G8 + G9a + G9b`) Acceptance Summary (`30/30 PASS`)

All three `r2` CAD-grade articulated hero assets passed all 10 gates (`G1..G8`, `G9a` Isaac Sim 4.1 RTX inspection + visual self-consistency, `G9b` blind VLM critique):

- Report: `external_artifacts/out_of_domain_factory_r3_20261113/hero_g9b_acceptance/ika_acceptance_summary_v2.json`
- SHA-256: `327c7cbd67b1b285b4c2bc9ad3e11e7700f0162c024edc361c0f26a422da4a20`
- Scoreboard: `30/30 PASS` (`10/10` per hero across `NespressoCreatistaPlus`, `IngunMA2111Fixture`, `BrotherMFCL2820DW`).

## 2. Track 2 — `Code-as-Room` `r3` Rooms & `ConvertAsset` (`isaac41`) Admission

All three `r3` rooms passed Blender Cycles blind critique (`visual_critique_report.json`), `Code-as-Room` source export (`support_audit == pass`), `intake_generated_environment.py`, and `ConvertAsset` (`isaac41`) normalization (`static,runtime` gates) with `deps/textures/` preserved:

| Room ID | Asset ID | Task ID | Textures | Cycles Critique (`min / mean`) | Normalized Manifest SHA-256 |
|---|---|---|---:|---|---|
| `kitchen_coffee_bar_v2` | `out_of_domain_env_kitchen_coffee_bar_v2` | `specialty_coffee_bar_creatista_prep` | 15 | PASS (`8.6 / 8.98`) | `7ea58583a17ea1a667853618db75d827814cce1f072ef81ff45bb8af2c95f113` |
| `smt_qa_workshop_v2` | `out_of_domain_env_smt_qa_workshop_v2` | `electronics_qa_ingun_probe_lock` | 11 | PASS (`8.6 / 8.82`) | `cca468903a228933219e790b7f1888be398b1154f5f37cb1b3de9877b5e066a4` |
| `office_print_studio_v2` | `out_of_domain_env_office_print_studio_v2` | `modern_office_brother_calibrate` | 10 | PASS (`8.6 / 8.76`) | `b82d209e324c07c188b0210fa2676ea32c411ece88cab2f327c68e7280d463c2` |

- `rooms_admission_summary.json` SHA-256: `dec24d6400c4e77c75c35de7da003171e3e98de1d3c6768da65e915c107cebf9`

## 3. End-to-End `r3` Compilation, Canary, Preview & Showcase Verification

1. **Scene Gate (`scripts/run_out_of_domain_scene_gate.py`)**:
   - `3/3` compiled & GenManip-collected (`package_validation_ok=true`, `asset_lock_ok=true`, `visual_ready_gate_status=passed`).
   - `scene_gate_summary.json` SHA-256: `3660a2c5247bf749541af3bdc69606cff237de38002b6fb26c6d7d51322d0ba6`.
2. **GenManip Predicate Canary (`scripts/verify_genmanip_predicate_canary.py --profile r3`)**:
   - `specialty_coffee_bar_creatista_prep`: `0.00 -> 1.00` (6 stages), Critic-1 drift `1e-06 m`
   - `electronics_qa_ingun_probe_lock`: `0.00 -> 1.00` (5 stages), Critic-1 drift `1e-06 m`
   - `modern_office_brother_calibrate`: `0.00 -> 1.00` (5 stages), Critic-1 drift `0.0 m`
   - `predicate_canary_summary.json` SHA-256: `65ecf85c911384fddbde08741ca18f22c960f6d197fd7310abf63e80cdb116d2`.
3. **Preview & Composed Isaac Sim 4.1 RTX Visual Critique**:
   - Extended `_COMPLETE_WALL_ROOT_NAME` (`src/scenario_forge/adapters/ebench/preview.py` and `scripts/ebench/render_genmanip_initial_preview.py`) to recognize `Arch_Wall_{North,South,East,West}*` without matching `Arch_Wall_Outlets_Sconces` or `WallShelf_*`.
   - Updated `scripts/ebench/render_genmanip_initial_preview.py` to hide ceiling occluders during `room_topdown`/`room_corner_a`/`room_corner_b`, hide closed entrance door leaves/daylight cards during `room_entrance_eye_level` while keeping jambs/frames intact, and enable interior 4-SphereLight studio fill + `DomeLight(1100.0)` when viewing enclosed interior shots (`scene_overview`, `room_entrance_eye_level`).
   - `canary_media_summary.json` SHA-256: `56cf10f4bb91067cf73d1ac770cb0d0f171744f9311fddf4d45f98ad9b97cb7c`.
   - `rtx_composed_critique_report.json` (`3/3 PASS`, Round 2 blind audit by `@visual-critic`: `min >= 8.8`, means `8.90`, `8.925`, `8.975`) SHA-256: `3f577638e154ac1648358bff205b80028d3680f8ee6583dfbdb85a6a58e62446`.
4. **Offline Showcase HTML (`scripts/build_out_of_domain_showcase_html.py --profile r3`)**:
   - Output: `external_artifacts/out_of_domain_factory_r3_20261113/out_of_domain_hero_showcase_r3_20261113.html`
   - Size: `130735689` bytes (`124.68 MB`), `62` inline lossless PNGs, `3` inline H.264 MP4s, `external_urls=0`
   - SHA-256: `6f98d43af1c4f7abf882ac9c8d9eca52ce22f37188fce1dfba2a9864e1896a31`

## Standards Maintenance Block

- **规范依据**：规范基线提交 `ea731f372a6ccb2cb7cb10d5da52bbf5ffe0726d` 及 [docs/standards/README.md](../standards/README.md)。
- **涉及规则**：新增 `GEN-008`（[docs/standards/asset-generation.md](../standards/asset-generation.md#gen-008)），同步关联 `GEN-001..007`、`ART-005`、`USD-008`、`VAL-001`、`VAL-002`。
- **变化**：
  1. 在 [docs/standards/asset-generation.md](../standards/asset-generation.md) 正式新增强制规则 **`GEN-008`（精细铰接主设备九道门禁与双层视觉验收：`G1..G8 + G9a + G9b`）**，将结构/拓扑/物理门禁（含 `PhysxRigidBodyAPI`/`PhysxArticulationAPI` 显式 schema 与串联关节 BFS 拓扑序）与双层视觉验收（`G9a` 客观非纯盒/PBR 分化/UI 纹理硬底线 + `G9b` 独立 Critic Agent 锚定盲审 $\ge 8.0/10$ 有界返修闭环）固化为交付要求，同时保持 `GEN-007` 四层证据隔离（`robot_integration` 留给下游 `Astra`）；
  2. 在 [docs/standards/articulation.md](../standards/articulation.md)（`ART-005`）补充串联关节 BFS 顺序与显式 PhysX schema 交叉引用；
  3. `ebench` 7 视角预览对闭合吊顶/入户门扇的临时相机遮挡剔除属于预览渲染适配层增强，不改变 `USD-*` 场景结构或物理契约。
- **验证**：
  - 纯包检查：`CHECK_PYTHON=/cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-py310/bin/python make check` 全绿（`1250 passed, 11 skipped`，`ruff` 0 错误，Phase 10.x `passed`）；
  - 资产 10 门禁：`ika_acceptance_summary_v2.json`（`30/30 PASS`，含 `@visual-critic` 独立盲审报告）；
  - 三间 `r3` 房间准入与合成闭环：`ConvertAsset`（`isaac41` `static,runtime`）`3/3 pass`、`run_out_of_domain_scene_gate.py` `3/3 pass`、`verify_genmanip_predicate_canary.py --profile r3` `3/3 pass`（`0.00 -> 1.00`，120 帧漂移 $\le 1\times 10^{-6}\text{ m}$）、合成 Isaac Sim 4.1 RTX 盲审 `3/3 PASS`（最低单项 $\ge 8.8$）。
- **限制或例外**：遵循 `GEN-007` 与 `VAL-001`，`robot_integration` 显式标为 `NOT_TESTED_DELEGATED_TO_ASTRA`；不在编译器仓内宣称机器人闭环策略成功率。
- **同步内容**：[docs/standards/asset-generation.md](../standards/asset-generation.md)、[docs/standards/articulation.md](../standards/articulation.md)、[docs/standards/README.md](../standards/README.md)、[docs/standards/templates/asset-spec-template.md](../standards/templates/asset-spec-template.md)、[docs/operations/generate-articulated-asset.md](../operations/generate-articulated-asset.md)、[skills/README.md](../../skills/README.md)、[skills/hunyuan-isaac-articulation-assets/](../../skills/hunyuan-isaac-articulation-assets/SKILL.md)、[external_artifacts/README.md](../../external_artifacts/README.md) 及本记录。
