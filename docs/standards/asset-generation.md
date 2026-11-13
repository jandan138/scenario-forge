# 资产生成规范

状态：当前。适用范围：由 Agent 驱动的关节/复杂资产**生产**阶段(需求 → 证据 → 资产规格书 →
迭代生成),以及生产结果移交现有 ConvertAsset 准入管线的边界。
不覆盖:ConvertAsset 内部的转换与资格化(归 [资产接入](asset-intake.md))、场景组装与任务制作。

## 强制要求

<a id="gen-001"></a>
### GEN-001 — 生成是生产者角色,仓库只拥有契约

关节/复杂资产的生成由 Agent 使用外部 skill(如 `skills/hunyuan-isaac-articulation-assets/`)
在生产者角色下完成;Scenario Forge 只拥有各阶段的输入/输出契约:资产规格书格式、证据与哈希策略、
准入请求。`skills/` 下的工具不被 `src/` 导入,不进入任何仓库自动检查;纯包层不得导入模拟器 SDK。
skill 的存在不构成任何资产的资格;生成资产只能经过现有 ConvertAsset 准入边界进入场景。
依据:[项目边界](../../AGENTS.md)、[边界测试](../../tests/test_architecture_boundaries.py)、
[ASSET-001](asset-intake.md#asset-001)、[skills/README](../../skills/README.md)。

<a id="gen-002"></a>
### GEN-002 — 证据分级与逐字段归属

资产规格书中的每个声明必须带证据等级与来源:E(精确,官方规格/实物测量)、F(同族,
同系列或同类产品)、D(推导,有写明依据的工程推导)、U(未知)。
**禁止从照片像素推导尺寸**;交互相关尺寸(手柄跨距、轴位、夹持面)必须实测或标 U。
U 级字段进入待测清单,不得静默填充;推导字段必须写明推导依据。
依据:两份证据分级参考文档(索引见 [external_artifacts README](../../external_artifacts/README.md))、
[资产规格书模板](templates/asset-spec-template.md)。

<a id="gen-003"></a>
### GEN-003 — 资产规格书完整性

进入生成阶段前,资产规格书必须完整实例化
[模板](templates/asset-spec-template.md) 的全部章节:型号身份与使用边界、证据分级、厂商规格冻结表、
资产拆分决策、USD prim 树、关节契约、建议状态量、交互语义、验证矩阵与失败模式、交付命名规范、
待测清单、图片清单。一份规格书可以覆盖多个资产(例如滴定管与支架两个资产 + 装配契约),
拆分决策必须说明理由。规格书经人工签认后冻结;生成阶段的规格变更必须重新签认。
依据:[模板](templates/asset-spec-template.md)、
[生成管线设计](../design/agent-driven-asset-generation-pipeline.md)。

<a id="gen-004"></a>
### GEN-004 — 证据与产物不进 Git

证据图片、参考 docx 原件、原始与生成的 USD 一律只存于 `external_artifacts/` 下;
提交进 Git 的文档以仓库相对路径引用,并把对应 SHA-256 登记进
[external_artifacts 索引](../../external_artifacts/README.md)。
证据只能放 `external_artifacts/` 子树——部分图片格式不在扩展名忽略规则内,
安全性依赖存放位置而非文件类型。
依据:[VAL-005](validation-and-delivery.md#val-005)、`.gitignore`、
[external_artifacts README](../../external_artifacts/README.md)。

<a id="gen-005"></a>
### GEN-005 — 生成资产静态门禁

向 ConvertAsset 提交准入请求前,生成的 USD 必须在 Isaac Kit Python 下通过 skill 自带的
静态契约检查(如 `skills/hunyuan-isaac-articulation-assets/scripts/check_articulation_usd.py`,
一律用全路径调用,不接进 `make check` 或任何仓库自动检查)。任何 FAIL 阻断交付。
检查报告存于 `external_artifacts/` 并登记哈希。静态通过不代表运行时验收,
不替代 [ASSET-002](asset-intake.md#asset-002) 的资格要求,不得写成"物理/交互已通过"。
依据:skill `references/validation-and-acceptance.md` 的静态/运行时分层、
[ASSET-002](asset-intake.md#asset-002)。

<a id="gen-008"></a>
### GEN-008 — 精细铰接主设备九道门禁与双层视觉验收（IKA-Grade Acceptance）

面向需要进入场景评测的多自由度铰接主设备（hero asset），必须在 Stage D 交付前通过
`G1..G8 + G9a + G9b`（共计 10 项门禁）的 IKA-OVEN-125 级验收，并由资产规格书中的声明式
`acceptance` 配置驱动 `scripts/verify_ika_grade_hero_acceptance.py --spec-config <spec>`
输出统一验收报告。本规则沿用 [GEN-007](#gen-007) 四层证据隔离：`robot_integration`
保持 `NOT_TESTED`（交由下游 Astra），不得将直接外力烟测或状态回放写成机器人抓取已通过。

1. **结构与动力学门禁（`G1..G8`）**：
   - **G1 静态单根契约与拓扑序**：通过 `skills/hunyuan-isaac-articulation-assets/scripts/check_articulation_usd.py --mode fixed`；每个刚体 link 显式挂载 `PhysxRigidBodyAPI`（通过 `AddAppliedSchema`），根节点显式挂载 `PhysxArticulationAPI`；USD `Joints` prim 声明顺序必须与 PhysX BFS 拓扑深度一致（所有 depth-1 关节在前，depth-2 及更深层串联子关节置于其后）。
   - **G2 独立重开包络与 CAD 密度**：新进程重开自包含 USD 无绝对路径或 `://` 外部依赖；闭合姿态实测包络误差 $\le 2.5\text{ mm}$ 且底面落座 $Z = 0 \pm 1.0\text{ mm}$；满足网格/材质/文件体积的 CAD 复杂度下限。
   - **G3 控件净空与闭合防遮挡**：所有面板按键/旋钮/开关两两 AABB 最小净空 $\ge 3.0\text{ mm}$ 且 `0` 重叠；默认闭合态（$q = 0$）下上翻压盖/扫描盖板不得遮挡控制屏、文字丝印或按键操作通道。
   - **G4 运行时单根发现与 120 帧零漂移**：Isaac 运行时仅发现 1 个 `Articulation`，`JointStateAPI` 初值生效；零动作静置 `120` 物理步基座与关节无漂移（含配重/阻尼防下坠上盖）。
   - **G5 全 DOF 双向遍历、弹簧回弹与串联复合旋钮**：全部 revolute/prismatic 关节双向行程达标；弹簧微动按键与按压载体可自动回弹归位；串联复合编码器（`DialPress` + `SelectDial`）按压与旋转解耦互不锁定；零 `ignored_friction_attrs`（禁止写入无效 `physxJoint:jointFriction`）。
   - **G6 直接外力烟测（`physics_smoke`）**：对把手/抽屉/压盖施加世界系外力可产生规定方向与幅度的有效位移，同时固定基座零漂移。
   - **G7 600 帧非凸腔体承重（[USD-008](usd-layout.md#usd-008)）**：在规定任务工位摆放独立刚体工件（如浓缩杯、胶囊、PCBA、纸包、校准靶板），连续 `600` 物理步持续承重无跌落、无穿透、无漂移。
   - **G8 载物滑轨/中空隧道穿行**：带抽屉/滑轨/中空隧道的设备（适用时）在物理接触下携带工件平滑推进/抽出，追踪误差与垂向偏移在容差内；无此类机构时显式标 `applicable: false` 并记 PASS。
2. **客观外观底线门禁（`G9a` — Automated Objective Appearance Floor）**：
   - **非纯立方体主构件**：主壳体、上盖、门体、旋钮、纸盒等主要视觉构件（`Visual`）不得退化为 6 面纯立方体（`UsdGeom.Cube` 或 $\le 8$ 顶点 / $\le 6$ 面的盒体），必须通过顶点/面片/法线多样性底线（如 `vertices >= 10`, `faces >= 10`, `unique_normals >= 8`）。
   - **多类 PBR 材质分化**：至少包含 $\ge 3$ 类相互区分的 `UsdPreviewSurface` 材质类别（例如：高金属度金属 `metallic >= 0.5`、哑光聚合物/弹性体 `metallic < 0.3, roughness >= 0.3`、透明玻璃/亚克力或自发光显示材质 `opacity < 0.99` 或 `emissiveColor > 0.01`）。
   - **UI/屏幕/丝印实底检查**：当规格书声明屏幕、刻度盘或丝印 UI 时，若采用 `uv_texture` 路线，USD 内必须绑定实际存在于磁盘的非均匀 `UsdUVTexture` PNG 贴图（像素标准差 `pixel_std > threshold`，拒绝纯色/缺失/占位空图）；若规格书显式采用 `cad_usd_kit` 自包含 `vector_3d` 路线，则必须检出足够数量的 3D 矢量字符/段码网格及分化自发光/颜料材质。
   - **双渲染器曝光与对比度**：Blender Cycles `AgX` 4 视角（`preview_iso`、`preview_front`、`preview_detail`、`preview_ui`）与 Isaac RTX 检视渲染（`isaac_rtx_inspection`）均需有效非空且满足亮度与对比度底线。
3. **独立 Critic 盲审闭环（`G9b` — Independent Critic Blind-Review Loop）**：
   - **硬角色隔离**：`author_agent != critic_agent`（生成器作者不得自审签认）。
   - **强制 3-Pack 视觉输入**：审阅者必须实读三组输入：（a）厂商实物证据与冻结规格书；（b）9/10 正向标杆（如 `ika-oven-125` 级参考）与 4/10 负向标杆（如早期粗粒纯盒退化 `r1` 渲染）；（c）多视角 + 微距 + 开合态候选渲染图。
   - **5 维量化评分与有界返修**：围绕 `silhouette_and_proportion`、`secondary_mechanism_craft`、`pbr_material_hierarchy`、`ui_silkscreen_legibility`、`artifact_free_integrity` 五个维度按 `1.0–10.0` 独立打分；**任一维度 $< 8.0$ 即判 `REJECT` 并附逐部件修复指令，最多允许 `3` 轮有界返修**；全部维度 $\ge 8.0$ 方可签发 `PASS`。
   - **密码学哈希绑定**：`visual_critique_report.json` 必须绑定被审源 USD（`asset.usda`/`source.usda`）及全部已审渲染 PNG 的真实 `SHA-256` 摘要，防止图物脱节或篡改复用。

依据：[validation-and-acceptance](../../skills/hunyuan-isaac-articulation-assets/references/validation-and-acceptance.md)、
[ika-grade-acceptance-and-visual-critic](../../skills/hunyuan-isaac-articulation-assets/references/ika-grade-acceptance-and-visual-critic.md)、
[验收脚本](../../scripts/verify_ika_grade_hero_acceptance.py)、
[单元测试](../../tests/test_ika_grade_hero_acceptance.py)。

<a id="gen-009"></a>
### GEN-009 — 落地结构支撑台面与内化房间环境导出契约

1. **落地结构支撑工作台（`structural_support`）**：场景主操作台严禁退化为悬空纯灰顶板（如仅在 $Z \in [0.71, 0.75]\text{ m}$ 放置单块悬空立方体）。台面资产视觉几何必须真实触地落座（`min_z = 0.000 m ± 2.0 mm`），具备独立桌腿/横梁/走线孔/防滑脚垫与多种分化 `UsdPreviewSurface` 材质，留出机器人前侧伸膝/底座净空通道，且运行时台面根节点（`/World/table`）最高包络 `max_z` 必须与声明支撑面高度 `surface_z_m` 严格一致（$\pm 1.0\text{ mm}$，不得将高于台面的屏风挂件混入 `/World/table` 导致运行时支撑面高度抬升），静态碰撞代理（`__aan_static_support_proxy`）显式启用，经独立 Critic 盲审通过后再提交 `ConvertAsset`（`isaac41`）准入。
2. **仓库内自包含房间导出（`room-source-v2`）**：背景建筑环境（`visual_static_environment`）由生产者使用仓库自有工具链 `skills/agentic-scene-factory/scripts/export_room_source_v2.py` 自包含导出，**严禁依赖外部 `Code-as-Room` 仓库路径**；导出包须包含相对路径 `./textures/` 材质闭包、哈希绑定的 `support_relations.json`（`support_audit == pass`）及独立 Critic 双引擎（Cycles + Isaac Sim 4.1 RTX）盲审签认报告，再经 `scripts/intake_generated_environment.py` 与 `ConvertAsset`（`isaac41`）准入。

依据：[internalized-room-exporter-and-critic](../../skills/agentic-scene-factory/references/internalized-room-exporter-and-critic.md)、
[环境准入操作指南](../operations/intake-generated-blender-environment.md)、
[r4 与 Real-to-Sim 记录](../records/2026-11-13-internalized-room-r4-tables-and-real2sim.md)。

<a id="gen-010"></a>
### GEN-010 — 单图真实工位数字孪生：空间解算、1:1 材质账本与同机位重投影门禁

面向从单张真实工作台照片重建可交互评测场景（Single-Image Real-to-Sim）的生产者流程，除多自由度主设备须满足 [GEN-008](#gen-008) 全部 10 项门禁、台面与房间须满足 [GEN-009](#gen-009) 外，还必须满足以下三项强制门禁（并保持 [GEN-007](#gen-007) 四层证据隔离）：

1. **多基准件锚定空间解算（禁止无锚像素臆测，对齐 [GEN-002](#gen-002)）**：`workstation_pose_grounding.json` 必须锚定至少 $\ge 2$ 件已知实物或工业标准尺寸基准件（如标准配列机械键盘、15.6 寸笔记本、27 寸标准显示器、500 mL 标准饮料瓶），结合 EXIF 等效焦距解算桌面包络、各物体三维位姿及非凸支撑关系（`rests_on` / `stacked_on`），并在刚体碰撞盒层级核验初始零穿透（防止宽面板屏幕与邻近桌面物在 $t = 0$ 发生碰撞推翻）。
2. **1:1 材质与贴图数字孪生账本（`Texture Twin Ledger`）**：源照片中所有可辨识表面材质、商品包装平面设计、品牌标识、贴纸与亮屏 UI 必须逐面建档于 `texture_twin_ledger.json`（由 `src/scenario_forge/adapters/texture_twin_ledger.py` 校验 schema、色差 $\Delta E_{ab}^*$、清晰度与哈希绑定），生成 `Real Crop | Twin Texture | USD Render` 三联比对条并经独立 Critic 盲审通过；禁止以单色 `displayColor` 替代可辨识实物图文。
3. **同机位重投影比对与合成闭环门禁（`Camera-Matched Reprojection Gate`）**：在匹配源照片内参/外参的虚拟相机下渲染完整合成工位，通过 `skills/agentic-scene-factory/scripts/render_reprojection_comparison.py` 输出 `[Source Photo | Virtual Twin Render | 50% Edge-Aligned Overlay]` 重投影比对板与客观对齐指标（$\Delta E_{ab}^*$、`luma_correlation`、`edge_iou`），经独立 Critic 盲审签认后，再通过 Isaac Sim 4.1 + GenManip 7 视角预览、120 帧冷启动稳态（漂移 $\le 5\text{ mm}$）及全阶段谓词金丝雀回放（`0.00 -> 1.00`；`robot_integration` 仍标 `NOT_TESTED`）。

依据：[texture_twin_ledger 校验契约](../../src/scenario_forge/adapters/texture_twin_ledger.py)、
[agentic-scene-factory SKILL](../../skills/agentic-scene-factory/SKILL.md)、
[单元测试](../../tests/test_texture_twin_ledger.py)、
[r4 与 Real-to-Sim 记录](../records/2026-11-13-internalized-room-r4-tables-and-real2sim.md)。

## 推荐做法

<a id="gen-006"></a>
### GEN-006 — 阶段人工签认

半自动流水线中,Agent 在单个阶段内自主执行,阶段之间设人工签认点:
A(需求清单确认)、C(规格书签认 = 冻结)、D(静态门禁报告复核)。
签认不新增审批系统,由任务记录中的签认说明承担。
依据:[生成管线设计](../design/agent-driven-asset-generation-pipeline.md) 的阶段门禁表。

<a id="gen-007"></a>
### GEN-007 — 区分静态、重开与运行时证据

生成阶段的验证结论必须标明证据类型:静态契约检查、重开/渲染检查、PhysX 运行时回放、
机器人接触验证,四者不互相替代。无真实运行时执行的结果标 `static_audit_only`;
未执行的检查项标 `NOT_TESTED`,不得留空或写成通过。
依据:skill `references/validation-and-acceptance.md`、
[VAL-001](validation-and-delivery.md#val-001) 的证据范围纪律。

## 已知限制与变更记录

本页规则重申已有硬边界(Git 策略、生产者/消费者职责、哈希纪律)与 skill 自身契约;
`GEN-001..007` 对纯框架历史说明保持不变,`GEN-008` 已在 `r2`/`r3` 三台跨领域主设备上落地验证契约。

变更记录:2026-09-17 建立资产生成主题,落地 skill 与 A–E 阶段方法论;
同步 [maintenance](maintenance.md) 前缀注册与 [资产接入](asset-intake.md) 交叉引用。
2026-11-13: 新增强制规则 `GEN-008`（`G1..G8 + G9a + G9b` 九道门禁与双层视觉验收）,
保持 `GEN-007` 四层证据隔离不变。
2026-11-13: 新增强制规则 `GEN-009`（落地结构支撑台面与仓库内自包含 `room-source-v2` 房间导出契约）与 `GEN-010`（单图真实工位数字孪生：多基准件空间解算、1:1 材质账本与同机位重投影门禁），见 [r4 与 Real-to-Sim 记录](../records/2026-11-13-internalized-room-r4-tables-and-real2sim.md)。
