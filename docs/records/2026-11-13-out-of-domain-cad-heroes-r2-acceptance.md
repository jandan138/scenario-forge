# 2026-11-13 — Out-of-Domain CAD-Grade Articulated Heroes (`r2`) & IKA-Modeled 9-Gate Acceptance

## 1. 背景与目标

在 [2026-11-12 首轮跨域闭环实证](2026-11-12-out-of-domain-closed-loop-canary.md)（`r1`：`23–25 KB`/台，共 `8 DOFs`）基础上，本轮按 **IKA OVEN 125 (`Oven125`)** 高精度程序化 CAD OpenUSD + 程序化 PBR/UI 贴图同级标准并行升级全部三台跨域主设备与 9 件配套刚体/背景资产，并建立仿照 `IKA OVEN 125` 验收体系的 **9 道量化门禁（`G1..G9`，共 `27/27 PASS`）**。所有首轮 `r1` 产物、配置与记录均保持原样未改写。

## 2. 三台 `r2` 主设备升级对比与哈希索引

| 领域 / 资产 (`r2`) | `r1 -> r2` 规模跃迁 | 可控关节 (`21 DOFs` 总计) | 源 USD SHA-256 / `ConvertAsset` 终态 Manifest SHA-256 |
|---|---|---|---|
| **精品咖啡吧**<br>`NespressoCreatistaPlus` (`nespresso-creatista-plus-bne800`) | `25 KB / 3 DOFs` $\rightarrow$ **`2.80 MB / 156 meshes / 22 colliders / 8 DOFs`** | `BrewLeverJoint`, `DripTrayJoint`, `DialPressJoint` + `SelectDialJoint` (串联复合旋钮), `SteamWandJoint`, `ButtonDrink/Temp/FrothJoint` | `raw`: `12923e4903796b870045fe03402969f0291d90fda8c9e0b1852d9ff40e09173d`<br>`manifest`: `598322825cc4a631083146eb6e01cd988e18e1a5eee6208424b35f9ee1d90b25` |
| **SMT 电子质检工坊**<br>`IngunMA2111Fixture` (`ingun-ma-2111-pcba-fixture`) | `25 KB / 3 DOFs` $\rightarrow$ **`2.69 MB / 123 meshes / 16 colliders / 6 DOFs`** | `PressureHoodJoint` (烟灰亚克力压盖), `ClampLeverJoint` (全宽 U 型门架), `ModeToggleJoint`, `MainsRockerJoint`, `TestStartButtonJoint`, `AbortStopButtonJoint` | `raw`: `6fc110b5256fa9e35ce511225f2006c7523d465e234d772d272a9ab881fbe1dd`<br>`manifest`: `07250093c56b5619f617efd452e677306b7624452281db66f9e38c16276b2a71` |
| **现代办公文印中心**<br>`BrotherMFCL2820DW` (`brother-mfc-l2820dw-printer`) | `23 KB / 2 DOFs` $\rightarrow$ **`1.47 MB / 162 meshes / 20 colliders / 7 DOFs`** | `PaperCassetteJoint`, `ScannerLidJoint` (合盖 100% 露空前 30° 面板), `OutputFlapJoint`, `ButtonStart/Stop/Clear/PowerJoint` | `raw`: `9a0f377ec553a6865202e3e1fc9ebbf475b608965c3a7f5e10cddffce655eed1`<br>`manifest`: `b6f91a7e6d4bdc291bf161911344aa063518ea9e3327f4914f08fadead6f0977` |

## 3. 仿照 `IKA OVEN 125` 的 9 道门禁验收结果（`27/27 PASS`）

机器可读汇总报告：`external_artifacts/out_of_domain_factory_r2_20261113/assets/ika_grade_acceptance/ika_acceptance_summary.json`（Isaac Sim runtime `4.1.0-rc.7+4.1.14801.71533b68.gl`，脚本 [verify_ika_grade_hero_acceptance.py](../../scripts/verify_ika_grade_hero_acceptance.py)）：

1. **`G1` 静态物理契约审计 (`check_articulation_usd.py --mode fixed`)**：3/3 `PASS`，单 `PhysicsArticulationRootAPI`、无负缩放碰撞体、全连杆质量/转动惯量完备。
2. **`G2` 二次开盘闭合包络与 CAD 密度**：轴向最大包络误差分别为 `0.2 mm` / `0.8 mm` / `0.4 mm`（全部 $\le 2.5\text{ mm}$），底面 `Z=0` 贴合误差 `0.0 mm`。
3. **`G3` 面板多控件两两净空审计**：最小键间净空分别为 `15.6 mm` / `47.0 mm` / `15.0 mm`（全部 $\ge 3.0\text{ mm}$，`0` 干涉）。
4. **`G4` Isaac Sim 4.1 铰接发现与 120 帧冷启动静置**：准确发现 `8 / 6 / 7` DOFs，基座漂移 `0.0 mm`，关节漂移 `0.0`。
5. **`G5` 全自由度扫掠、微动弹簧按键自动回零与串联复合旋钮解耦**：全部 10 颗弹簧微动键按压释放后回位至 `0.0000 m`；`NespressoCreatistaPlus` 串联推按+旋转双自由度独立可读。
6. **`G6` 直接外力把手/抽屉驱动烟雾测试 (`apply_forces_and_torques_at_pos`)**：`DripTray` 拉出 `45.0 mm`、`PressureHood` 顺畅合盖 `0.728 rad`、`PaperCassette` 推入 `165.0 mm`，基座漂移 `0.0 mm`。
7. **`G7` 600 帧非凸腔体承载测试**：浓缩杯、咖啡胶囊、PCBA 载板、A5 纸包与扫描校准靶板持续 600 帧漂移 $\le 0.026\text{ mm}$。
8. **`G8` 载物导轨/隧道随动运输**：`DripTray` 载杯随动误差 `0.067 mm`；`PaperCassette` 载纸包滑入中空隧道随动 `+164.25 mm`（跟踪误差 `0.753 mm`，垂向跳动 `0.0 mm`）。
9. **`G9` Blender 4.4.3 Cycles `AgX` 四视角棚拍 + Isaac Sim 4.1 RTX 原生光追审视**：全部 15 张高分辨率审视图通过曝光对比度门禁与人工目视核验。

## 4. 三场景 `r2` 闭环编译、Canary 验证与离线 HTML 交付

- **任务配置**：[configs/out_of_domain_tasks_r2/](../../configs/out_of_domain_tasks_r2/)（扩展为 **6 / 5 / 5 阶段**，终态均包含实体硬件 UI 控件触发：`dial_press: pressed`、`test_start_button: pressed`、`button_start: pressed`）。
- **GenManip Predicate Canary (`predicate_canary_summary.json`)**：
  - `specialty_coffee_bar_creatista_prep`：`t0=0.0 -> [0.1667, 0.3333, 0.5000, 0.6667, 0.8333, 1.0000]`（120 帧最大漂移 `0.001 mm`，Report SHA-256: `ae0675a8067f86932d64a07d691f03fb44acebab49f1a80aaab155ba1e5dba0f`）。
  - `electronics_qa_ingun_probe_lock`：`t0=0.0 -> [0.20, 0.40, 0.60, 0.80, 1.00]`（120 帧最大漂移 `0.001 mm`，Report SHA-256: `ccde52529922d098bdb4e4ccec5b8ae0696ad10b204ef09b85f972ceda4990de`）。
  - `modern_office_brother_calibrate`：`t0=0.0 -> [0.20, 0.40, 0.60, 0.80, 1.00]`（120 帧最大漂移 `0.000 mm`，Report SHA-256: `2e0f7f8b791fe1b83b3dba46f7cc809908b3fe7363942f0a3f1e9bca8098f830`）。
- **纯离线自包含 HTML 展厅**：
  `external_artifacts/out_of_domain_factory_r2_20261113/out_of_domain_hero_showcase_r2_20261113.html`（`83.16 MB`，内嵌 `62` 张无损 PNG 与 `3` 段 720p H.264 视频，`external_urls=0`，SHA-256: `40a43415182bedfcff1823602b9776dabba1f359063bec8b7351c1ecfef6e1e6`）。

## 5. 规范维护说明（Standards Maintenance Block）

- **规范依据**：规范基线提交 `ea731f372a6ccb2cb7cb10d5da52bbf5ffe0726d` 及 [docs/standards/README.md](../standards/README.md)。
- **涉及规则**：`GEN-001..007`、`ART-001`、`USD-001`、`USD-008`、`VAL-001`、`VAL-002`。
- **变化**：**规范无需变更**。原因：现有 `GEN-001..007`（厂商数据表锚定、禁止照片量尺寸、静态/开盘/物理烟雾/机器人策略四层证据分离）、`ART-001`（固定基座唯一根关节与物理单位制）、`USD-008`（开放腔体禁用凸包封口）与 `VAL-001` 已完整覆盖本次 `r2` CAD 级主设备升级与 9 门禁验收边界，无需新增或修改通用规范条款。本次实现中沉淀的 OpenUSD `PhysxRigidBodyAPI`/`PhysxArticulationAPI` 显式 schema 应用及串联关节树 BFS 顺序对齐均属于具体资产构建脚本实践，记录于本档案与脚本单测中。
- **验证**：
  - 纯包检查：`CHECK_PYTHON=/cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-py310/bin/python make check` 全量通过；
  - 资产 9 门禁：`ika_acceptance_summary.json`（`27/27 PASS`，Isaac Sim `4.1.0-rc.7`）；
  - 资产准入：`qualification_summary.json`（12/12 `ConvertAsset` `isaac41` 通过）；
  - 场景闭环：`scene_gate_summary.json` + `predicate_canary_summary.json`（3/3 场景 `0.00 -> 1.00` 通过）。
- **限制或例外**：遵循 `GEN-007` 与 `VAL-001` 诚实声明边界，`static_contract: PASS`、`reopen_and_bounds: PASS`、`physics_smoke: PASS`、`robot_integration: NOT_TESTED`（双臂 `lift2` 逆运动学与无碰撞策略轨迹生成由下游 `Astra` 负责，不在 `Scenario Forge` 编译器仓内伪造策略成功率）。
- **同步内容**：已同步升级三份资产规格书至 `v2.0`（[nespresso-creatista-plus-bne800.md](../design/asset-specs/nespresso-creatista-plus-bne800.md)、[ingun-ma-2111-pcba-fixture.md](../design/asset-specs/ingun-ma-2111-pcba-fixture.md)、[brother-mfc-l2820dw-printer.md](../design/asset-specs/brother-mfc-l2820dw-printer.md)）、[external_artifacts/README.md](../../external_artifacts/README.md) 外部产物哈希索引及本验证记录。
