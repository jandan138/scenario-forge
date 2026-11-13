# Internalized Room Exporter, Out-of-Domain `r4` Freestanding Worktables & Single-Image Real-to-Sim Workstation Record

- **Date**: 2026-11-13
- **Artifact Roots**:
  - `external_artifacts/out_of_domain_factory_r4_20261113`
  - `external_artifacts/real2sim_office_desk_20261113`
- **Configs**:
  - `configs/source_bindings/out_of_domain_hero_r4_20261113.yaml` (`sha256:4c2ff2c6a5be0c2bae3e1c2631ed0fbbcfda607297c0575754f6d0d822e9ec28`)
  - `configs/out_of_domain_tasks_r4/specialty_coffee_bar_creatista_prep.yaml`
  - `configs/out_of_domain_tasks_r4/electronics_qa_ingun_probe_lock.yaml`
  - `configs/out_of_domain_tasks_r4/modern_office_brother_calibrate.yaml`
  - `configs/domain_packs/real2sim_open_office/layout_constraints.yaml`
  - `configs/source_bindings/real2sim_office_desk_r1_20261113.yaml` (`sha256:b40d9643d59b0193c08fb86e87b7d1b0a2dcddf873eb47227efce6447510cd0c`)
  - `configs/real2sim_tasks_r1/real2sim_office_desk_riser_organize.yaml` (`sha256:b1c92d480d98c1191a0768d4ec6f1587f8c2a49b3d6d3bcd7a356d9d59bdafc4`)

## 1. Workstream 1 — Internalized `scenario-forge` Room Toolchain & Validator Contracts

1. **Zero-External-Dependency `room-source-v2` Exporter**:
   - Internalized `skills/agentic-scene-factory/scripts/export_room_source_v2.py` and `skills/agentic-scene-factory/scripts/verify_and_render_room_pack.py` so every room source delivery carries `producer.repo = "scenario-forge"` with `0` references to any external `Code-as-Room` repository path.
   - Added pure-Python validator contracts in `src/scenario_forge/adapters/`:
     - `room_support_relations.py` (`tests/test_room_support_relations.py`)
     - `spatial_pose_grounding.py` (`tests/test_spatial_pose_grounding.py`)
     - `texture_twin_ledger.py` (`tests/test_texture_twin_ledger.py`)
   - Extended `src/scenario_forge/adapters/generated_environment.py` to accept native `scenario-forge` `room-source-v2` deliveries while preserving backwards compatibility with historical `Code-as-Room` intakes.

## 2. Workstream 2 — Out-of-Domain `r4` Native Rooms & Freestanding 4-Legged Worktables (`GEN-009`)

1. **Native `r4` Room Re-Exports & `ConvertAsset` (`isaac41`) Admission**:
   - Summary: `external_artifacts/out_of_domain_factory_r4_20261113/rooms/rooms_admission_summary.json` (`sha256:0d1fcbcb6a7571a102a1394b35f451d5eff7aa0cc1846459503eddfce819d748`, `code_as_room_references = 0` across all 3 rooms):
     - `kitchen_coffee_bar_v2`: manifest `sha256:99c38fb9f0246644a14732020ca7f9fd2ab1775dab8b3db4b4276131e41d44b7`
     - `smt_qa_workshop_v2`: manifest `sha256:6cb812bbda075bc50cda5b157e8954cda98d32bb70d505c38a9c28159f4c8270`
     - `office_print_studio_v2`: manifest `sha256:c6847411c85940df066ba83d706cfe7ee25c5c12f02e68fa719293ffca514e27`
2. **Three Freestanding 4-Legged Domain Worktables (`2.000 × 0.800 × 0.755 m`, `min_z = 0.000 m`)**:
   - Replaced the legacy floating `Z ∈ [0.71, 0.75] m` solid gray slab with domain-specific floor-grounded worktables (`tables/tables_qualification_summary.json` `sha256:f37f0ff7a370ee277dfe8fa1ffa40e6824cb548d4ca0e9726353bb233d2143f8`; independent Critic report `tables/renders/tables_visual_critique_report.json` `sha256:7b4d5433b9c38cbd3a6f7238178a993d7453c087737da7742c766a98a5f1bdae`, `min 9.0/10`):
     - `CoffeeBarOakSteelTable`: manifest `sha256:214296817b2debff524ef12d2e1d9bbf10a6e1ffe1276300b4cadee5e6f55bef`
     - `SmtEsdAluminumBenchTable`: manifest `sha256:c3e109aee7fb69ce5f0062938bfdc83924a29b9877d8cfbc7300fc3f8d702e58`
     - `OfficeBirchSteelTable`: manifest `sha256:c97f6066486d011b776444f4c043dae903b795bed5820f78255fe9e796821206`
3. **`r4` Scene Gate, Predicate Canary & Composed Isaac Sim 4.1 RTX Blind Review (`3/3 PASS`)**:
   - `scene_gate/scene_gate_summary.json`: `sha256:89ceede0ddde7fc0eb4443065c02713ce41f8947203d1b6f9cbea5bdc067f0cf` (`3/3 PASS`)
   - `canary/predicate_canary_summary.json`: `sha256:cc5be6d7395a88af1e9be42e9b638b2fc422a60f3393fad681d6ed1453997675` (`0.00 -> 1.00` across `6 / 5 / 5` stages, `critic1_max_translation_drift_m = 0.0 m`)
   - `media/canary_media_summary.json`: `sha256:ee89c9ab9ad01092a378f4da31ba7bffeb1c1d91ab8aeca66131dd7953e88a4d` (`314 / 260 / 285` H.264 720p frames + 19 lossless 1080p keyframes)
   - `media/rtx_composed_critique_report.json`: `sha256:cd5837a8755001885ccf57732ee5bd56bb33f314a7dfd08b86642cfbb70543fe` (`@critic-r4` Round-1 `PASS`, `min 8.9/10`, means `9.08 / 9.18 / 9.18`)

## 3. Workstreams 3 & 4 — Single-Image Real-to-Sim Open-Office Workstation (`GEN-010`)

1. **Ground-Truth Evidence, Multi-Anchor Spatial Grounding & 1:1 Texture Twin Ledger (`19/19 PASS`)**:
   - Ground-truth photograph: `external_artifacts/real2sim_office_desk_20261113/evidence/source_photo.jpg` (`4096 × 3072`, EXIF `17 mm` 35mm-equiv, `sha256:9a7d1149de9eb9aa852401ba53271f374f44b25e3e88f0743961f51811ecd195`)
   - Multi-anchor spatial pose grounding: `spatial_grounding/workstation_pose_grounding.json` (`sha256:7d580dbad44ef26ba612d335ff03038db0e218e708eeee56450a0eee7f8b4087`)
   - 19-surface 1:1 Texture Twin Ledger: `ledger/ledger_manifest.json` (`sha256:64ea562f64c7b9f7531cb31c10a7c1657bf539031abfd63ef736d384d7d085b5`, `max ΔE_ab = 0.3884 <= 8.0`) & `@critic-r4` Round-2 `PASS` `ledger/patch_critique_report.json` (`sha256:a0f5bb15ea699b0f06dcf28684a4513f80df5d98806d9c04ec23501f1eb90678`, `19/19 >= 8.4/10`, mean `9.04/10`)
2. **Native Open-Office Bay Room (`real2sim_open_office_bay_v1`) & Standing Desk + 11 Props**:
   - `room/room_admission_summary.json`: `sha256:74ea86a3086874649eb3519f9f9bf41fe49243cb88e1c3b60106180e2add04f3` (manifest `sha256:593f73c72c2d87ff2221e737f9a35c9b1d05df177e77204850e63c4acf46f0bd`)
   - `room/renders/room_visual_critique_report.json`: `sha256:2ac4323281b5fd0ac1c82b822c00792e4f231f920aa7a36e8b216c0271bf9ef9` (`min 8.9/10, mean 9.12/10`)
   - `desk_and_props/qualification_summary.json`: `sha256:f3d69a6544df26528a5b706f52c8965de5af8d366201d560ac5d0e86b7d060cb` (`Real2SimBunchStandingDesk` exact `/World/table` `Z ∈ [0.000, 0.750] m`, manifest `sha256:a0859a5ca903fe5cb0f7abbc5383ae66cafba5e650d4c999fa6ffcfd9c6f89a0`, plus 11 qualified rigid & context props)
3. **3-DOF Articulated Hero `DesktopDualDrawerRiserRig` (`GEN-008` `10/10 PASS`)**:
   - `hero_rig/assets/ika_grade_acceptance/ika_acceptance_summary.json`: `sha256:e506001ee450b7fbe939703f01ca70f01ad0f176cea3aa92857642a0aa79818f` (`10/10 PASS`, `drawer_left` + `drawer_right` `[0, +165 mm]` 5-wall hollow drawers + `laptop_lid_hinge` `102°` Acer laptop)
   - `ConvertAsset` (`isaac41`) final manifest: `sha256:569879c3393b7f885411261346fb5d20a68fc9460d85b95ee51a866a41d02718`
   - `G9b` blind critique `hero_rig/critique/desktop-dual-drawer-riser-rig_visual_critique_report.json`: `sha256:3419b37ecec94dbdee5afbd218c82c77a79d36580e5cc955e3675ae3f10b777a` (`min 9.0/10, mean 9.18/10`)
4. **Camera-Matched Reprojection, Scene Gate, 5-Stage Canary & Composed Isaac Sim 4.1 RTX Blind Review**:
   - Cycles camera-matched reprojection board `spatial_grounding/reprojection_comparison_board.png` (`sha256:0d4d012401fd16503941babf7ae11d2e0ee671c32bef2f828cfec59bf236ad2c`) & Round-2 critique `spatial_grounding/reprojection_critique_report.json` (`sha256:fa7fadaa3514c0d2b55426a47b2d77bc90464cadfab18eef098b2cf1a62d1e2a`, `min 8.7/10, mean 8.95/10`, `mean_delta_e_ab = 5.43`, `edge_iou = 0.2390`)
   - `scene_gate/scene_gate_summary.json`: `sha256:94dba9d136aeb2cd2252f52b6a1381313756ba5a01816f6c0e0a747fd1bba609` (`1/1 PASS`)
   - `canary/predicate_canary_summary.json`: `sha256:fd92a5a9596393a010d7daac83d37147d137dfc9edd02d35fb301f3f07921ef8` (`0.00 -> [0.2, 0.4, 0.6, 0.8, 1.0]`, 120-frame settling drift `7e-06 m = 0.007 mm`)
   - `media/canary_media_summary.json`: `sha256:fad2d6509c9a6209e5aef41015713155fb4619de9c075c989fa6479aedad9b86` (6 lossless 1080p keyframes + 298-frame 720p H.264 `progression.mp4` `sha256:03afd9c67894a5ee33a9f6b76e59ca89f2344791f08d23fe5ca3fa3e01c3d04e`)
   - RTX camera-matched reprojection board `media/rtx_reprojection_comparison_board.png` (`sha256:4b5a04469519bd543e3885d18a9970142246d15f6e47d0436d8ed3a2bed1eadc`, `edge_iou = 0.2483`, `mean_delta_e_ab = 8.8593`)
   - Composed RTX blind critique `media/rtx_composed_critique_report.json`: `sha256:5fad71a7a453d7067775cc782c0db710d52cb2ebb2d907486183d982feab2509` (`@critic-r4` `PASS`, `min 8.9/10, mean 9.10/10`)

## 4. Workstream 5 — Unified 4-Scenario Self-Contained Offline HTML Showcase (`external_urls == 0`)

- Output: `external_artifacts/out_of_domain_factory_r4_20261113/out_of_domain_and_real2sim_showcase_r4_20261113.html`
- Size: `262798095` bytes (`250.62 MB`), `118` inline lossless PNGs, `4` inline H.264 MP4s, `external_urls = 0`, external `Code-as-Room` path refs = `0`
- HTML SHA-256: `71f3e2a71a3c4bb26b58abe3f120d473a45962227f8ee414588e001eb37457c8`
- Manifest JSON: `external_artifacts/out_of_domain_factory_r4_20261113/out_of_domain_and_real2sim_showcase_r4_manifest.json` (`sha256:2b2d8cc54233f892ab24343e9003aca23dc0e1738f5a2596de0eb8178c769737`)

## Standards Maintenance Block

- **规范依据**：规范基线提交 `ea731f372a6ccb2cb7cb10d5da52bbf5ffe0726d` 及 [docs/standards/README.md](../standards/README.md)。
- **涉及规则**：新增 `GEN-009`、`GEN-010`（[docs/standards/asset-generation.md](../standards/asset-generation.md#gen-009)），同步关联 `GEN-002`、`GEN-007`、`GEN-008`、`USD-008`、`VAL-001`、`VAL-002`。
- **变化**：
  1. 在 [docs/standards/asset-generation.md](../standards/asset-generation.md) 正式新增强制规则 **`GEN-009`（落地结构支撑台面与内化房间环境导出契约）**，禁止主操作台退化为悬空纯灰顶板（要求 `min_z = 0.000 m ± 2.0 mm` 真实触地桌腿、前侧机器人净空、以及 `/World/table` 运行时最高包络 `max_z == surface_z_m ± 1.0 mm` 不被高于台面的装饰屏风抬升），并将 `room-source-v2` 房间导出工具链完全收敛至本仓 `skills/agentic-scene-factory/scripts/export_room_source_v2.py`（零外部 `Code-as-Room` 路径依赖）；
  2. 在 [docs/standards/asset-generation.md](../standards/asset-generation.md) 正式新增强制规则 **`GEN-010`（单图真实工位数字孪生：空间解算、1:1 材质账本与同机位重投影门禁）**，要求多基准件锚定三维位姿与刚体碰撞盒零初始穿透核验（对齐 `GEN-002`）、逐面 `Texture Twin Ledger` 三联比对盲审、以及 `[Source Photo | Virtual Render | 50% Edge Overlay]` 同机位重投影比对门禁，同时严格保持 `GEN-007` 四层证据隔离；
  3. 在 [docs/operations/intake-generated-blender-environment.md](../operations/intake-generated-blender-environment.md) 同步自包含 `export_room_source_v2.py` 生产者交付入口说明。
- **验证**：
  - 纯包检查：`CHECK_PYTHON=/cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-py310/bin/python make check` 全绿（`pytest` + `ruff` + Phase 10.x 全通过）；
  - `r4` 三场景闭环：3 套内化房间 + 3 张落地四腿工作台全部通过 `ConvertAsset`（`isaac41`）准入、`run_out_of_domain_scene_gate.py` `3/3 PASS`、`verify_genmanip_predicate_canary.py --profile r4` `3/3 PASS`（`0.00 -> 1.00`，120 帧漂移 `0.000 m`）、`@critic-r4` 合成 RTX 盲审 `min 8.9/10`；
  - `Real-to-Sim` 真实工位闭环：19 组贴图孪生账本 `19/19 PASS`（`max ΔE_ab = 0.3884`）、`DesktopDualDrawerRiserRig` `GEN-008` `10/10 PASS`（`min 9.0/10`）、Cycles/RTX 双渲染同机位重投影（`edge_iou = 0.2390 / 0.2483`）、`run_out_of_domain_scene_gate.py` `1/1 PASS`、`verify_genmanip_predicate_canary.py --profile real2sim` `1/1 PASS`（`0.00 -> 1.00`，120 帧漂移 `0.007 mm`）、`@critic-r4` 合成 RTX 盲审 `min 8.9/10`。
- **限制或例外**：遵循 `GEN-007` 与 `VAL-001`，`robot_integration` 显式标为 `NOT_TESTED_DELEGATED_TO_ASTRA`；谓词金丝雀验证初始 120 帧物理稳态、非凸腔体承重与 `MetricsManager` 顺序判分，不在本编译器仓内宣称自主机器人策略成功率。
- **同步内容**：[docs/standards/asset-generation.md](../standards/asset-generation.md)、[docs/standards/README.md](../standards/README.md)、[docs/operations/intake-generated-blender-environment.md](../operations/intake-generated-blender-environment.md)、[external_artifacts/README.md](../../external_artifacts/README.md) 及本记录。
