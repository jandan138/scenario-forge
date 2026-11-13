# 资产规格书：Nespresso Creatista Plus (Breville BNE800) 多自由度咖啡机与配套器皿

> 本规格书依据 [资产规格书模板](../../standards/templates/asset-spec-template.md) 与
> [GEN-001..007](../../standards/asset-generation.md)、[ART-001](../../standards/articulation-and-joints.md)、
> [USD-008](../../standards/usd-layout.md) 及 IKA OVEN 125 (`Oven125`) CAD 级验收标准编写，支撑跨领域精品咖啡吧台（`specialty_coffee_bar`）
> **8-DOF** 多自由度铰接操作、串联推按旋转复合编码器交互与非凸腔体投料闭环验证。

## 0. Front matter

| 字段 | 值 |
|---|---|
| asset slug | `nespresso-creatista-plus-bne800` |
| 规格书版本 | `v2.0`（`r2` CAD 级升级版；完整保留 `v1.0`/`r1` 历史溯源） |
| 状态 | `draft`（未经人工冻结签认；冻结需人工签认，见 GEN-006） |
| 日期 | `2026-11-13`（`v1.0`: `2026-11-12`） |
| 作者/Agent | `Antigravity (Scenario Forge Agent)` |
| 来源文档 | 无源 DOCX，按 GEN-002 登记官方数据表证据：`external_artifacts/asset_evidence/nespresso-creatista-plus-bne800/datasheet_evidence.json` |
| 生成工具链 | `cad_usd_kit.py` + `build_coffee_bar_r2.py`, `source_route: cad_procedural_openusd` |

## 1. 型号身份与使用边界(Model identity & usage boundary)

- **型号与厂商依据**：**Breville / Nespresso Creatista Plus (Model BNE800BSS)**，拉丝不锈钢圆弧窄体机身、顶部镀铬 U 型上翻式胶囊压杆（`BrewLever`）、顶部 OLED 圆屏 + 串联旋转/按压复合选择旋钮（`DialPressCarrier` + `SelectDialRotor`）+ 3 颗微动弹簧按键（`ButtonDrink` / `ButtonTemp` / `ButtonFroth`）、前部穿孔格栅抽拉式杯托滴水盘（`DripTray`）及右侧球节摆动蒸汽棒（`SteamWand`）。
- **关键识别特征**：
  - 机身闭合包络严格贴合 $171 \times 393 \times 308\text{ mm}$（实测 $171.0 \times 393.2 \times 308.0\text{ mm}$，最大轴向误差 $0.2\text{ mm}$），后置透明 SAN 水箱配液位刻度与内部立管；
  - 顶部冲煮鼻上方设镀铬 U 型拱形压杆，掀开后露出 5 盒复合非凸胶囊投料槽（严禁凸包封口）；
  - 控制面板采用真实 Creatista Plus 复合编码器机构（先绕 $Z$ 轴选档、再沿 $+Z$/法向推按确认萃取），禁止退化为静态贴花。
- **使用边界**：
  - **支撑**：**8-DOF** 全关节开合/抽拉/旋钮选档/推按确认/按键回弹/蒸汽棒摆出、非凸胶囊投料槽物理容纳、抽拉杯托载杯平顺滑移及 GenManip 6 阶段闭环判分验证。
  - **不支撑**：真实高压热水萃取流体、蒸汽打奶泡热力学及实机弹簧凸轮曲线力控标定（见第 11 节待测清单）。

## 2. 证据等级与建模纪律(Evidence grading)

等级定义：E = 精确（官方规格/实物测量）；F = 同族（同系列/同类产品）；D = 推导（写明依据）；U = 未知。

- **禁止从照片像素推导尺寸**；未实测交互细节标 D（写明几何间隙推导依据）或 U。
- 本规格书逐字段归属表：

| 字段 | 取值 | 等级 | 来源(图片/文档编号) |
|---|---|---|---|
| 咖啡机闭合外形尺寸 W × D × H | $171 \times 393 \times 308\text{ mm}$ | E | Nespresso / Breville BNE800 官方技术规格 (`S01`) |
| 咖啡机整机重量 | $5.20\text{ kg}$ | E | Nespresso / Breville BNE800 官方技术规格 (`S01`) |
| 水箱标称容积 | $1.5\text{ L}$ | E | Nespresso / Breville BNE800 官方技术规格 (`S01`) |
| OriginalLine 胶囊包络 | 顶缘直径 $37\text{ mm}$ × 高 $30\text{ mm}$ | F | Nespresso Original 标准胶囊规格 |
| 开放式胶囊投料槽净空 | $46 \times 48\text{ mm}$，槽底 $Z = 252\text{ mm}$，5-box 非凸复合碰撞 | D | 由 $37\times 30\text{ mm}$ 胶囊包络加单侧 $\ge 4.5\text{ mm}$ 投料间隙与压杆闭合净空推导 |
| 压杆 `BrewLeverJoint` 行程 | $-75^\circ \leftrightarrow 0^\circ$（绕 $+X$ 轴上翻开启为负角） | D | 由完全暴露投料槽且闭合贴合顶盖推导 |
| 抽拉滴水盘 `DripTrayJoint` 行程 | $-45\text{ mm} \leftrightarrow 0\text{ mm}$（沿 $-Y$ 朝操作侧拉出） | D | 由杯托中心拉出至双联浓缩冲煮嘴正下方（$Y = -192\text{ mm}$）推导 |
| 选择旋钮旋转 `SelectDialJoint` 行程 | $0^\circ \leftrightarrow +90^\circ$ | D | 面板浓缩档位选定区间推导 |
| 选择旋钮推按 `DialPressJoint` 行程 | $0\text{ mm} \leftrightarrow +3.2\text{ mm}$（弹簧刚度 $k=240\text{ N/m}, c=6.0$） | D | 旋转编码器轴向微动确认行程推导 |
| 蒸汽棒摆角 `SteamWandJoint` 行程 | $0^\circ \leftrightarrow +32^\circ$（绕 $+X$ 轴向前摆出） | D | 奶缸打奶泡工位拉出扇区推导 |
| 3 颗面板按键行程 | $-2.2\text{ mm} \leftrightarrow 0\text{ mm}$（弹簧刚度 $k=260\text{ N/m}, c=5.5$） | D | 面板金属微动按键触觉回弹推导，最小键间净空 $15.6\text{ mm}$ |
| 压杆凸轮穿刺峰值阻力矩 | — | U | 待测清单 #1 |

## 3. 厂商规格冻结表(Frozen manufacturer spec)

| 参数 | 值 | 单位 | 等级 | 来源 |
|---|---|---|---|---|
| 外形宽度 (W) | `171` | mm | E | Breville BNE800 官方规格 (`S01`) |
| 外形深度 (D) | `393` | mm | E | Breville BNE800 官方规格 (`S01`) |
| 外形高度 (H) | `308` | mm | E | Breville BNE800 官方规格 (`S01`) |
| 整机质量 | `5.2` | kg | E | Breville BNE800 官方规格 (`S01`) |

## 4. 资产拆分决策(Decomposition)

`v2.0 (r2)` 覆盖 1 台 **8-DOF**（9 刚体连杆、`156` CAD 网格、`2.80 MB`）固定基座铰接主设备 + 2 件高精度旋成任务刚体 + 1 件同域背景刚体：

| 单元 | 形态 | 理由 |
|---|---|---|
| `Links/Base` | 固定基座刚体 link | 承载拉丝不锈钢倒角机身、双联浓缩嘴、透明水箱、TFT 彩屏与 5-box 胶囊投料槽 |
| `Links/BrewLever` | 铰接刚体 link (`Revolute`) | 顶部镀铬 U 型拱形压杆与铆钉耳轴，控制胶囊仓开闭锁紧状态 |
| `Links/DripTray` | 铰接刚体 link (`Prismatic`) | 前置穿孔不锈钢抽拉杯托盘（含凹槽护沿复合碰撞与红色浮球液位标） |
| `Links/DialPressCarrier` | 铰接刚体 link (`Prismatic`, spring) | 复合编码器轴向按压滑架（串联父级），支撑按压启动萃取并自动回弹 |
| `Links/SelectDialRotor` | 铰接刚体 link (`Revolute`) | 滚花不锈钢旋转外环（串联挂接于 `DialPressCarrier` 下），实现“旋选+推按”双自由度解耦 |
| `Links/SteamWand` | 铰接刚体 link (`Revolute`) | 右侧球节不锈钢蒸汽管 + 4 孔蒸汽喷嘴 + 测温探头凸台 |
| `Links/ButtonDrink` / `ButtonTemp` / `ButtonFroth` | 3 个铰接刚体 link (`Prismatic`, spring) | 顶盖 3 颗独立金属微动按键，配 `disableGravity=True` 与弹簧自动回位 |
| `EspressoCup` | 独立任务刚体资产 (`rigid_object`, `240 KB`) | 白瓷回转壁厚浓缩杯配人体工学握把与杯底釉圈（5-box 中空开口复合碰撞） |
| `CoffeeCapsule` | 独立任务刚体资产 (`rigid_object`, `178 KB`) | $\varnothing 37 \times 30\text{ mm}$ 旋成锥台铝胶囊配卷边法兰与铝箔压纹顶膜 |
| `MilkPitcher` | 独立背景刚体资产 (`dynamic_context_object`, `259 KB`) | 不锈钢拉花奶缸配导流尖嘴、带焊接底座握把与内壁容量刻线 |

## 5. USD prim 树(Prim hierarchy)

```text
/AssetRoot                                     (defaultPrim="AssetRoot", Xform, upAxis="Z", mpu=1.0)
├── Materials                                  (19 个 PBR UsdPreviewSurface 材质，含 TFT 自发光贴图与滚花金属)
├── Links
│   ├── Base                                   (RigidBodyAPI + MassAPI + 复合碰撞含 5-box 开放胶囊槽)
│   ├── BrewLever                              (RigidBodyAPI + MassAPI + U 型拱杆复合碰撞)
│   ├── DripTray                               (RigidBodyAPI + MassAPI + 穿孔格栅与护沿复合碰撞)
│   ├── DialPressCarrier                       (RigidBodyAPI + PhysxRigidBodyAPI(disableGravity) + 按压滑架碰撞)
│   ├── SelectDialRotor                        (RigidBodyAPI + PhysxRigidBodyAPI(disableGravity) + 滚花旋钮碰撞)
│   ├── SteamWand                              (RigidBodyAPI + MassAPI + 蒸汽管碰撞)
│   ├── ButtonDrink                            (RigidBodyAPI + PhysxRigidBodyAPI(disableGravity) + 按键碰撞)
│   ├── ButtonTemp                             (RigidBodyAPI + PhysxRigidBodyAPI(disableGravity) + 按键碰撞)
│   └── ButtonFroth                            (RigidBodyAPI + PhysxRigidBodyAPI(disableGravity) + 按键碰撞)
└── Joints
    ├── BaseToWorld                            (PhysicsFixedJoint + PhysicsArticulationRootAPI + PhysxArticulationAPI)
    ├── BrewLeverJoint                         (PhysicsRevoluteJoint, axis=X, [-75°, 0°], reset=-70°)
    ├── DripTrayJoint                          (PhysicsPrismaticJoint, axis=Y, [-0.045m, 0.0m], reset=0.0m)
    ├── DialPressJoint                         (PhysicsPrismaticJoint, axis=Z, [0.0m, +0.0032m], k=240, c=6.0)
    ├── SelectDialJoint                        (PhysicsRevoluteJoint, axis=Z, [0°, +90°], DialPressCarrier->SelectDialRotor)
    ├── SteamWandJoint                         (PhysicsRevoluteJoint, axis=X, [0°, +32°], reset=0°)
    ├── ButtonDrinkJoint                       (PhysicsPrismaticJoint, axis=Z, [-0.0022m, 0.0m], k=260, c=5.5)
    ├── ButtonTempJoint                        (PhysicsPrismaticJoint, axis=Z, [-0.0022m, 0.0m], k=260, c=5.5)
    └── ButtonFrothJoint                       (PhysicsPrismaticJoint, axis=Z, [-0.0022m, 0.0m], k=260, c=5.5)
```

*(历史兼容说明：`v1.0/r1` 3-DOF 版本保留于 `external_artifacts/out_of_domain_factory_20261112/` 未覆盖改写。)*

## 6. 关节契约(Joint contracts)

| 关节 (`r2`) | 语义名 | 类型 | 限位 | 驱动/阻尼 | 初始状态 | 状态输出 |
|---|---|---|---|---|---|---|
| `BrewLeverJoint` | `brew_lever` | `revolute` (`X`) | `[-75.0°, 0.0°]` (`[-1.3090, 0.0] rad`) | `k=0, c=1.8` | `open` (`-1.2217 rad`) | `open: [-1.309, -0.960]`, `closed_locked: [-0.087, 0.0]` |
| `DripTrayJoint` | `drip_tray` | `prismatic` (`Y`) | `[-0.045, 0.000] m` | `k=0, c=32.0` | `retracted` (`0.0 m`) | `retracted: [-0.005, 0.0]`, `extended: [-0.045, -0.035]` |
| `SelectDialJoint` | `select_dial` | `revolute` (`Z`) | `[0.0°, +90.0°]` (`[0.0, 1.5708] rad`) | `k=0, c=0.25` | `standby` (`0.0 rad`) | `standby: [0.0, 0.175]`, `espresso_selected: [1.134, 1.571]` |
| `DialPressJoint` | `dial_press` | `prismatic` (`Z`) | `[0.0, +0.0032] m` | `k=240, c=6.0` | `released` (`0.0 m`) | `released: [0.0, 0.0007]`, `pressed: [0.0014, 0.0031]` |
| `SteamWandJoint` | `steam_wand` | `revolute` (`X`) | `[0.0°, +32.0°]` (`[0.0, 0.5585] rad`) | `k=0, c=0.6` | `parked` (`0.0 rad`) | `parked: [0.0, 0.105]`, `angled_out: [0.279, 0.524]` |
| `ButtonDrinkJoint` | `button_drink` | `prismatic` (`Z`) | `[-0.0022, 0.0] m` | `k=260, c=5.5` | `released` (`0.0 m`) | `released: [-0.0006, 0.0]`, `pressed: [-0.0022, -0.0011]` |
| `ButtonTempJoint` | `button_temp` | `prismatic` (`Z`) | `[-0.0022, 0.0] m` | `k=260, c=5.5` | `released` (`0.0 m`) | `released: [-0.0006, 0.0]`, `pressed: [-0.0022, -0.0011]` |
| `ButtonFrothJoint` | `button_froth` | `prismatic` (`Z`) | `[-0.0022, 0.0] m` | `k=260, c=5.5` | `released` (`0.0 m`) | `released: [-0.0006, 0.0]`, `pressed: [-0.0022, -0.0011]` |

## 7. 建议状态量(State variables)

| 状态量 | 类型 | 阈值/语义 |
|---|---|---|
| `drip_tray_extended` | bool | `DripTrayJoint` 位于 `[-0.045, -0.035] m` |
| `cup_under_spout` | bool | `espresso_cup` 位于拉出托盘杯位 `cup_spout_target`（容差 `0.028 m`）且直立 $\le 12^\circ$ |
| `capsule_in_chute` | bool | `coffee_capsule` 投入非凸胶囊槽 `capsule_chute`（容差 `0.024 m`） |
| `brew_lever_locked` | bool | `BrewLeverJoint` 闭合至 `[-0.087, 0.0] rad` 且胶囊稳定留存槽内 |
| `dial_set_espresso` | bool | `SelectDialJoint` 旋至 `[1.134, 1.571] rad` |
| `dial_pressed_confirm` | bool | `DialPressJoint` 推按进入 `[0.0014, 0.0031] m`（触发冲煮确认） |

## 8. 交互语义(Interaction semantics)

| 阶段 (`r2` 6-Stage) | 动作 | 成功判据 |
|---|---|---|
| Stage 1: 拉出滴水盘 | 将前部 `drip_tray` 沿 $-Y$ 拉出至 `-42 mm` | `drip_tray` 进入 `extended` 区间 |
| Stage 2: 放置浓缩杯 | 抓取 `espresso_cup` 正立安放于穿孔杯托格栅正中 | 杯底稳定落座双联嘴下方且直立误差 $\le 12^\circ$ |
| Stage 3: 投入咖啡胶囊 | 将 `coffee_capsule` 投入顶部 $46\times 48\text{ mm}$ 非凸投料槽 | 胶囊稳定落于槽底 `z ≈ 0.252 m` |
| Stage 4: 压下镀铬压杆 | 将 `brew_lever` 从 `-70°` 下压闭合至 `0°` | `brew_lever` 进入 `closed_locked`，槽内胶囊零弹飞 |
| Stage 5: 旋动选择旋钮 | 将 `select_dial` 顺时针旋至 `+78°` 浓缩档 | `select_dial` 进入 `espresso_selected` |
| Stage 6: 推按编码器确认 | 沿轴向推按旋钮滑架 `+2.4 mm` 确认冲煮 | `dial_press` 进入 `pressed`，6 项阶段谓词全部成立 (`Score = 1.00`) |

## 9. 验证矩阵与失败模式(QA matrix & failure modes)

| 检查 (`IKA-Grade 9-Gate` + 场景闭环) | 类型 | 结果 |
|---|---|---|
| `G1` `check_articulation_usd.py --mode fixed` 单根/质量/碰撞门禁 | `static` | `PASS` (`sha256:12923e4903796b870045fe03402969f0291d90fda8c9e0b1852d9ff40e09173d`) |
| `G2` 二次开盘包络与 CAD 密度 (`2.80 MB`, `156` meshes, `22` colliders) | `reopen` | `PASS` (`measured=[0.1710, 0.3932, 0.3080] m`, `err=0.2 mm <= 2.5 mm`) |
| `G3` 面板多控件两两净空审计 (`6` pairs) | `reopen` | `PASS` (`0` 干涉，最小净空 `15.6 mm >= 3.0 mm`) |
| `G4` Isaac Sim 4.1 8-DOF 发现与 120 帧零漂移静置 | `runtime` | `PASS` (`8 DOFs`, `base_drift=0.0 mm`, `joint_drift=0.0`) |
| `G5` 全自由度扫掠 + 4 按键弹簧自动回零 + 复合旋钮按转解耦 | `runtime` | `PASS` (4 弹簧键松手均回 `0.0000 m`) |
| `G6` 直接外力拉出 `DripTray` 物理烟雾测试 | `runtime_physics_smoke` | `PASS` (`signed_travel=45.0 mm`, `base_drift=0.0 mm`) |
| `G7` 600 帧双非凸腔体承载 (`espresso_cup` + `coffee_capsule`) | `runtime_physics_smoke` | `PASS` (持续漂移 `0.0 mm` / `0.0001 mm`) |
| `G8` 载杯导轨随动拉出测试 (`-42 mm`) | `runtime_physics_smoke` | `PASS` (`obs_delta_y=-41.93 mm`, `tracking_err=0.067 mm`) |
| `G9` Blender Cycles 4 视角 + Isaac RTX 工作室渲染门禁 | `visual` | `PASS` (`mean_luma=188.57`, `std_luma=32.15`) |
| `ConvertAsset` `isaac41` 准入与 GenManip 6-Stage Canary | `runtime` | `PASS` (`0.00 -> 0.17 -> 0.33 -> 0.50 -> 0.67 -> 0.83 -> 1.00`) |
| 双臂 `lift2` 自主抓取与轨迹规划（下游 `Astra` 负责） | `robot` | `NOT_TESTED`（严格遵循 `GEN-007` 证据分离） |

## 10. 交付与命名规范(Delivery conventions)

- **`r2` 源文件**：`external_artifacts/out_of_domain_factory_r2_20261113/assets/source/nespresso-creatista-plus-bne800/asset.usda`
- **`r1` 历史源文件**：`external_artifacts/out_of_domain_factory_20261112/assets/source/nespresso_creatista_plus/nespresso_creatista_plus.usda`
- **坐标/单位/轴向**：`metersPerUnit = 1.0`, `kilogramsPerUnit = 1.0`, `upAxis = "Z"`，前向朝 `-Y`，底面齐平 `Z = 0.0`（`USD-001`）。

## 11. 待测清单(Open measurements)

| 项 | 等级 | 计划如何获得 |
|---|---|---|
| 实机压杆穿刺铝膜峰值扭矩曲线 | U | 实机拉力计测量（仅力控策略需要） |
| 前面板旋钮段落阻尼系数 | U | 实机扭矩计测量 |

## 12. 图片清单(Image inventory)

| 证据 ID | 等级 | 来源 | 使用边界 | 相对路径 |
|---|---|---|---|---|
| `S01` | E | Breville / Nespresso BNE800 官方技术规格结构化摘录 | 外包络尺寸与整机重量冻结依据 | `external_artifacts/asset_evidence/nespresso-creatista-plus-bne800/datasheet_evidence.json` |
| `P01-r2` | D | Blender 4.4.3 Cycles `AgX` 工作室等轴测 (`1280×960`) | 8-DOF CAD 机身、透明水箱与蒸汽管外观审视 | `external_artifacts/asset_evidence/nespresso-creatista-plus-bne800-r2/preview_iso.png` |
| `P02-r2` | D | Blender 4.4.3 Cycles `AgX` 正视预览 | 双联冲煮嘴、穿孔杯托与不锈钢倒角机身审视 | `external_artifacts/asset_evidence/nespresso-creatista-plus-bne800-r2/preview_front.png` |
| `P03-r2` | D | Blender 4.4.3 Cycles `AgX` 腔体特写预览 | 5-box 非凸胶囊投料槽与镀铬 U 型压杆铰链审视 | `external_artifacts/asset_evidence/nespresso-creatista-plus-bne800-r2/preview_detail.png` |
| `P04-r2` | D | Blender 4.4.3 Cycles `AgX` 顶盖 UI 微距特写 | TFT 菜单圆屏、滚花复合旋钮与 3 颗微动按键审视 | `external_artifacts/asset_evidence/nespresso-creatista-plus-bne800-r2/preview_ui.png` |
| `RTX-r2` | D | Isaac Sim 4.1 Headless RTX 光追审视图 (`1280×960`) | 仿真器原生 PBR/玻璃折射与开盘一致性核验 | `external_artifacts/asset_evidence/nespresso-creatista-plus-bne800-r2/isaac_rtx_inspection.png` |
| `QA-r2` | E | IKA 级 9 门禁机器可读报告 | 静态/开盘/物理/视觉全链路量化证据 | `external_artifacts/out_of_domain_factory_r2_20261113/assets/ika_grade_acceptance/nespresso-creatista-plus-bne800.json` |

## 13. 来源与许可(Sources & licensing)

- **来源登记**：Nespresso / Breville Creatista Plus (BNE800) 公开技术规格参数表（仅引用物理包络数值与功能拓扑，几何网格与程序化 UI 贴图全部由本仓 `cad_usd_kit.py` 独立生成）。
- **许可提醒**：资产包内部不包含第三方受版权保护的商标贴图或厂商 CAD 网格，内部评测与开源场景包均可安全分发（`LicenseRef-Team-Owned-Procedural`）。
