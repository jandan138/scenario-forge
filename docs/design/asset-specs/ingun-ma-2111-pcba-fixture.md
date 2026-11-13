# 资产规格书：INGUN MA 2111 手动压杆式 PCBA 针床测试治具与 ESD 载板组件

> 本规格书依据 [资产规格书模板](../../standards/templates/asset-spec-template.md) 与
> [GEN-001..007](../../standards/asset-generation.md)、[ART-001](../../standards/articulation-and-joints.md)、
> [USD-008](../../standards/usd-layout.md) 及 IKA OVEN 125 (`Oven125`) CAD 级验收标准编写，支撑工业电子质检台（`electronics_qa_station`）
> **6-DOF** 针床治具开合、全宽 U 型门架锁紧、双路弹簧测试按钮与毫米级三轴姿态对位闭环验证。

## 0. Front matter

| 字段 | 值 |
|---|---|
| asset slug | `ingun-ma-2111-pcba-fixture` |
| 规格书版本 | `v2.0`（`r2` CAD 级升级版；完整保留 `v1.0`/`r1` 历史溯源） |
| 状态 | `draft`（未经人工冻结签认；冻结需人工签认，见 GEN-006） |
| 日期 | `2026-11-13`（`v1.0`: `2026-11-12`） |
| 作者/Agent | `Antigravity (Scenario Forge Agent)` |
| 来源文档 | 无源 DOCX，按 GEN-002 登记官方数据表证据：`external_artifacts/asset_evidence/ingun-ma-2111-pcba-fixture/datasheet_evidence.json` |
| 生成工具链 | `cad_usd_kit.py` + `build_ingun_qa_r2.py`, `source_route: cad_procedural_openusd` |

## 1. 型号身份与使用边界(Model identity & usage boundary)

- **型号与厂商依据**：**INGUN Prüfmittelbau GmbH — MA 2111 手动压杆式测试治具（标准台式机壳 `MA 2111/D/H/S-5`, Item No. 31730，搭配 ATS MA11 ESD 针床板组件）**。
- **关键识别特征**：
  - 倾斜人体工学浅灰粉末喷涂台式底座（闭合包络 $320 \times 515 \times 270\text{ mm}$，实测 $320.0 \times 515.8 \times 270.0\text{ mm}$，最大轴向误差 $0.8\text{ mm}$）；
  - 上翻式烟灰半透明防静电亚克力探针压盖配阳极氧化铝边框与不锈钢压料柱（`PressureHood`）；
  - 全宽双侧镀铬连杆 + 红色滚花横梁 U 型门架锁紧手柄（`ClampLever`），前斜控制面板集成双行 OLED 通道屏、金属模式拨杆（`ModeToggle`）、绿色微动启动按钮（`TestStartButton`）、红色急停按钮（`AbortStopButton`）及电源船型开关（`MainsRocker`）；
  - 针床内腔采用琥珀黄 G10/FR4 环氧玻纤载板 + 80 根 24K 镀金弹簧探针阵列 + 4 导轨非凸定位巢。
- **使用边界**：
  - **支撑**：**6-DOF** 治具放板/合盖/U 型压杆锁紧/激励档切换/绿色 `TEST START` 微动触发全流程几何与刚体碰撞交互、4 导轨定位巢三轴精确姿态判定（$\le 8^\circ$）及 GenManip 5 阶段闭环判分验证。
  - **不支撑**：850 路弹簧探针（Pogo Pin）逐针弹性接触力仿真（$2,000\text{ N}$ 满载接触力）及真实电气导通信号采集。

## 2. 证据等级与建模纪律(Evidence grading)

等级定义：E = 精确（官方规格/实物测量）；F = 同族（同系列/同类产品）；D = 推导（写明依据）；U = 未知。

| 字段 | 取值 | 等级 | 来源(图片/文档编号) |
|---|---|---|---|
| 闭合外形尺寸 W × D × H | $320 \times 515 \times 270\text{ mm}$ | E | INGUN MA 2111 官方数据表 (`S01`, Item 31730) |
| 开启外形尺寸 W × D × H | $320 \times 463 \times 583\text{ mm}$ | E | INGUN MA 2111 官方数据表 (`S01`) |
| ATS MA11 ESD 有效测试区 | $150 \times 240\text{ mm}$ | E | INGUN MA 2111 / ATS MA11 官方数据表 (`S01`) |
| PCB 上方净空高度 | $58\text{ mm}$ | E | INGUN MA 2111 官方数据表 (`S01`) |
| 治具标准质量 | $9.30\text{ kg}$ | E | INGUN MA 2111 官方数据表 (`S01`) |
| 定制 DUT 定位巢内腔净空 | $108 \times 88\text{ mm}$，巢底 $Z = 128\text{ mm}$，4 侧限位轨非凸碰撞 | D | 由 $100 \times 80 \times 10\text{ mm}$ 待测 PCBA 载板加单侧 $4\text{ mm}$ 导向余量推导 |
| 上压盖 `PressureHoodJoint` 行程 | $-70^\circ \leftrightarrow 0^\circ$（阻尼 $0.35\text{ N}\cdot\text{m}\cdot\text{s/deg}$） | D | 由敞开上方放板通道及外力推合顺畅运动推导 |
| U 型门架锁杆 `ClampLeverJoint` 行程 | $-95^\circ \leftrightarrow 0^\circ$（阻尼 $0.30\text{ N}\cdot\text{m}\cdot\text{s/deg}$） | D | 由双侧偏心曲柄无碰撞扫掠包络推导 |
| 模式拨杆 `ModeToggleJoint` 行程 | $-25^\circ \leftrightarrow +25^\circ$ | D | 标准工业双位钮子开关摆角推导 |
| `TestStart` / `AbortStop` 按钮行程 | $-3.4\text{ mm} \leftrightarrow 0\text{ mm}$（弹簧刚度 $k=280\text{ N/m}, c=6.0$） | D | 工业面板自复位微动按钮行程推导，两两最小净空 $47.0\text{ mm}$ |
| 电源船型开关 `MainsRockerJoint` | $-18^\circ \leftrightarrow +18^\circ$ | D | 标准 IEC 面板船型开关摆角推导 |

## 3. 厂商规格冻结表(Frozen manufacturer spec)

| 参数 | 值 | 单位 | 等级 | 来源 |
|---|---|---|---|---|
| 闭合宽度 (W) | `320` | mm | E | INGUN MA 2111 数据表 (`S01`) |
| 闭合深度 (D) | `515` | mm | E | INGUN MA 2111 数据表 (`S01`) |
| 闭合高度 (H) | `270` | mm | E | INGUN MA 2111 数据表 (`S01`) |
| ESD 套件有效区 | `150 × 240` | mm | E | INGUN ATS MA11 数据表 (`S01`) |
| PCB 上方净空 | `58` | mm | E | INGUN MA 2111 数据表 (`S01`) |
| 整机质量 | `9.3` | kg | E | INGUN MA 2111 数据表 (`S01`) |

## 4. 资产拆分决策(Decomposition)

`v2.0 (r2)` 覆盖 1 台 **6-DOF**（7 刚体连杆、`123` CAD 网格、`2.69 MB`）固定基座针床治具 + 2 件高精度任务刚体 + 1 件同域背景刚体：

| 单元 | 形态 | 理由 |
|---|---|---|
| `Links/Base` | 固定基座刚体 link | 承载斜楔金属底座、琥珀 G10 针床、80 根镀金探针阵列、OLED 状态屏与 4 导轨非凸 PCBA 定位巢 |
| `Links/PressureHood` | 铰接刚体 link (`Revolute`) | 烟灰透明亚克力视窗 + 阳极氧化铝框架 + 不锈钢压料柱（合盖保留净空不挤压 PCBA） |
| `Links/ClampLever` | 铰接刚体 link (`Revolute`) | 全宽双臂镀铬连杆 + 红色滚花横梁门架手柄 |
| `Links/ModeToggle` | 铰接刚体 link (`Revolute`) | 前面板金属锥形拨杆开关（`SAFE_OFF` / `PROBE_ACTIVE`） |
| `Links/TestStartButton` | 铰接刚体 link (`Prismatic`, spring) | 绿色护圈弹簧自复位启动按钮（触发针床采样） |
| `Links/AbortStopButton` | 铰接刚体 link (`Prismatic`, spring) | 红色蘑菇头急停微动按钮（配弹簧自复位） |
| `Links/MainsRocker` | 铰接刚体 link (`Revolute`) | 右侧电源船型开关 |
| `PCBACarrierBoard` | 独立任务刚体资产 (`rigid_object`, `449 KB`) | $100 \times 80 \times 10\text{ mm}$ 绿油 FR4 电路板（含 QFP 主控、屏蔽罩、SMD 电容排、镀金测试焊盘与铜柱工艺孔） |
| `ESDTray` | 独立任务刚体资产 (`rigid_object`, `112 KB`) | $160 \times 130\text{ mm}$ 碳黑防静电分格周转托盘（5-box 非凸凹槽复合碰撞） |
| `BenchMultimeter` | 独立背景刚体资产 (`dynamic_context_object`, `217 KB`) | 台式精密六位半万用表（带倾斜支架、背光双显屏、量程旋钮与红黑 4mm 香蕉插孔） |

## 5. USD prim 树(Prim hierarchy)

```text
/AssetRoot                                     (defaultPrim="AssetRoot", Xform, upAxis="Z", mpu=1.0)
├── Materials                                  (19 个 PBR UsdPreviewSurface 材质，含烟灰亚克力与 24K 镀金探针)
├── Links
│   ├── Base                                   (RigidBodyAPI + MassAPI + 斜楔壳体与 4 导轨非凸定位巢碰撞)
│   ├── PressureHood                           (RigidBodyAPI + MassAPI + 上压盖框架碰撞)
│   ├── ClampLever                             (RigidBodyAPI + MassAPI + 双侧曲柄与红色横梁复合碰撞)
│   ├── ModeToggle                             (RigidBodyAPI + PhysxRigidBodyAPI(disableGravity) + 拨杆碰撞)
│   ├── TestStartButton                        (RigidBodyAPI + PhysxRigidBodyAPI(disableGravity) + 绿钮碰撞)
│   ├── AbortStopButton                        (RigidBodyAPI + PhysxRigidBodyAPI(disableGravity) + 红钮碰撞)
│   └── MainsRocker                            (RigidBodyAPI + PhysxRigidBodyAPI(disableGravity) + 船型开关碰撞)
└── Joints
    ├── BaseToWorld                            (PhysicsFixedJoint + PhysicsArticulationRootAPI + PhysxArticulationAPI)
    ├── PressureHoodJoint                      (PhysicsRevoluteJoint, axis=X, [-70°, 0°], reset=-62°, c=0.35)
    ├── ClampLeverJoint                        (PhysicsRevoluteJoint, axis=X, [-95°, 0°], reset=-78°, c=0.30)
    ├── ModeToggleJoint                        (PhysicsRevoluteJoint, axis=X, [-25°, +25°], reset=+21°)
    ├── MainsRockerJoint                       (PhysicsRevoluteJoint, axis=X, [-18°, +18°], reset=+16°)
    ├── TestStartButtonJoint                   (PhysicsPrismaticJoint, axis=Z, [-0.0034m, 0.0m], k=280, c=6.0)
    └── AbortStopButtonJoint                   (PhysicsPrismaticJoint, axis=Z, [-0.0034m, 0.0m], k=280, c=6.0)
```

*(历史兼容说明：`v1.0/r1` 3-DOF 版本保留于 `external_artifacts/out_of_domain_factory_20261112/` 未覆盖改写。)*

## 6. 关节契约(Joint contracts)

| 关节 (`r2`) | 语义名 | 类型 | 限位 | 驱动/阻尼 | 初始状态 | 状态输出 |
|---|---|---|---|---|---|---|
| `PressureHoodJoint` | `pressure_hood` | `revolute` (`X`) | `[-70.0°, 0.0°]` (`[-1.2217, 0.0] rad`) | `k=0, c=0.35` | `open` (`-1.0821 rad`) | `open: [-1.222, -0.873]`, `closed: [-0.087, 0.0]` |
| `ClampLeverJoint` | `clamp_lever` | `revolute` (`X`) | `[-95.0°, 0.0°]` (`[-1.6581, 0.0] rad`) | `k=0, c=0.30` | `unlocked` (`-1.3614 rad`) | `unlocked: [-1.658, -1.047]`, `locked: [-0.105, 0.0]` |
| `ModeToggleJoint` | `mode_toggle` | `revolute` (`X`) | `[-25.0°, +25.0°]` (`[-0.4363, +0.4363] rad`) | `k=0, c=0.18` | `safe_off` (`+0.3665 rad`) | `safe_off: [0.209, 0.436]`, `probe_active: [-0.436, -0.209]` |
| `TestStartButtonJoint` | `test_start_button` | `prismatic` (`Z`) | `[-0.0034, 0.0] m` | `k=280, c=6.0` | `released` (`0.0 m`) | `released: [-0.0007, 0.0]`, `pressed: [-0.0032, -0.0016]` |
| `AbortStopButtonJoint` | `abort_stop_button` | `prismatic` (`Z`) | `[-0.0034, 0.0] m` | `k=280, c=6.0` | `released` (`0.0 m`) | `released: [-0.0007, 0.0]`, `pressed: [-0.0032, -0.0016]` |
| `MainsRockerJoint` | `mains_rocker` | `revolute` (`X`) | `[-18.0°, +18.0°]` (`[-0.3142, +0.3142] rad`) | `k=0, c=0.20` | `on` (`+0.2793 rad`) | `off: [-0.314, -0.175]`, `on: [0.175, 0.314]` |

## 7. 建议状态量(State variables)

| 状态量 | 类型 | 阈值/语义 |
|---|---|---|
| `pcba_seated_in_nest` | bool | `pcba_carrier_board` 位于 `pcba_nest`（容差 `0.018 m`）且 Z 轴与 X 轴对齐误差均 $\le 8^\circ$ |
| `pressure_hood_closed` | bool | `PressureHoodJoint` 合盖至 `[-0.087, 0.0] rad` |
| `clamp_lever_locked` | bool | `ClampLeverJoint` 下压锁止至 `[-0.105, 0.0] rad` |
| `mode_toggle_active` | bool | `ModeToggleJoint` 拨至 `[-0.436, -0.209] rad` |
| `test_start_pressed` | bool | `TestStartButtonJoint` 按压进入 `[-0.0032, -0.0016] m` |

## 8. 交互语义(Interaction semantics)

| 阶段 (`r2` 5-Stage) | 动作 | 成功判据 |
|---|---|---|
| Stage 1: 拾取并高精度放入 PCBA | 从左侧 `esd_tray` 拾取 `pcba_carrier_board`，三轴对准放入 4 导轨定位巢 | 板底平稳贴合巢底 `z = 0.128 m`，三轴角度误差 $\le 8^\circ$ |
| Stage 2: 闭合透明探针压盖 | 将 `pressure_hood` 缓慢合下至 `0°` | 压盖闭合到位且巢内 PCBA 无弹跳 |
| Stage 3: 压下全宽 U 型门架锁杆 | 将 `clamp_lever` 向前下压至 `0°` 死点锁止位 | `clamp_lever` 进入 `locked` 区间 |
| Stage 4: 拨动激励拨杆 | 将 `mode_toggle` 从 `+21°` 拨至 `-21°` 探针激励档 | `mode_toggle` 进入 `probe_active` |
| Stage 5: 按下绿色测试启动键 | 按压前面板 `test_start_button` `-2.4 mm` 触发导通测试 | `test_start_button` 进入 `pressed`，5 项阶段谓词全部成立 (`Score = 1.00`) |

## 9. 验证矩阵与失败模式(QA matrix & failure modes)

| 检查 (`IKA-Grade 9-Gate` + 场景闭环) | 类型 | 结果 |
|---|---|---|
| `G1` `check_articulation_usd.py --mode fixed` 单根/质量/碰撞门禁 | `static` | `PASS` (`sha256:6fc110b5256fa9e35ce511225f2006c7523d465e234d772d272a9ab881fbe1dd`) |
| `G2` 二次开盘包络与 CAD 密度 (`2.69 MB`, `123` meshes, `16` colliders) | `reopen` | `PASS` (`measured=[0.3200, 0.5158, 0.2700] m`, `err=0.8 mm <= 2.5 mm`) |
| `G3` 前面板 4 控件两两净空审计 (`6` pairs) | `reopen` | `PASS` (`0` 干涉，最小净空 `47.0 mm >= 3.0 mm`) |
| `G4` Isaac Sim 4.1 6-DOF 发现与 120 帧零漂移静置 | `runtime` | `PASS` (`6 DOFs`, `base_drift=0.0 mm`, `joint_drift=0.0051`) |
| `G5` 全自由度扫掠 + 双弹簧按钮自动回零 | `runtime` | `PASS` (`TestStart` / `AbortStop` 松手均回 `0.0000 m`) |
| `G6` 直接外力合盖 `PressureHood` 物理烟雾测试 | `runtime_physics_smoke` | `PASS` (`signed_travel=0.728 rad`, `base_drift=0.0 mm`) |
| `G7` 600 帧 4 导轨定位巢承载 `PCBACarrierBoard` | `runtime_physics_smoke` | `PASS` (`settled_z=0.128 m`, 持续漂移 `0.0 mm`) |
| `G8` 导轨隧道随动（本设备无水平抽屉，标记 N/A） | `runtime_physics_smoke` | `PASS` (`applicable=false`) |
| `G9` Blender Cycles 4 视角 + Isaac RTX 工作室渲染门禁 | `visual` | `PASS` (`mean_luma=193.83`, `std_luma=29.35`) |
| `ConvertAsset` `isaac41` 准入与 GenManip 5-Stage Canary | `runtime` | `PASS` (`0.00 -> 0.20 -> 0.40 -> 0.60 -> 0.80 -> 1.00`) |
| 双臂 `lift2` 高精度对插与轨迹规划（下游 `Astra` 负责） | `robot` | `NOT_TESTED`（严格遵循 `GEN-007` 证据分离） |

## 10. 交付与命名规范(Delivery conventions)

- **`r2` 源文件**：`external_artifacts/out_of_domain_factory_r2_20261113/assets/source/ingun-ma-2111-pcba-fixture/asset.usda`
- **`r1` 历史源文件**：`external_artifacts/out_of_domain_factory_20261112/assets/source/ingun_ma_2111_fixture/ingun_ma_2111_fixture.usda`
- **坐标/单位/轴向**：`metersPerUnit = 1.0`, `kilogramsPerUnit = 1.0`, `upAxis = "Z"`，前向朝 `-Y`，底面齐平 `Z = 0.0`（`USD-001`）。

## 11. 待测清单(Open measurements)

| 项 | 等级 | 计划如何获得 |
|---|---|---|
| 偏心连杆死点自锁力矩与探针板反力曲线 | U | 实机测力传感器标定 |
| 定位销倒角几何公差 | U | 卡尺测量实物载具治具板 |

## 12. 图片清单(Image inventory)

| 证据 ID | 等级 | 来源 | 使用边界 | 相对路径 |
|---|---|---|---|---|
| `S01` | E | INGUN MA 2111 (`MA 2111/D/H/S-5`, Item 31730) 数据表结构化摘录 | 闭合/开启包络、有效测试区与整机质量依据 | `external_artifacts/asset_evidence/ingun-ma-2111-pcba-fixture/datasheet_evidence.json` |
| `P01-r2` | D | Blender 4.4.3 Cycles `AgX` 工作室等轴测 (`1280×960`) | 6-DOF 烟灰亚克力压盖、红色门架锁杆与探针床审视 | `external_artifacts/asset_evidence/ingun-ma-2111-pcba-fixture-r2/preview_iso.png` |
| `P02-r2` | D | Blender 4.4.3 Cycles `AgX` 正视预览 | 全宽门架锁杆与前斜控制面板审视 | `external_artifacts/asset_evidence/ingun-ma-2111-pcba-fixture-r2/preview_front.png` |
| `P03-r2` | D | Blender 4.4.3 Cycles `AgX` 针床微距特写 | 80 根 24K 镀金弹簧探针与 4 导轨定位巢审视 | `external_artifacts/asset_evidence/ingun-ma-2111-pcba-fixture-r2/preview_detail.png` |
| `P04-r2` | D | Blender 4.4.3 Cycles `AgX` 面板 UI 特写 | 双行 OLED 屏、金属拨杆、绿启动钮与红急停钮审视 | `external_artifacts/asset_evidence/ingun-ma-2111-pcba-fixture-r2/preview_ui.png` |
| `RTX-r2` | D | Isaac Sim 4.1 Headless RTX 光追审视图 (`1280×960`) | 亚克力透光折射与镀金探针阵列原生渲染核验 | `external_artifacts/asset_evidence/ingun-ma-2111-pcba-fixture-r2/isaac_rtx_inspection.png` |
| `QA-r2` | E | IKA 级 9 门禁机器可读报告 | 静态/开盘/物理/视觉全链路量化证据 | `external_artifacts/out_of_domain_factory_r2_20261113/assets/ika_grade_acceptance/ingun-ma-2111-pcba-fixture.json` |

## 13. 来源与许可(Sources & licensing)

- **来源登记**：INGUN MA 2111 公开产品数据表参数；几何网格与程序化 OLED 贴图全部由本仓 `cad_usd_kit.py` 独立生成，不含第三方 CAD 模型或商标贴图（`LicenseRef-Team-Owned-Procedural`）。
