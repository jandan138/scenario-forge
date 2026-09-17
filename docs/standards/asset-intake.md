# 资产接入规范

状态：当前。适用范围：Scenario Forge 消费资产、生产者整场景与相关 handoff 的制作流程。
接口字段与版本由相应 [来源绑定契约](../design/scenario-source-bindings.md) 定义。

## 强制要求

<a id="asset-001"></a>
### ASSET-001 — 尊重生产与集成职责

ConvertAsset 负责资产转换、源几何/材质修复及其物理配置资格。Scenario Forge 消费合格资产，
按项目契约进行场景组装、任务视觉创作、验证和可移植打包；不得在消费者中重新实现 USD/MDL/mesh 转换，
或为了让设备“能动”而修补生产者的 articulation、关节和碰撞。
纯包层不得导入模拟器 SDK；目标运行时行为由适配器或工具入口承接。
依据：[项目边界](../../AGENTS.md)、[边界测试](../../tests/test_architecture_boundaries.py)、
[固定基座教训](../records/2026-09-04-fixed-base-articulated-instance-v2-and-oven-handoffs.md)。

<a id="asset-002"></a>
### ASSET-002 — 资格绑定到具体来源

记录来源身份、版本、内容哈希、能力与目标运行时，并按所选契约保留许可与分发限制。必须验证所选 handoff 契约要求的资格和依赖闭包，
不能凭文件名中的 `pass`、`final` 或编号最高就采用，也不能以原始资产通过代替最终场景通过。
材质覆盖与原材质保留采用不同的资格路径，按 [视觉接入接口](../design/asset-handoff-visual-admission.md) 选择。
依据：[资产锁](../design/asset-lock.md)、[接入测试](../../tests/test_asset_handoff_archive.py)。

<a id="asset-003"></a>
### ASSET-003 — 只继承被验证的能力

刚体资格不自动包含液体容纳能力；静态保留液体不等于运动、倒液或导流合格。
生产者要求的目标运行时、来源哈希与行为范围必须一同保留；更换运行时不能静默继承验证。
厘米级样品的刚体接触资格也不自动覆盖细颗粒：粒径、接触偏移、薄壁、惯量及宏观设备的
支撑接触可能跨越不同尺度，须以联合场景验证相应能力。
视觉网格转为 SDF 碰撞前，闭合性之外还须检查绕序、方向及内外判定；
不能把 watertight 等同于有效容器碰撞。参见[task09 粉末瓶 r2](../records/2026-09-10-task09-powder-bottle-r2.md)。
依据：[流体交互资产契约](../design/fluid-interaction-asset-contract.md)、
[液体自动接入](../design/liquid-autofill-contract.md)。其中的比例、次数与时间属于对应接口版本，不在本页另写一份。

<a id="asset-004"></a>
### ASSET-004 — 保留不可安全拆分的组成

使用 `producer_entrypoint` 时，内嵌对象按其契约注册，不重新实例化或改写生产者物理、材质与初始状态。
其粒子所有者、碰撞组等可能是一个整体。视觉编辑权限也必须先确认该入口契约允许，
不能把普通组合任务的编辑方式用于只允许原样消费的生产者整场景。
依据：[整场景接口](../design/producer-composed-interactive-scenes.md)、
[对应接入测试](../../tests/test_labutopia_interactive_scene_handoff.py)。

<a id="asset-005"></a>
### ASSET-005 — 碰撞和视觉覆盖分别处理

标准桌等支撑资产使用合格的生产者碰撞，不在 Scenario Forge 场景里额外叠一块本地 slab。
视觉隐藏不等于禁用碰撞。如适用的下游契约明确允许替换支撑碰撞，须先禁用被替换的 collider，
不能把第二套 active collider 直接叠上去；这不赋予 Scenario Forge 修复生产者物理的权限。

依据：[VR 导出接口与操作](../operations/export-vr-teleop-package.md)、
[视觉覆盖测试](../../tests/test_vr_presentation.py)、[标准桌测试](../../tests/test_scientific_workbench_standard_table.py)。

## 推荐做法

<a id="asset-006"></a>
### ASSET-006 — 用明确的能力缺口请求新资产版本

缺少适用的姿态、关节、容器或视觉资格时，把需求、源哈希与失败证据交给生产者，获得新版本后再集成。
优先复用已合格闭包，场景自己拥有的视觉修改按 [MAT-004](materials-and-liquids.md#mat-004) 保留差异证据。
需要全新关节/复杂资产时，能力缺口请求也可经由 Agent 驱动的资产生成管线履行：
按 [GEN-001](asset-generation.md#gen-001) 生成属生产者角色，交付前按
[GEN-005](asset-generation.md#gen-005) 过静态门禁，准入仍走本页资格路径。

<a id="asset-007"></a>
### ASSET-007 — 为 CPU 接触改碰撞近似时锁定摆放

默认仍把碰撞修复交给 ConvertAsset。任务明确要求 CPU 接触、且已有证据表明 SDF 未进入 PhysX 时，
可以在新包中改 `physics:approximation` 或增加不可见基本几何碰撞，但必须证明所有 `obj_*` 世界坐标不变，
并记录这是授权例外而不是消费者常规修关节/修碰撞。不得用凸包填满带孔架子后再把试管留在孔内；
静态三角网格可以保留插孔。残留的禁用 SDF shape 必须从刚体上移除，否则整刚体仍不会进入 CPU PhysX。

依据：[USD-008](usd-layout.md#usd-008)、[斐林 r4](../records/2026-09-11-fehlings-r4-cpu-contact-colliders.md)。

## 验证依据与限制

本页规定接入与证据边界，不宣布所有外部资产均已合格。具体范围由资产报告及接口版本给出。
`scene_fixture_verified` 不能解释成机器人抓取、成功策略或 benchmark 结果。

变更记录：2026-09-08 从现有职责边界与接入契约提炼制作规则；核心/API 契约保留原文权威。
2026-09-09：按[粉末称重 r1](../records/2026-09-09-rigid-powder-force-weighing-r1.md)补充颗粒尺度资格边界。
2026-09-11：按[斐林 r4](../records/2026-09-11-fehlings-r4-cpu-contact-colliders.md)增加 CPU 接触碰撞的授权例外推荐项。
2026-09-17：ASSET-006 交叉引用 [GEN-001](asset-generation.md#gen-001)/[GEN-005](asset-generation.md#gen-005)，能力缺口请求可经由资产生成管线履行；准入资格路径不变。
