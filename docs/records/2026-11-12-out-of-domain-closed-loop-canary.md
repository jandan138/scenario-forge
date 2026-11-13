# 2026-11-12 Out-of-Domain Agentic Scene Factory & Multi-DOF Articulated Canary Record

## Summary

Executed and verified an end-to-end generalization of `scenario-forge` beyond `scientific_workbench` into **three out-of-domain tabletop themes** (`specialty_coffee_bar`, `electronics_qa_station`, `modern_office_print_hub`), aligned capability-by-capability against NVIDIA's agentic simulation stack (**SAGE + Scenethesis + Isaac Lab-Arena + SimReady**). Each task authors a manufacturer-grounded, multi-DOF articulated hero machine (`GEN-001..007`, `ART-001` fixed-base v2), pairs it with a newly generated `Code-as-Room` (`room-source-v2`) themed room, solves tabletop layout with multi-DOF sweep-volume clearance + automated Critic conflict repair, compiles a hash-locked GenManip collected package, and passes **Critic 1 cold-reset physics settling + `t=0` zero-false-positive audit**, **Multi-Stage State-Teleport `MetricsManager` Predicate Canary (`0.0 -> 1.0`)**, and **Critic 2 7-view RayTraced visual gate (`v0.3`)** inside Isaac Sim `4.1` (`2023.1.1`).

---

## Standards Maintenance Block (`docs/standards/maintenance.md`)

- **规范依据**：基线提交 `ea731f3` (`docs: record task09 and task10 limits in the scene standards`)；适用规则见 [docs/standards/README.md](../standards/README.md)。
- **涉及规则**：`GEN-001..007`（资产生成与尺寸证据表）、`ART-001`（固定底座多自由度铰接 v2 契约）、`USD-008`（非凸功能腔体复合碰撞体禁单凸包封口）、`LAY-001`（台面 10 cm 边距与朝向机器人主操作区）、`VAL-001` / `VAL-002`（包锁校验、7 视角渲染证据与双阶段运行验证）。
- **变化**：**规范无需变更**。原因：既有 `GEN-001..007`、`ART-001`、`USD-008`、`LAY-001` 与 `VAL-001` 在不改任何规范条文的前提下直接泛化至商业咖啡吧（`NespressoCreatistaPlus` 3-DOF）、SMT 电子质检工位（`IngunMA2111Fixture` 3-DOF）与现代办公文印中心（`BrotherMFCL2820DW` 2-DOF 正交滑轨+翻盖）三大非湿实验主题；本次新增能力属于纯 Python 关系布局求解扩展（`relational_solver.py`、`spec_composer.py`）、`skills/agentic-scene-factory/` 编排技能与两处 EBench/GenManip 适配器实现缺陷修复（见下文）。
- **验证**：
  - 单元与契约门禁：`CHECK_PYTHON=/cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-py310/bin/python make check`（全量测试、`ruff`、边界导入检查通过）。
  - 房间准入证据：`external_artifacts/out_of_domain_factory_20261112/rooms/rooms_admission_summary.json`（3 个 `Code-as-Room` `room-source-v2` 房间全部通过 `ConvertAsset` `isaac41` `visual_static_environment` 准入）。
  - 资产准入证据：`external_artifacts/out_of_domain_factory_20261112/assets/qualification_summary.json`（3 台多自由度英雄设备通过 `check_articulation_usd.py --mode fixed` + `ConvertAsset` `isaac41` 运行时晋升 + Cycles `AgX` 渲染审查；6 个刚体任务件与 3 个桌面背景件全部通过 `ConvertAsset` 准入）。
  - Critic 自动修场景轨迹：`external_artifacts/out_of_domain_factory_20261112/critic_repair_trace.json`（`modern_office_brother_calibrate` 第 1 轮检出 `paper_cassette_pullout` 抽屉行程走廊侵占 `infeasible`，第 2 轮自动迁移 `a5_media_pack` 至左侧后 `solved`）。
  - Critic 1 物理静置 + 多阶段状态瞬移谓词金丝雀：`external_artifacts/out_of_domain_factory_20261112/predicate_canary_summary.json`（3 个任务 120 帧零动作重置最大漂移 `<= 1e-6 m`、`t0_score == 0.0`，分阶段单调推进至 `final_score == 1.0`）。
  - Critic 2 7 视角光线追踪视觉门禁：`external_artifacts/out_of_domain_factory_20261112/scene_gate_summary.json`（21 张 `1920x1080` `RayTracedLighting` 图像全部通过 `validate_genmanip_preview_evidence` `visual_ready_gate.yaml`）。
- **限制或例外**：
  - 双臂 `lift2` 逆运动学（IK）与无碰撞操作轨迹规划明确不在 `scenario-forge` 仓内执行（遵守 `AGENTS.md` 硬边界），由下游特权世界轨迹求解器 `Astra`（*Embodied First Exam* §2.1 & Appendices C/G）消费导出的 `collected_package` 完成。
  - `BrotherMFCL2820DW` 因机身进深 `399 mm` 叠加前向抽屉拉出行程 `180 mm`，在 `800 mm` 深工作台上需采用 `y = +0.090 m` 跨中心线摆位，已在 `ScenarioSpec` 中按契约显式声明 `tabletop_placement_exception` 以确保拉出态前端（`-0.292 m`）与机身后端（`+0.2895 m`）同时满足 `>= 0.10 m` 台面边距。
- **同步内容**：
  - 架构设计：[docs/design/agentic-out-of-domain-scene-factory.md](../design/agentic-out-of-domain-scene-factory.md)
  - 英雄铰接资产规格：[nespresso-creatista-plus-bne800.md](../design/asset-specs/nespresso-creatista-plus-bne800.md)、[ingun-ma-2111-pcba-fixture.md](../design/asset-specs/ingun-ma-2111-pcba-fixture.md)、[brother-mfc-l2820dw-printer.md](../design/asset-specs/brother-mfc-l2820dw-printer.md)
  - Agent 技能：`skills/agentic-scene-factory/SKILL.md`、`skills/agentic-scene-factory/references/critic-rubric-and-loop.md`
  - 源绑定与任务包配置：`configs/source_bindings/out_of_domain_hero_20261112.yaml`、`configs/out_of_domain_tasks/*.yaml`、`configs/domain_packs/{specialty_coffee_bar,electronics_qa_station,modern_office_print_hub}/layout_constraints.yaml`

---

## 1. Admitted `Code-as-Room` (`room-source-v2`) Environments

| Task ID | Domain | Room ID | Asset ID | ConvertAsset Manifest SHA-256 | Status |
|---|---|---|---|---|---|
| `specialty_coffee_bar_creatista_prep` | `specialty_coffee_bar` | `kitchen_coffee_bar_v1` | `out_of_domain_env_kitchen_coffee_bar_v1` | `3259c030ceb7cde0c37fd8bbd62c91863e13baa839c59e0dca8ba331fbcdd743` | `pass` |
| `electronics_qa_ingun_probe_lock` | `electronics_qa_station` | `smt_qa_workshop_v1` | `out_of_domain_env_smt_qa_workshop_v1` | `f02c1b7fc828eb0e9b58c86d6538d99fc8531f4f82d1862301534baa5c1b8fdf` | `pass` |
| `modern_office_brother_calibrate` | `modern_office_print_hub` | `office_print_studio_v1` | `out_of_domain_env_office_print_studio_v1` | `bedcdcd9e0421d464360786c925d12d4e82f69862de943ff7550c0a03a179c25` | `pass` |

---

## 2. Qualified Hero Articulated Appliances & Companion Assets

### 2.1 Multi-DOF Hero Articulated Machines (`articulated_object`)

| Asset ID (`slug`) | Grounded Envelope ($W\times D\times H$) | DOFs & Functional Cavity (`USD-008`) | Raw Source SHA-256 | Runtime Report SHA-256 | Final Manifest SHA-256 |
|---|---|---|---|---|---|
| `NespressoCreatistaPlus` (`nespresso-creatista-plus-bne800`) | $171 \times 393 \times 308\text{ mm}$, $5.2\text{ kg}$ (Breville BNE800 E-grade) | 3-DOF: `brew_lever` Rev-$X$ $[-75^\circ, 0^\circ]$, `drip_tray` Pris-$Y$ $[-0.045, 0\text{ m}]$, `select_dial` Rev-$Y$ $[0^\circ, +90^\circ]$; open $46\times 48\text{ mm}$ 5-box capsule chute | `3f426cdea1fc7ee69e85a53627c558d0a0bc053fa984f36083953bd9c25d9fda` | `0364a986663abab8e53886920156286026b269ee22267128facbc350cc9608cf` | `03ab59bf61f00fab25650d0d6645adb551e4ca85a56cf78422bd92d1b56674f3` |
| `IngunMA2111Fixture` (`ingun-ma-2111-pcba-fixture`) | $320 \times 515 \times 270\text{ mm}$, $9.3\text{ kg}$ (INGUN MA 2111 Item 31730 E-grade) | 3-DOF: `pressure_hood` Rev-$X$ $[-70^\circ, 0^\circ]$, `clamp_lever` Rev-$X$ $[-95^\circ, 0^\circ]$, `mode_toggle` Rev-$X$ $[-25^\circ, +25^\circ]$; recessed $112\times 92\text{ mm}$ 4-rail PCBA nest | `28538e5829644128a079b53dc19081c1e39f9be9d5316899e8726ecb3d5e9389` | `9e8f006d2d888eba254b8b16fbd3bbde4921cd6ab44c70c3db7cd060532ccd94` | `c1771f0e5a570d4e16f148bdb68159bf5052067ce37f911d30ab6d8129490b49` |
| `BrotherMFCL2820DW` (`brother-mfc-l2820dw-printer`) | $410 \times 399 \times 319\text{ mm}$, $11.56\text{ kg}$ (Brother MFC-L2820DW E-grade) | 2-DOF orthogonal: `paper_cassette` Pris-$Y$ $[-0.180, 0\text{ m}]$ (`damping=200`), `scanner_lid` Rev-$X$ $[-70^\circ, 0^\circ]$; hollow lower `Base` tunnel + 5-box `PaperCassette` tray + `PlatenGlass` | `04928171ac2a47b3528d5a914bd50c406bbbe5b2fa1428cdcf5a3bcebeb7b259` | `0cbd9a4f7ae14aa371837e475a5c0fd55e534109b1de0af8442905422f61f48d` | `c8125e7bbeef95f5c87e24df0c30cd20e45c5fc0744076f26914840c22926ca4` |

### 2.2 Rigid Task & Context Objects

| Asset ID | Slug | Role | Final Manifest SHA-256 |
|---|---|---|---|
| `EspressoCup` | `espresso_cup` | `rigid_object` | `368fd51072dd5b260c4f092d13d1ad030398c46dc6312ac2d112b77ade677361` |
| `CoffeeCapsule` | `coffee_capsule` | `rigid_object` | `dfe0bc0954626600f1754033a7453bd6995c493aca77b3f499c72de6cb432a48` |
| `MilkPitcher` | `milk_pitcher` | `dynamic_context_object` | `d96180197382523f8f3fb6dfa2d974ed8b6ececc3150ae367895f9c55125f8c0` |
| `PCBACarrierBoard` | `pcba_carrier_board` | `rigid_object` | `d79cf10e7dff601a70444ab1d879752b96db8b65b115ada670cd7cbc07d8e699` |
| `ESDTray` | `esd_tray` | `rigid_object` | `42a34c1dad861ef76a9dbdb7ff34b9c46577941ec0b13e3ffc806118eaac4e7f` |
| `BenchMultimeter` | `bench_multimeter` | `dynamic_context_object` | `638af40e3b9c1de0f248d8fddbf046159138f94a7448ff9dcb1ea63ecc885d3a` |
| `A5MediaPack` | `a5_media_pack` | `rigid_object` | `710ae25c6eb5b38a2683a97528675d0655d3e99d7c1287c1e130c5a30a4b30a9` |
| `CalibrationSheet` | `calibration_sheet` | `rigid_object` | `9853c6f1bd22da39f156efe5238912863eb719360e6fe2ed92386eb36cb60452` |
| `OfficePenOrganizer` | `office_pen_organizer` | `dynamic_context_object` | `2d979014c66e303eab0ab12b584844b85f658ec6f0cc172d85c6a9f8634f13c1` |

---

## 3. Closed-Loop Runtime Verification Results

### 3.1 Automated Kinematic-Sweep Critic Repair (`critic_repair_trace.json`)
- **Scenario**: `modern_office_brother_calibrate` (`seed: 303`)
- **Iteration 1 (Unrepaired)**: Placed `a5_media_pack` at `[0.0, -0.20]` (`in_front_of` `brother_printer`). `solve_relational_tabletop_layout` rejected the layout (`status: "infeasible"`) with structured conflict `kinematic_clearance_intrusion` on `paper_cassette_pullout` (`joint: paper_cassette`, world corridor `x: [-0.145, 0.145], y: [-0.292, -0.1095]`).
- **Iteration 2 (Repaired)**: Critic applied `relocate_out_of_kinematic_corridor`, moving `a5_media_pack` to `region: left` (`left_of` `brother_printer`, solved at `[-0.415, -0.152, 0.757]`). Solver converged cleanly (`status: "solved"`, `conflicts: []`).

### 3.2 Critic 1 Physics Settling + Multi-Stage Predicate Canary + Critic 2 Visual Gate

| Scenario ID | Critic 1 120-Step Max Drift | `t=0` Score | Stage Score Progression | Final Score | Canary Report SHA-256 | Critic 2 7-View Gate |
|---|---|---|---|---|---|---|
| `specialty_coffee_bar_creatista_prep` | `0.000000 m` | `0.0` | `0.2 -> 0.4 -> 0.6 -> 0.8 -> 1.0` | `1.0` | `sha256:a8d0c3b11f03ecf215810b0aaaa2d7af5981a0fb124c89329d961c74ae9b5283` | `passed` (7/7) |
| `electronics_qa_ingun_probe_lock` | `0.000001 m` | `0.0` | `0.25 -> 0.5 -> 0.75 -> 1.0` | `1.0` | `sha256:f7633ec73d12f621c10ff72e22f56727292659a3c951d36733b2a1aa0c6f4b29` | `passed` (7/7) |
| `modern_office_brother_calibrate` | `0.000000 m` | `0.0` | `0.25 -> 0.5 -> 0.75 -> 1.0` | `1.0` | `sha256:125e334913bf60194be2a095bd2d4f2b623e104dab6b107c20787c624076142a` | `passed` (7/7) |

---

## 4. Real Adapter & Task-Design Bugs Caught by Closed-Loop Execution

Running full compilation $\rightarrow$ Isaac Sim `4.1` physics $\rightarrow$ `GenManip` `MetricsManager` $\rightarrow$ 7-view RayTraced preview caught three high-impact defects that static schema checks alone could not detect:

1. **GenManip `ArticulationView` 4-Level `status` Nesting (`src/scenario_forge/adapters/ebench/genmanip.py`)**:
   - GenManip's `ArticulationView.get_joints_state().positions.tolist()` returns shape `(1, num_dofs)`, so `check_subgoal_finished_articulation` requires `"status": [[candidate]]` (4 nested lists). Previously `genmanip.py` exported `"status": [candidate]` (3 nested lists), causing joint-band predicates to fail silently in live `MetricsManager` evaluation. Fixed via TDD (`tests/test_ebench_genmanip_export.py`).
2. **`t=0` Partial-Credit Leak in Conjunctive Stage-0 Clauses (`electronics_qa_ingun_probe_lock.yaml`, `modern_office_brother_calibrate.yaml`)**:
   - GenManip's `MetricsManager.calc_overall_score()` averages leaf predicate booleans inside an incomplete conjunction (`mean([0.0, 1.0]) / 4 = 0.125`). When `pcba_carrier_board` or `a5_media_pack` started at `yaw_offset_deg: 0.0`, its `x`-axis alignment clause (`sr_based_genmanip_axis_align`) was already `True` at `t=0`, granting `0.125` score to a zero-action policy. Rotating initial workpiece placements to `yaw_offset_deg: 90.0` eliminated all `t=0` partial credit (`t0_score == 0.0`) and enforced genuine $90^\circ$ wrist re-orientation during manipulation.
3. **`Code-as-Room` `room-source-v2` CamelCase Perimeter Wall Roots (`src/scenario_forge/adapters/ebench/preview.py`, `scripts/ebench/render_genmanip_initial_preview.py`)**:
   - `Code-as-Room` `v2` names perimeter wall Xforms `WallNorth`, `WallSouth_0..1`, `WallSide_0..1` rather than `Wall_*`. Extending `_COMPLETE_WALL_ROOT_NAME` enabled two-wall cutaways for `room_corner_a` / `room_corner_b` and clean doorway framing for `room_entrance_eye_level` while preserving `WallShelf_*` furniture. Fixed via TDD (`tests/test_ebench_genmanip_preview.py`).

---

## 5. Multi-Stage RayTraced Canary Media & Self-Contained Offline HTML Showcase

To provide zero-dependency visual proof of multi-stage physical feasibility (non-convex cavity seating, `32 N` passive rail transport into the hollow lower printer tunnel, and live `MetricsManager` score progression), `scripts/render_out_of_domain_canary_media.py` recorded 16 lossless `1920x1080` `RayTracedLighting` stage keyframes + 3 `1280x720` `30 fps` `h264`/`yuv420p` reels, and `scripts/build_out_of_domain_showcase_html.py` assembled the single-file offline review showcase (`tests/test_out_of_domain_showcase_html.py`):

- **Self-Contained HTML Showcase**: `external_artifacts/out_of_domain_factory_20261112/out_of_domain_hero_showcase_20261112.html`
  - Size: `60,896,779` bytes (`58.08 MB`)
  - SHA-256: `sha256:34a8f3e93b37b2d4745b6bd7043b078417b8587b3b393ee79420edb8b8b8178a`
  - Audit (`out_of_domain_hero_showcase_manifest.json`): `external_url_count = 0`, `png_data_uri_count = 46` (deduplicated lossless `MEDIA_MAP`: 9 Cycles studio views + 21 7-view 1080p initial-scene renders + 16 1080p Canary stage keyframes), `mp4_data_uri_count = 3`.
- **Per-Scenario Canary Progression Reels (`showcase_media/canary_media_summary.json`)**:
  - `specialty_coffee_bar_creatista_prep`: 6 lossless 1080p keyframes (`0.0 -> 0.3 -> 0.5 -> 0.6 -> 0.8 -> 1.0`), 286-frame H.264 MP4 (`766,449` bytes, `sha256:fb5ea668af8fa25455efb941b0a72e764703853bf8986cf088184c72c278d2b9`), contact sheet `sha256:07546468bef5404fb4cdb293bd1f11a53ae86e0d9486d92ffa50dcebcbcf9484`.
  - `electronics_qa_ingun_probe_lock`: 5 lossless 1080p keyframes (`0.0 -> 0.25 -> 0.5 -> 0.75 -> 1.0`), 232-frame H.264 MP4 (`620,698` bytes, `sha256:dbd39cbbf26c3cc1146d69b33b6ae08a85c5bde22ec2c4c977063ef2d0e31875`), contact sheet `sha256:1d8165f3f264230928cbb1c65824ee3e906c035553640105e9e28830f2d6d110`.
  - `modern_office_brother_calibrate`: 5 lossless 1080p keyframes (`0.0 -> 0.25 -> 0.5 -> 0.75 -> 1.0`), 252-frame H.264 MP4 (`701,709` bytes, `sha256:595e72efe2eb127544b78782fb273764dad874df36ac6686295c3a8ff88862c7`), contact sheet `sha256:c12e5fe42b8f582ed6e6d93c31986f8df568b75ffbe94989be2dd7c38b987db4`.
- **Headless Isaac Sim `4.1` Rendering Notes**:
  - `omni.isaac.sensor.Camera` with `frequency > 0` gates `_current_frame["rgba"]` updates on `sim_time` advancing; setting `camera._frequency = -1` and reading `_rgb_annotator.get_data()` guarantees fresh frames across both render-only kinematic arcs and live PhysX settling steps.
  - Defining interior ceiling `UsdLux.SphereLight` fixtures (`z = 2.60..2.80 m`) after physics warmup prevents enclosed `room-source-v2` ceilings/walls from occluding exterior `DomeLight` rays under headless `RayTracedLighting`.
