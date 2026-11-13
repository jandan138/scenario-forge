# 资产规格书：Brother MFC-L2820DW 激光一体机（正交抽屉+扫描盖+翻转挡纸翼+4微动按键）与纸张耗材组件

> 本规格书依据 [资产规格书模板](../../standards/templates/asset-spec-template.md) 与
> [GEN-001..007](../../standards/asset-generation.md)、[ART-001](../../standards/articulation-and-joints.md)、
> [USD-008](../../standards/usd-layout.md) 及 IKA OVEN 125 (`Oven125`) CAD 级验收标准编写，支撑现代智慧办公印务岛（`modern_office_print_hub`）
> **7-DOF** 水平滑动纸盒装纸随动推入、平板扫描仪对位合盖与前面板实体 `START` 按键触发闭环验证。

## 0. Front matter

| 字段 | 值 |
|---|---|
| asset slug | `brother-mfc-l2820dw-printer` |
| 规格书版本 | `v2.0`（`r2` CAD 级升级版；完整保留 `v1.0`/`r1` 历史溯源） |
| 状态 | `draft`（未经人工冻结签认；冻结需人工签认，见 GEN-006） |
| 日期 | `2026-11-13`（`v1.0`: `2026-11-12`） |
| 作者/Agent | `Antigravity (Scenario Forge Agent)` |
| 来源文档 | 无源 DOCX，按 GEN-002 登记官方数据表证据：`external_artifacts/asset_evidence/brother-mfc-l2820dw-printer/datasheet_evidence.json` |
| 生成工具链 | `cad_usd_kit.py` + `build_brother_office_r2.py`, `source_route: cad_procedural_openusd` |

## 1. 型号身份与使用边界(Model identity & usage boundary)

- **型号与厂商依据**：**Brother Industries, Ltd. — MFC-L2820DW 黑白激光多功能一体机**（底部 250 页全封闭抽拉纸盒 `PaperCassette` + 中部内凹出纸仓及折叠挡纸翼 `OutputFlap` + 右前 $30^\circ$ 倾斜式 2.7 英寸彩屏控制面板及 4 颗微动按键 + 顶部平板扫描仪铰接盖板 `ScannerLid`）。
- **关键识别特征**：
  - 方正深炭灰机身（闭合包络 $410 \times 399 \times 319\text{ mm}$，实测 $410.0 \times 399.4 \times 319.0\text{ mm}$，最大轴向误差 $0.4\text{ mm}$），下部带内凹扣手与青绿导纸卡尺的全宽抽拉纸盒；
  - 顶部平板玻璃稿台四周带白色毫米刻度尺与 CIS 扫描灯条，扫描盖板深度精确设定为 $321\text{ mm}$（$Y \in [-0.122, +0.199]\text{ m}$），合盖状态下 **100% 露空右前 $30^\circ$ 倾斜触控屏与实体按键区**，绝不遮挡按压通道；
  - 控制面板集成自发光彩色 LCD 菜单屏与 4 颗独立弹簧自复位按键（`ButtonStart` 翠绿、`ButtonStop` 珊瑚红、`ButtonClear`、`ButtonPower`）。
- **使用边界**：
  - **支撑**：**7-DOF** 底部纸盒装纸随动推入中空隧道、顶部扫描仪盖板合盖、中层挡纸翼翻出、前面板 4 颗微动按键触发及 GenManip 5 阶段闭环判分验证。
  - **不支撑**：单张柔性纸张搓纸轮卷曲走纸动力学、激光定影热力学及光学 CIS 扫描成像仿真。

## 2. 证据等级与建模纪律(Evidence grading)

等级定义：E = 精确（官方规格/实物测量）；F = 同族（同系列/同类产品）；D = 推导（写明依据）；U = 未知。

| 字段 | 取值 | 等级 | 来源(图片/文档编号) |
|---|---|---|---|
| 闭合外形尺寸 W × D × H | $410 \times 399 \times 319\text{ mm}$ | E | Brother MFC-L2820DW 官方硬件规格 (`S01`) |
| 含耗材整机重量 | $11.56\text{ kg}$ | E | Brother MFC-L2820DW 官方硬件规格 (`S01`) |
| 底部标准纸盒容量 | `250` 页 | E | Brother MFC-L2820DW 官方硬件规格 (`S01`) |
| 触控屏对角线尺寸 | `2.7` in | E | Brother MFC-L2820DW 官方硬件规格 (`S01`) |
| 纸盒 `PaperCassetteJoint` 行程 | $-180\text{ mm} \leftrightarrow 0\text{ mm}$（沿 $-Y$ 拉出，阻尼 $200\text{ N}\cdot\text{s/m}$） | D | 由完全露出装纸内腔并保证 $32\text{ N}$ 推力无冲击平顺载纸滑入推导 |
| 扫描仪盖板 `ScannerLidJoint` 行程 | $-70^\circ \leftrightarrow 0^\circ$（盖深 $321\text{ mm}$，合盖露空前倾斜面板） | D | 由敞开扫描玻璃稿台且合盖不遮挡前 $30^\circ$ 面板推导 |
| 出纸挡翼 `OutputFlapJoint` 行程 | $0^\circ \leftrightarrow +62^\circ$ | D | 中部内凹出纸托盘前缘翻折接纸托翼推导 |
| 4 颗面板微动按键行程 | $-2.5\text{ mm} \leftrightarrow 0\text{ mm}$（弹簧刚度 $k=260\text{ N/m}, c=5.5$） | D | 办公设备面板微动按键回弹行程推导，两两最小净空 $15.0\text{ mm}$ |

## 3. 厂商规格冻结表(Frozen manufacturer spec)

| 参数 | 值 | 单位 | 等级 | 来源 |
|---|---|---|---|---|
| 外形宽度 (W) | `410` | mm | E | Brother MFC-L2820DW 官方规格 (`S01`) |
| 外形深度 (D) | `399` | mm | E | Brother MFC-L2820DW 官方规格 (`S01`) |
| 外形高度 (H) | `319` | mm | E | Brother MFC-L2820DW 官方规格 (`S01`) |
| 含耗材整机质量 | `11.56` | kg | E | Brother MFC-L2820DW 官方规格 (`S01`) |

## 4. 资产拆分决策(Decomposition)

`v2.0 (r2)` 覆盖 1 台 **7-DOF**（8 刚体连杆、`162` CAD 网格、`1.47 MB`）固定基座激光一体机 + 2 件高精度任务刚体 + 1 件同域背景刚体：

| 单元 | 形态 | 理由 |
|---|---|---|
| `Links/Base` | 固定基座刚体 link | 承载深炭灰倒角机身（底部 U 型中空抽屉隧道）、中部内凹出纸仓、顶部玻璃稿台与右前 $30^\circ$ 彩屏座 |
| `Links/PaperCassette` | 铰接刚体 link (`Prismatic`) | 底部可拉出纸盒（5-box 非凸碰撞 + 青绿导纸卡尺 + 扣手凹槽），装载纸包后随动推入机身 |
| `Links/ScannerLid` | 铰接刚体 link (`Revolute`) | 顶部平板扫描仪上盖（含白色柔性压稿背垫），合盖不遮挡前倾斜控制区 |
| `Links/OutputFlap` | 铰接刚体 link (`Revolute`) | 中层内凹出纸口翻转接纸挡翼 |
| `Links/ButtonStart` / `ButtonStop` / `ButtonClear` / `ButtonPower` | 4 个铰接刚体 link (`Prismatic`, spring) | 右前 $30^\circ$ 面板 4 颗法向微动弹簧按键（`disableGravity=True`，自动回弹） |
| `A5MediaPack` | 独立任务刚体资产 (`rigid_object`, `200 KB`) | $156 \times 116 \times 22\text{ mm}$ 精细叠层纹理打印纸包配彩色封腰 |
| `CalibrationSheet` | 独立任务刚体资产 (`rigid_object`, `209 KB`) | $180 \times 130\text{ mm}$ 刚性光学扫描校准靶板（含高精度程序化棋盘格、RGBW 色块与十字对位标贴图） |
| `OfficePenOrganizer` | 独立背景刚体资产 (`dynamic_context_object`, `217 KB`) | 穿孔金属网格笔筒配多色办公签字笔与记号笔组件 |

## 5. USD prim 树(Prim hierarchy)

```text
/AssetRoot                                     (defaultPrim="AssetRoot", Xform, upAxis="Z", mpu=1.0)
├── Materials                                  (23 个 PBR UsdPreviewSurface 材质，含 LCD 贴图、玻璃稿台与通风百叶)
├── Links
│   ├── Base                                   (RigidBodyAPI + MassAPI + 底部中空隧道壳体与扫描稿台复合碰撞)
│   ├── PaperCassette                          (RigidBodyAPI + MassAPI + 5-box 非凸纸槽复合碰撞)
│   ├── ScannerLid                             (RigidBodyAPI + MassAPI + 扫描上盖碰撞)
│   ├── OutputFlap                             (RigidBodyAPI + MassAPI + 出纸挡翼碰撞)
│   ├── ButtonStart                            (RigidBodyAPI + PhysxRigidBodyAPI(disableGravity) + 绿键碰撞)
│   ├── ButtonStop                             (RigidBodyAPI + PhysxRigidBodyAPI(disableGravity) + 红键碰撞)
│   ├── ButtonClear                            (RigidBodyAPI + PhysxRigidBodyAPI(disableGravity) + 返回键碰撞)
│   └── ButtonPower                            (RigidBodyAPI + PhysxRigidBodyAPI(disableGravity) + 电源键碰撞)
└── Joints
    ├── BaseToWorld                            (PhysicsFixedJoint + PhysicsArticulationRootAPI + PhysxArticulationAPI)
    ├── PaperCassetteJoint                     (PhysicsPrismaticJoint, axis=Y, [-0.180m, 0.0m], reset=-0.165m, c=200)
    ├── ScannerLidJoint                        (PhysicsRevoluteJoint, axis=X, [-70°, 0°], reset=-62°, c=20)
    ├── OutputFlapJoint                        (PhysicsRevoluteJoint, axis=X, [0°, +62°], reset=0°, c=3)
    ├── ButtonStartJoint                       (PhysicsPrismaticJoint, axis=Z, [-0.0025m, 0.0m], k=260, c=5.5)
    ├── ButtonStopJoint                        (PhysicsPrismaticJoint, axis=Z, [-0.0025m, 0.0m], k=260, c=5.5)
    ├── ButtonClearJoint                       (PhysicsPrismaticJoint, axis=Z, [-0.0025m, 0.0m], k=260, c=5.5)
    └── ButtonPowerJoint                       (PhysicsPrismaticJoint, axis=Z, [-0.0025m, 0.0m], k=260, c=5.5)
```

*(历史兼容说明：`v1.0/r1` 2-DOF 版本保留于 `external_artifacts/out_of_domain_factory_20261112/` 未覆盖改写。)*

## 6. 关节契约(Joint contracts)

| 关节 (`r2`) | 语义名 | 类型 | 限位 | 驱动/阻尼 | 初始状态 | 状态输出 |
|---|---|---|---|---|---|---|
| `PaperCassetteJoint` | `paper_cassette` | `prismatic` (`Y`) | `[-0.180, 0.000] m` | `k=0, c=200.0` | `open` (`-0.165 m`) | `open: [-0.180, -0.135]`, `closed: [-0.012, 0.0]` |
| `ScannerLidJoint` | `scanner_lid` | `revolute` (`X`) | `[-70.0°, 0.0°]` (`[-1.2217, 0.0] rad`) | `k=0, c=20.0` | `open` (`-1.0821 rad`) | `open: [-1.222, -0.873]`, `closed: [-0.087, 0.0]` |
| `OutputFlapJoint` | `output_flap` | `revolute` (`X`) | `[0.0°, +62.0°]` (`[0.0, 1.0821] rad`) | `k=0, c=3.0` | `folded` (`0.0 rad`) | `folded: [0.0, 0.105]`, `deployed: [0.611, 0.960]` |
| `ButtonStartJoint` | `button_start` | `prismatic` (`Z`) | `[-0.0025, 0.0] m` | `k=260, c=5.5` | `released` (`0.0 m`) | `released: [-0.0006, 0.0]`, `pressed: [-0.0025, -0.0011]` |
| `ButtonStopJoint` | `button_stop` | `prismatic` (`Z`) | `[-0.0025, 0.0] m` | `k=260, c=5.5` | `released` (`0.0 m`) | `released: [-0.0006, 0.0]`, `pressed: [-0.0025, -0.0011]` |
| `ButtonClearJoint` | `button_clear` | `prismatic` (`Z`) | `[-0.0025, 0.0] m` | `k=260, c=5.5` | `released` (`0.0 m`) | `released: [-0.0006, 0.0]`, `pressed: [-0.0025, -0.0011]` |
| `ButtonPowerJoint` | `button_power` | `prismatic` (`Z`) | `[-0.0025, 0.0] m` | `k=260, c=5.5` | `released` (`0.0 m`) | `released: [-0.0006, 0.0]`, `pressed: [-0.0025, -0.0011]` |

## 7. 建议状态量(State variables)

| 状态量 | 类型 | 阈值/语义 |
|---|---|---|
| `media_pack_in_cassette` | bool | `a5_media_pack` 装入纸盒并随盒进入中空隧道，轴向对齐 $\le 15^\circ$ |
| `paper_cassette_closed` | bool | `PaperCassetteJoint` 推回闭合区间 `[-0.012, 0.0] m` |
| `calibration_sheet_on_platen` | bool | `calibration_sheet` 平铺于 `platen_center`（容差 `0.035 m`）且水平对齐 $\le 15^\circ$ |
| `scanner_lid_closed` | bool | `ScannerLidJoint` 合盖至 `[-0.087, 0.0] rad` |
| `button_start_pressed` | bool | 合盖后按压露空的右前翠绿 `ButtonStartJoint` 进入 `[-0.0025, -0.0011] m` |

## 8. 交互语义(Interaction semantics)

| 阶段 (`r2` 5-Stage) | 动作 | 成功判据 |
|---|---|---|
| Stage 1: 抽屉敞开装入打印纸包 | 将左侧 `a5_media_pack` 旋转对准放入拉出 `-165 mm` 的 `paper_cassette` 非凸纸槽 | 纸包平稳落于槽底 `z ≈ 0.014 m` |
| Stage 2: 推回底部纸盒闭合 | 施加 `32 N` 推力将载纸 `paper_cassette` 沿 $+Y$ 推回至 `0.0 m` | 纸包随抽屉无碰撞滑入机身底部中空隧道，`paper_cassette` 达 `closed` |
| Stage 3: 扫描稿台放置校准靶板 | 将右侧 `calibration_sheet` 对准顶部玻璃稿台刻度区平放 | 靶板贴合稿台表面且角度误差 $\le 15^\circ$ |
| Stage 4: 合下顶部扫描仪盖板 | 将 `scanner_lid` 从 `-62°` 合下至 `0°`（不遮挡前倾斜控制区） | 上盖平稳闭合，校准卡零弹跳 |
| Stage 5: 按压前面板翠绿 START 键 | 按压右前 $30^\circ$ 倾斜面板上的 `button_start` `-1.7 mm` 启动扫描校准 | `button_start` 进入 `pressed`，5 项阶段谓词全部成立 (`Score = 1.00`) |

## 9. 验证矩阵与失败模式(QA matrix & failure modes)

| 检查 (`IKA-Grade 9-Gate` + 场景闭环) | 类型 | 结果 |
|---|---|---|
| `G1` `check_articulation_usd.py --mode fixed` 单根/质量/碰撞门禁 | `static` | `PASS` (`sha256:9a0f377ec553a6865202e3e1fc9ebbf475b608965c3a7f5e10cddffce655eed1`) |
| `G2` 二次开盘包络与 CAD 密度 (`1.47 MB`, `162` meshes, `20` colliders) | `reopen` | `PASS` (`measured=[0.4100, 0.3994, 0.3190] m`, `err=0.4 mm <= 2.5 mm`) |
| `G3` 前倾斜面板 4 按键两两净空审计 (`6` pairs) | `reopen` | `PASS` (`0` 干涉，最小净空 `15.0 mm >= 3.0 mm`) |
| `G4` Isaac Sim 4.1 7-DOF 发现与 120 帧零漂移静置 | `runtime` | `PASS` (`7 DOFs`, `base_drift=0.0 mm`, `joint_drift=0.0`) |
| `G5` 全自由度扫掠 + 4 按键弹簧自动回零 | `runtime` | `PASS` (4 颗微动键松手均回 `0.0000 m`) |
| `G6` 直接外力推回 `PaperCassette` 物理烟雾测试 | `runtime_physics_smoke` | `PASS` (`signed_travel=165.0 mm`, `base_drift=0.0 mm`) |
| `G7` 600 帧双腔体承载 (`a5_media_pack` + `calibration_sheet`) | `runtime_physics_smoke` | `PASS` (持续漂移 `0.026 mm` / `0.0 mm`) |
| `G8` 载物抽屉滑入中空隧道测试 (`+165 mm`) | `runtime_physics_smoke` | `PASS` (`obs_delta_y=+164.25 mm`, `tracking_err=0.753 mm`, `z_shift=0.0 mm`) |
| `G9` Blender Cycles 4 视角 + Isaac RTX 工作室渲染门禁 | `visual` | `PASS` (`mean_luma=184.59`, `std_luma=42.58`) |
| `ConvertAsset` `isaac41` 准入与 GenManip 5-Stage Canary | `runtime` | `PASS` (`0.00 -> 0.20 -> 0.40 -> 0.60 -> 0.80 -> 1.00`) |
| 双臂 `lift2` 抽屉推拉与薄板拾放轨迹规划（下游 `Astra` 负责） | `robot` | `NOT_TESTED`（严格遵循 `GEN-007` 证据分离） |

## 10. 交付与命名规范(Delivery conventions)

- **`r2` 源文件**：`external_artifacts/out_of_domain_factory_r2_20261113/assets/source/brother-mfc-l2820dw-printer/asset.usda`
- **`r1` 历史源文件**：`external_artifacts/out_of_domain_factory_20261112/assets/source/brother_mfc_l2820dw/brother_mfc_l2820dw.usda`
- **坐标/单位/轴向**：`metersPerUnit = 1.0`, `kilogramsPerUnit = 1.0`, `upAxis = "Z"`，前向朝 `-Y`，底面齐平 `Z = 0.0`（`USD-001`）。

## 11. 待测清单(Open measurements)

| 项 | 等级 | 计划如何获得 |
|---|---|---|
| 纸盒底部防尘卡扣推入峰值阻力 | U | 实机推拉力计测量 |
| 扫描仪自由停顿铰链扭矩区间 | U | 实机角度-力矩测量 |

## 12. 图片清单(Image inventory)

| 证据 ID | 等级 | 来源 | 使用边界 | 相对路径 |
|---|---|---|---|---|
| `S01` | E | Brother MFC-L2820DW 官方硬件规格结构化摘录 | 外包络尺寸、容量与整机质量冻结依据 | `external_artifacts/asset_evidence/brother-mfc-l2820dw-printer/datasheet_evidence.json` |
| `P01-r2` | D | Blender 4.4.3 Cycles `AgX` 工作室等轴测 (`1280×960`) | 7-DOF 机身、拉出纸盒、敞开稿台与露空倾斜彩屏审视 | `external_artifacts/asset_evidence/brother-mfc-l2820dw-printer-r2/preview_iso.png` |
| `P02-r2` | D | Blender 4.4.3 Cycles `AgX` 正视预览 | 底部青绿导纸卡尺、中部翻转接纸翼与右前控制区审视 | `external_artifacts/asset_evidence/brother-mfc-l2820dw-printer-r2/preview_front.png` |
| `P03-r2` | D | Blender 4.4.3 Cycles `AgX` 扫描稿台特写 | 白色刻度基准边、CIS 扫描灯条与双阻尼铰链审视 | `external_artifacts/asset_evidence/brother-mfc-l2820dw-printer-r2/preview_detail.png` |
| `P04-r2` | D | Blender 4.4.3 Cycles `AgX` 面板 UI 微距特写 | 2.7" 彩屏菜单与翠绿 `START`/珊瑚红 `STOP` 四按键审视 | `external_artifacts/asset_evidence/brother-mfc-l2820dw-printer-r2/preview_ui.png` |
| `RTX-r2` | D | Isaac Sim 4.1 Headless RTX 光追审视图 (`1280×960`) | 仿真器原生扫描玻璃反射与面板可视性核验 | `external_artifacts/asset_evidence/brother-mfc-l2820dw-printer-r2/isaac_rtx_inspection.png` |
| `QA-r2` | E | IKA 级 9 门禁机器可读报告 | 静态/开盘/物理/视觉全链路量化证据 | `external_artifacts/out_of_domain_factory_r2_20261113/assets/ika_grade_acceptance/brother-mfc-l2820dw-printer.json` |

## 13. 来源与许可(Sources & licensing)

- **来源登记**：Brother MFC-L2820DW 公开产品规格参数；几何网格、校准靶板贴图与 LCD 界面贴图全部由本仓 `cad_usd_kit.py` 独立生成，不含第三方 CAD 模型或商标贴图（`LicenseRef-Team-Owned-Procedural`）。
