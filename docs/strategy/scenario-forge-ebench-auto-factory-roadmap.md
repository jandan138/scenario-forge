# Scenario Forge 发展规划：EBench 自动任务工厂

> 版本：v0.1 PM/Tech Master Plan
> 日期：2026-07-03
> 角色视角：产品经理、技术负责人、研究负责人、工程执行团队
> 核心目标：把 Scenario Forge 规划成一个能批量、自动、可验证、可追溯地为 EBench / embodied-eval-os 生成 embodied evaluation 任务包的场景工厂。

---

## 0. 文档定位

这份文档不是论文综述，也不是保守的“以后可能支持什么”的备忘录。它是一份面向执行的产品与技术规划文档。

这份文档描述的是目标产品方向，不代表当前仓库已经具备 v0.2、USD scene compiler、EBench export、
real-to-sim ingestion、suite factory 或 runtime validation 能力。当前已实现能力仍以 README、
`docs/design/` 和测试为准。

边界声明：

- Scenario Forge 仍然是 portable scenario package compiler，不是 simulator、episode runner、
  model evaluator、leaderboard 或 benchmark report system。
- EBench / embodied-eval-os 负责 episode execution、model interface、trace capture、runtime
  evaluator 和报告/排行榜。
- ConvertAsset 负责 USD/MDL/mesh/GLB conversion；Scenario Forge 只通过公开 CLI 边界规划或调用。
- L7/L8 这类 runtime evidence 可以由 Scenario Forge 记录，但必须来自 adapter 或 downstream runtime，
  不能由 core validation 伪造。
- LabBuilder、RoboGenesis、SimFoundry 是 capability inspirations，不是 runtime dependencies、
  code sources 或 package boundaries。Scenario Forge 会把相关 capability patterns 映射到自己拥有的
  generation plan、asset lock、USD entrypoint、validation report、provenance 和 adapter export contract。

我们已经讨论并确认了几个关键判断：

1. Scenario Forge 的核心定位不是 simulator，不是 episode runner，不是模型训练平台，也不是 leaderboard。
2. Scenario Forge 的核心定位是 **portable scenario package compiler**，也就是把任务、场景、资产、机器人、指标、验证证据和 provenance 编译成下游评测系统可以消费的标准任务包。
3. 给 EBench 的任务包应该包含 USD 场景布局文件，至少包含 `scene.usda` 或等价的 USD stage 文件。
4. USD 场景中引用的 USD 物体资产不能临时乱拼，必须来自 asset registry / asset resolver；正式 v0.2 package 必须有 asset lock，EBench export 优先 fat package。
5. LabBuilder、SimFoundry、LabVLA 论文里的 RoboGenesis 都值得参考，但我们不是把三个项目整个吞进 Scenario Forge，而是把它们的 capability patterns 映射到 Scenario Forge-owned contracts。
6. 理论目标非常明确：Scenario Forge 完成后，应该可以全自动为 EBench 生成任务包。EBench 负责运行 episode 和产出模型评测结果，Scenario Forge 负责生成、校验、追溯、导出任务包。

这份文档会直接把这个判断展开成产品路线、系统架构、模块拆分、包格式、asset 策略、USD 策略、EBench 导出策略、验证策略、阶段规划和近期执行清单。

---

## 1. 一句话愿景

**Scenario Forge 是面向 embodied AI evaluation 的任务包生成与编译平台。它把实验协议、真实场景、资产库、机器人配置、任务图、成功条件和评测指标，自动编译成 EBench / embodied-eval-os 可运行、可验证、可追溯、可复现的标准 scenario packages。**

更产品化地说：

> 用户只需要描述想要的 benchmark 方向，例如“生成 100 个湿实验室机械臂任务，机器人是 Franka，任务难度分三档，导出给 EBench”，Scenario Forge 就能自动生成一组带 USD 场景、USD 物体资产、任务定义、机器人配置、成功条件、验证报告和 provenance 的 EBench-compatible 任务包。

最终产品形态不是一个单点工具，而是一条完整的“任务包工厂”流水线：

```text
Benchmark Spec
  ↓
Protocol / Task Intent
  ↓
Task Graph / Atomic Skills
  ↓
Asset Requirements
  ↓
Asset Resolution / Normalization
  ↓
Layout Planning / Scene Instance Generation
  ↓
USD Scene Compilation
  ↓
Task / Robot / Metric / Predicate Compilation
  ↓
Validation Evidence
  ↓
Fat Package or Locked Package
  ↓
EBench Export
```

---

## 2. 当前项目基因：Scenario Forge 已经走在正确方向上

当前仓库已经建立了一个正确的初始边界：

- 它是 scenario package compiler。
- 它准备 asset、scene、task、robot、metric、provenance artifacts。
- 它不让任何单一 simulator 定义核心格式。
- 它的 first-class downstream targets 包括 EBench-compatible package exports 和 `embodied-eval-os` scenario package exports。
- 它不是 episode runner、simulator facade、USD converter、benchmark leaderboard 或 model evaluation core。
- 它坚持 core validation 不依赖 Isaac Sim、Omniverse、CUDA、Habitat、ManiSkill、OmniGibson 或 simulator SDK。
- 它把 simulator 和 asset tool 集成放在 adapter 边界。
- 它把 ConvertAsset 作为外部 CLI 边界，不重写 USD/MDL/mesh/GLB 转换逻辑。

这说明项目一开始没有走偏。现在要做的不是推翻这个定位，而是把这个定位从“窄而正确的骨架”升级成“能规模化生产评测任务包的工厂”。

当前 starter package 的基本结构是：

```text
scenario_package/
  manifest.yaml
  scene.usda
  scene_instances.yaml
  task.yaml
  robot.yaml
  validation_report.yaml
```

这个结构很适合作为 v0.1 起点，但不够支撑未来的 EBench 自动任务工厂。我们要在这个基础上大胆升级，不背历史包袱。

---

## 3. 核心产品结论

### 3.1 EBench 任务包会包含 USD 场景布局

是的，给 EBench 的任务包应该包含 USD 场景布局文件。这个文件可以叫：

```text
scene.usda
```

或者在更复杂场景中拆成：

```text
scene/root.usda
scene/layout.usda
scene/instances.usda
scene/lighting.usda
scene/cameras.usda
```

但从产品和工程角度，v0.2 应该先坚持一个清晰入口：

```text
scene/main.usda
```

或者沿用当前结构：

```text
scene.usda
```

USD 文件负责表达：

- 3D 场景层级。
- 实验台、地面、背景、区域。
- 物体 USD 引用。
- 每个物体的 pose。
- 机器人初始位置。
- 基础灯光、相机、坐标系。
- 物理/碰撞相关引用或 metadata。

但是 USD 不应该成为唯一真相来源。任务语义仍然应该在 YAML/JSON schema 中明确表达：

- 哪个 instance 是目标物。
- 哪个 instance 是 target zone。
- 哪个 object 是 pickable。
- 成功条件是什么。
- 安全规则是什么。
- 机器人 profile 是什么。
- metric 如何计算。

### 3.2 USD 物体资产来自 asset registry / resolver

USD 场景中的物体资产必须来自一个正式的 asset 系统。我们不接受“临时引用某个本地路径”的开发模式作为默认路径。

资产来源可以包括：

1. Scenario Forge curated asset registry。
2. ConvertAsset 规范化后的 USD asset package。
3. LabBuilder-style planner 推导出的实验室资产需求。
4. SimFoundry-style real-to-sim 产出的物体 mesh / scene mesh / digital twin / digital cousin。
5. simulator-native asset library，经 adapter 和 lockfile 规范化后使用。
6. 用户上传资产，经 normalization、license、checksum、physics metadata 检查后进入 registry。

关键原则：

> 任务生成器只应该面对 `asset_id`、`affordance`、`semantic_tags`、`physics_profile`、`license`、`version`，不应该直接面对散落的本地文件路径。

### 3.3 开发阶段就使用 asset lock；正式导出优先 fat package

这个决策非常重要。

我们不采用“开发阶段先 thin package，发布阶段再补 lockfile”的保守路线。因为 embodied evaluation 的最大风险之一就是不可复现。场景包今天能跑，三个月后资产变了、路径变了、材质丢了、版本不一致，任务就失去 benchmark 价值。

因此从开发阶段开始就默认要求：

```text
每个正式 v0.2 scenario package 都必须有 `asset_lock.yaml`。

`package_mode` 决定资产是否随包 materialize：

1. fat package：资产实体随包 materialize 到 assets/ 目录，同时仍然携带 asset_lock.yaml；
2. locked package：资产可以不全部 materialize，但所有外部资产都写入 asset_lock.yaml，包含 source、version、sha256、license、normalized hash、resolver 信息。
```

内部临时实验可以有 thin reference，但 thin reference 不能作为 Scenario Forge 的标准产物，不能作为 EBench export 的默认输入，也不能进入正式 benchmark suite。

### 3.4 Scenario Forge 完成后可以全自动给 EBench 生成任务

理论目标是肯定的：Scenario Forge 应该能自动给 EBench 生成任务包。

但要把这句话拆成两层：

```text
Scenario Forge 负责：自动生成 EBench-compatible scenario packages。
EBench 负责：加载任务包、运行 episode、记录 trace、评测模型、产出 leaderboard/report。
```

产品目标不是“Scenario Forge 自己评测所有模型”，而是“Scenario Forge 成为 EBench 的任务包工厂”。

---

## 4. 外部能力映射策略

我们要把 LabBuilder、SimFoundry、RoboGenesis 的 capability patterns 映射到 Scenario Forge-owned contracts，但不能把它们变成 Scenario Forge 的依赖、代码来源或边界污染源。

一句话映射：

```text
LabBuilder   → protocol-grounded layout and safety planning
SimFoundry   → real-to-sim scene/asset ingestion and digital twin/cousin generation
RoboGenesis  → workflow decomposition, atomic skills, rollout filtering, structured demonstrations
Scenario Forge → package schema, asset locking, USD compilation, validation, provenance, EBench export
```

我们要吸的是能力模型，不是项目形态。

### 4.1 2026-07-03 外部能力采用政策

多视角调研结论：

```text
不要闭门重写大而全的 layout / real-to-sim 系统。
也不要把 LabBuilder 或 SimFoundry fork 成 Scenario Forge core。
Scenario Forge 采用 contract-first + adapter/importer + A/B gate。
```

原因：

1. Scenario Forge 的核心价值是 portable package contract、asset lock、USD entrypoint、
   validation ladder、provenance 和 EBench export，而不是外部 pipeline 的内部实现。
2. LabBuilder-style 能力最适合作为 protocol/layout/safety producer，输出必须落到
   `generation_plan.yaml`、`scene/layout.yaml`、`scene/instances.yaml` 和 `evidence/*`。
3. SimFoundry-style 能力最适合作为 real-to-sim ingestion adapter，输出必须落到
   `assets/asset_manifest.yaml`、`locks/asset_lock.yaml`、`scene/instances.yaml`、
   `provenance/*` 和 `evidence/*`。
4. 外部 pipeline 可以比我们的 baseline 更强，但只有在 license、artifact contract、
   dependency boundary、validation evidence 都清楚之后，才能升级为 supported adapter。
5. 任何外部系统都不能绕过 Scenario Forge 的 manifest、asset lock、schema validation
   和 adapter boundary。

采用门槛：

```text
1. 先实现 Scenario Forge deterministic baseline。
2. 外部系统先作为 importer/adapter 接入，不进入 core。
3. 用 golden tasks 做 A/B：baseline vs external pipeline vs hand-authored reference。
4. 对比 package validity、asset-lock coverage、predicate binding、reachability、
   collision/safety checks、EBench adapter readiness。
5. 只有外部 pipeline 在这些指标上稳定更好，且不破坏 portability，才扩大使用。
```

---

## 5. LabBuilder-style 能力映射

### 5.1 LabBuilder 对我们的价值

LabBuilder 的核心价值是：它不是普通的 3D 室内场景生成，而是 protocol-grounded 实验室布局生成。它强调实验协议、功能语义、安全约束、可达性、化学安全、导航可行性。

对 Scenario Forge 来说，这正好补齐“场景布局不是好看就行，而是要支持任务执行”的能力。

我们应该吸收的能力：

1. **Protocol Grounding**
   把自然语言实验需求转成结构化 protocol。

2. **Protocol Asset Knowledge Base**
   维护实验室资产、仪器、试剂、容器、区域、危险属性、可交互 affordance。

3. **Constraint-aware Layout Planning**
   根据实验 protocol 生成实验台、设备、容器、目标区域、危险区域、机器人操作区域的布局。

4. **Safety-aware Layout Validation**
   检查化学安全、几何可达性、导航可行性、操作空间、碰撞风险。

5. **Task-grounded Scene Generation**
   布局不是为了视觉真实，而是为了让任务可以执行、可以评测、可以复现。

### 5.2 Scenario Forge 中对应模块

建议新增或强化这些模块：

```text
src/scenario_forge/
  generation/
    protocols/
      protocol_grounder.py
      protocol_schema.py
    layout/
      workbench_layout_planner.py
      constraints.py
      zoning.py
      reachability.py
      safety_rules.py
  assets/
    asset_knowledge_base.py
    affordances.py
    hazards.py
  evaluation/
    layout_checks.py
    safety_checks.py
```

### 5.3 LabBuilder-style 输入输出

输入：

```yaml
schema_version: protocol-request/v0.1
request_id: workbench_pipette_001
natural_language: "Create a bench setup where a Franka robot transfers liquid from a sample tube to a target vial using a pipette."
domain: scientific_workbench
robot_profile: franka_panda
safety_level: standard_workbench
```

输出：

```yaml
schema_version: grounded-protocol/v0.1
protocol_id: workbench_pipette_001
required_assets:
  - role: workbench
    asset_type: workbench_table
  - role: pipette
    asset_type: pipette
    affordances: [graspable, pressable]
  - role: source_container
    asset_type: sample_tube
    affordances: [container, transparent, graspable]
  - role: target_container
    asset_type: vial
    affordances: [container]
  - role: waste_area
    asset_type: waste_container
constraints:
  - type: reachable_by_robot
    object_roles: [pipette, source_container, target_container]
  - type: separate_from
    a: waste_area
    b: source_container
  - type: stable_support
    object_roles: [source_container, target_container]
  - type: operation_clearance
    around: pipette
    radius_m: 0.15
safety_rules:
  - type: no_cross_contamination
  - type: no_spill
  - type: keep_containers_upright
```

### 5.4 产品化结论

LabBuilder 的能力应该成为 Scenario Forge 的 **layout intelligence**，不是单独的产品孤岛。

Scenario Forge 应该能回答：

- 这个实验任务需要哪些物体？
- 这些物体应该如何摆放？
- 哪些东西必须靠近？
- 哪些东西必须隔离？
- 机器人是否够得到？
- 任务区域是否有操作空间？
- 场景是否满足安全约束？

### 5.5 复用性判断

截至 2026-07-03，公开 LabBuilder 仓库显示：

- `LabForge` protocol synthesis 已发布；
- `LabGen` layout generation 与 `LabTouchstone` evaluation 标记为 coming soon；
- 代码 license 与 data/assets license 分离，data/assets 包含非商业限制；
- USD asset payload 仍需单独下载或尚未完全公开。

因此当前策略不是 fork LabBuilder，也不是把 LabBuilder 数据集直接放进 Scenario Forge。

采用方式：

```text
LabForge-style protocol output
  -> generation_plan.yaml
  -> required_assets
  -> layout_constraints
  -> safety_rules
  -> evidence/layout_checks.yaml
  -> provenance/source_refs.yaml
```

后续只有在完整 LabGen / LabTouchstone 代码和可再分发资产条款明确后，才重新评估
是否增加 optional LabBuilder adapter。

---

## 6. RoboGenesis-style 能力映射

### 6.1 RoboGenesis 对我们的价值

LabVLA 论文里的 RoboGenesis 是 simulation-based workflow and data engine。它从 atomic skills 组合实验室 workflow，验证和过滤 rollouts，并跨 robot profiles 导出 structured demonstrations。

这和 Scenario Forge 的任务生成主线高度相关。

我们应该吸收的能力：

1. **Atomic Skill Library**
   把 pick、place、pour、insert、open、close、press、move-to、aspirate、dispense 等能力抽象成可组合单元。

2. **Workflow Composer**
   把实验 protocol 组合成多步 task graph。

3. **Precondition / Postcondition Modeling**
   每一步动作都有前置条件和后置状态变化。

4. **Rollout Validation / Filtering**
   自动生成的任务必须过滤掉不可执行、不稳定、不安全、语义错误的候选。

5. **Robot Profile Abstraction**
   同一个 task graph 可以映射到不同机器人 profile。

6. **Structured Demonstration Export**
   结构化演示数据可以作为可选 artifact，为下游训练或评测提供辅助。

### 6.2 Scenario Forge 中对应模块

```text
src/scenario_forge/
  generation/
    skills/
      atomic_skill.py
      skill_library.py
      skill_bindings.py
    workflows/
      task_graph.py
      workflow_composer.py
      preconditions.py
      postconditions.py
      rollout_filter.py
  schemas/
    v1/
      task_graph.py
      skill.py
      demonstration.py
  evaluation/
    predicates.py
    trajectory_evidence.py
```

### 6.3 Task Graph 示例

```yaml
schema_version: task-graph/v0.1
task_graph_id: pipette_transfer_graph_001
instruction: "Transfer liquid from the source tube to the target vial."
robot_profile: franka_panda
nodes:
  - id: move_to_pipette
    skill: move_to_object
    target: pipette_001
    preconditions:
      - type: object_exists
        object: pipette_001
    postconditions:
      - type: end_effector_near_object
        object: pipette_001

  - id: grasp_pipette
    skill: grasp
    target: pipette_001
    preconditions:
      - type: end_effector_near_object
        object: pipette_001
    postconditions:
      - type: object_grasped
        object: pipette_001

  - id: aspirate_liquid
    skill: aspirate
    tool: pipette_001
    source: source_tube_001
    amount_ml: 1.0
    preconditions:
      - type: object_grasped
        object: pipette_001
      - type: liquid_available
        container: source_tube_001
    postconditions:
      - type: pipette_contains_liquid
        tool: pipette_001
        amount_ml: 1.0

  - id: dispense_liquid
    skill: dispense
    tool: pipette_001
    target: target_vial_001
    amount_ml: 1.0
    preconditions:
      - type: pipette_contains_liquid
        tool: pipette_001
    postconditions:
      - type: liquid_in_container
        container: target_vial_001
        amount_ml_min: 0.9
edges:
  - from: move_to_pipette
    to: grasp_pipette
  - from: grasp_pipette
    to: aspirate_liquid
  - from: aspirate_liquid
    to: dispense_liquid
success_predicates:
  - type: liquid_transferred
    source: source_tube_001
    target: target_vial_001
    amount_ml_min: 0.9
safety_rules:
  - type: no_spill
  - type: keep_containers_upright
  - type: no_collision_with_glassware
```

### 6.4 产品化结论

RoboGenesis 的能力应该成为 Scenario Forge 的 **workflow intelligence**。

Scenario Forge 应该能回答：

- 一个实验任务可以拆成哪些 atomic skills？
- 每一步的前置条件和后置条件是什么？
- 哪些 object / tool / zone 是任务必须的？
- 任务成功条件如何从 workflow 自动推导？
- 机器人 profile 改变后，任务是否仍然可行？
- 生成的任务是否能通过 rollout filtering？

---

## 7. SimFoundry-style 能力映射

### 7.1 SimFoundry 对我们的价值

SimFoundry 的价值是 real-to-sim：从真实世界视频自动生成可交互仿真环境，并支持 digital twins 和 digital cousins。它还能做 object、scene、task editing，从真实视频中提取 segmentation、depth 等信息，生成 3D object meshes，标注物理参数，并在物理仿真器里 sanity check 场景。

对 Scenario Forge 来说，SimFoundry-style 能力是资产和场景的强入口。

我们应该吸收的能力：

1. **Real-to-Sim Ingestion**
   从视频、图片、scan、外部 reconstruction pipeline 中导入场景初稿。

2. **Digital Twin Packaging**
   把真实场景复刻成一个 locked scenario package。

3. **Digital Cousin Generation**
   保持任务语义不变，生成对象、布局、背景、材质、任务条件的变体。

4. **Physics-ready Object Reconstruction**
   不是只有视觉 mesh，还要有 collision、mass、friction、articulation、graspability 等物理信息。

5. **Scene/Task Augmentation**
   为 benchmark 生成泛化维度，而不是只生成一个固定任务。

### 7.2 Scenario Forge 中对应模块

```text
src/scenario_forge/
  adapters/
    real2sim/
      base.py
      simfoundry_like.py
  assets/
    reconstructed_assets.py
    physics_profiles.py
    normalization.py
  generation/
    cousins/
      cousin_plan.py
      object_cousins.py
      scene_cousins.py
      task_cousins.py
  artifacts/
    evidence.py
    provenance.py
```

### 7.3 SimFoundry-style 输入输出

输入：

```yaml
schema_version: real2sim-request/v0.1
request_id: real_workbench_scan_001
source:
  type: video
  uri: file://inputs/workbench_surface_video.mp4
intent:
  preserve_task_semantics: true
  target_domain: scientific_workbench
outputs:
  generate_twin: true
  generate_cousins: true
  cousin_count: 20
```

输出：

```yaml
schema_version: real2sim-result/v0.1
result_id: real_workbench_scan_001_result
scene:
  kind: digital_twin
  usd_entrypoint: scene/main.usda
assets:
  - asset_id: reconstructed_beaker_001
    asset_type: beaker
    usd_path: assets/objects/reconstructed_beaker_001/model.usd
    collision_path: assets/objects/reconstructed_beaker_001/collision.usd
    physics_profile:
      mass_kg: 0.12
      friction: 0.4
    source_evidence:
      source_video: inputs/workbench_surface_video.mp4
      reconstruction_method: simfoundry_like
cousins:
  - cousin_id: cousin_001
    changes:
      - type: object_substitution
        original: reconstructed_beaker_001
        replacement_asset_id: curated_beaker_250ml_v2
      - type: pose_perturbation
        object: target_vial_001
        max_distance_m: 0.08
```

### 7.4 产品化结论

SimFoundry 的能力应该成为 Scenario Forge 的 **real-to-sim and cousin generation intelligence**。

Scenario Forge 应该能回答：

- 如何把真实实验台变成 EBench 任务包？
- 如何从一个真实场景生成多个语义等价但外观/布局不同的 cousins？
- 如何让 benchmark 覆盖真实世界变体？
- 如何把重建资产锁定、校验、追溯？
- 如何把 real-to-sim pipeline 的结果纳入统一 package contract？

### 7.5 复用性判断

截至 2026-07-03，公开 SimFoundry 信息主要是论文、项目页、交互 demo 和 pipeline 描述；
没有稳定、可直接依赖的公开实现和 artifact contract 可作为 Scenario Forge core 依赖。

SimFoundry-style 能力仍然非常重要，但采用方式是 real-to-sim adapter：

```text
SimFoundry-like output
  -> adapters/real2sim/importer
  -> assets/asset_manifest.yaml
  -> locks/asset_lock.yaml
  -> scene/instances.yaml
  -> scene/layout.yaml
  -> provenance/source_refs.yaml
  -> evidence/asset_checks.yaml
  -> evidence/layout_checks.yaml
```

不进入 core 的内容：

```text
video reconstruction pipeline
foundation model calls
segmentation/depth/intermediate tensors
Gaussian splat training
simulator settling and rollout code
policy training/evaluation
benchmark reports
```

---

## 8. Scenario Forge 的目标产品形态

### 8.1 不只是 CLI，而是任务包工厂

最终产品可以有三个入口：

1. **CLI**：工程师和自动化流水线使用。
2. **Python SDK**：研究代码、数据生成 pipeline 使用。
3. **Workbench UI**：产品经理、研究员、benchmark designer 使用。

但所有入口都应该收敛到同一条核心 pipeline：

```text
Spec → Plan → Resolve → Compile → Validate → Package → Export
```

### 8.2 用户画像

主要用户：

1. Benchmark designer
   想批量设计评测任务。

2. Embodied AI researcher
   想快速生成高质量场景任务，用于模型评估。

3. Robotics engineer
   关心任务是否可执行、资产是否物理合理、机器人是否可达。

4. Dataset / benchmark release manager
   关心可复现、license、版本、provenance、split、coverage。

5. EBench / embodied-eval-os maintainer
   关心任务包是否可加载、可运行、可评测。

### 8.3 产品故事

用户输入：

```text
我想生成 100 个湿实验室任务，机器人是 Franka，任务包括 pick-place、pipette transfer、container sorting、sample staging，难度分 easy/medium/hard，导出给 EBench。
```

Scenario Forge 输出：

```text
ebench_workbench_suite_v0/
  suite_manifest.yaml
  splits/
    train.yaml
    dev.yaml
    test.yaml
  packages/
    workbench_pick_place_0001/
    workbench_pick_place_0002/
    workbench_pipette_transfer_0001/
    ...
  suite_validation_report.yaml
  suite_asset_lock.yaml
  suite_provenance.yaml
```

每个 package 内部都是 fat package 或 locked package，可以被 EBench adapter 消费。

---

## 9. 标准包格式：v0.2 建议

当前 v0.1 package 是很好的起点，但 v0.2 应该直接面向 EBench 自动任务工厂升级。

### 9.1 单个任务包结构

建议结构：

```text
scenario_package/
  manifest.yaml
  generation_plan.yaml
  scene/
    main.usda
    layout.yaml
    instances.yaml
  task/
    task.yaml
    task_graph.yaml
    predicates.yaml
    safety_rules.yaml
  robot/
    robot.yaml
    robot_profile.yaml
  metrics/
    metrics.yaml
    splits.yaml
  assets/
    asset_manifest.yaml
    objects/
      <asset_id>/
        model.usd
        collision.usd
        materials/
        textures/
        metadata.yaml
    robots/
      <robot_asset_id>/
        model.usd
        metadata.yaml
    environments/
      <environment_asset_id>/
        model.usd
        metadata.yaml
  locks/
    asset_lock.yaml
    generator_lock.yaml
    schema_lock.yaml
  evidence/
    validation_report.yaml
    static_checks.yaml
    asset_checks.yaml
    layout_checks.yaml
    adapter_checks.yaml
    runtime_smoke.yaml
  provenance/
    provenance.yaml
    source_refs.yaml
    generation_trace.jsonl
  adapters/
    ebench/
      package.yaml
      task_entrypoint.yaml
      adapter_report.yaml
    embodied-eval-os/
      package.yaml
      adapter_report.yaml
```

### 9.2 为什么 v0.2 要大胆升级

不建议为了兼容 v0.1 starter package 而设计过多 fallback。当前项目还处于早期，最重要的是尽快定义正确的 v0.2 contract。v0.1 可以通过 migration 工具升级到 v0.2，但不应该让 v0.1 限制未来。

决策：

```text
v0.1 是 bootstrap format。
v0.2 是 product format。
v1.0 是 external stability format。
```

在 v1.0 之前，不承诺长期向后兼容。所有 schema 允许快速演进，但必须有 migration command：

```bash
scenario-forge package migrate \
  --from scenario-package/v0.1 \
  --to scenario-package/v0.2 \
  --in old_package \
  --out new_package
```

---

## 10. Manifest 设计

### 10.1 manifest.yaml 示例

```yaml
schema_version: scenario-package/v0.2
package_id: workbench_pick_place_0001
package_kind: single_task
scenario_domain: scientific_workbench
benchmark_target:
  primary: ebench
  secondary:
    - embodied-eval-os
entrypoints:
  scene_usd: scene/main.usda
  scene_instances: scene/instances.yaml
  task: task/task.yaml
  task_graph: task/task_graph.yaml
  robot: robot/robot.yaml
  metrics: metrics/metrics.yaml
  validation_report: evidence/validation_report.yaml
  asset_lock: locks/asset_lock.yaml
assets:
  mode: fat_or_locked
  asset_manifest: assets/asset_manifest.yaml
  asset_lock: locks/asset_lock.yaml
exports:
  - target: ebench
    path: adapters/ebench/package.yaml
    status: generated
  - target: embodied-eval-os
    path: adapters/embodied-eval-os/package.yaml
    status: generated
provenance:
  generator: scenario-forge
  generator_version: 0.2.0
  generation_plan: generation_plan.yaml
  trace: provenance/generation_trace.jsonl
validation:
  report: evidence/validation_report.yaml
  minimum_required_level: adapter_static_validated
```

### 10.2 manifest 的产品含义

`manifest.yaml` 是任务包的合同。任何下游系统，包括 EBench，都不应该猜目录结构，而应该先读 manifest。

manifest 负责回答：

- 这个包是什么版本？
- 这个包是什么任务？
- 这个包属于哪个 domain？
- 场景入口在哪里？
- 任务定义在哪里？
- 机器人定义在哪里？
- 资产锁在哪里？
- 验证报告在哪里？
- 有哪些 adapter export？
- provenance 在哪里？

---

## 11. Asset 架构

### 11.1 设计原则

Asset 是 Scenario Forge 的核心资产，不是附属品。

原则：

1. `asset_id` 是语义标识，不等于文件路径。
2. `asset_digest` 是内容身份，不等于 asset_id。
3. 每个 asset 必须有 license。
4. 每个 asset 必须有 checksum。
5. 每个 asset 必须有 normalized status。
6. 每个 asset 必须说明是否可用于 EBench export。
7. 每个 asset 必须说明 physics readiness。
8. 每个 asset 必须有 provenance。
9. 每个正式 package 必须有 asset lock；`fat` 和 `locked` 是资产 materialization 模式。
10. USD reference 必须来自 resolver 结果，不允许手写不受控路径。

### 11.2 asset_manifest.yaml 示例

```yaml
schema_version: asset-manifest/v0.2
assets:
  - asset_id: workbench_table_basic_v1
    role: support_surface
    asset_type: workbench_table
    canonical_usd: assets/objects/workbench_table_basic_v1/model.usd
    collision_usd: assets/objects/workbench_table_basic_v1/collision.usd
    license: CC-BY-4.0
    sha256: "sha256:..."
    normalized: true
    normalized_by: convert_asset
    affordances:
      - support_surface
      - static
    physics:
      rigid_body: false
      collision: static_mesh
      scale_meters: 1.0

  - asset_id: sample_bottle_50ml_v1
    role: manipulated_object
    asset_type: bottle
    canonical_usd: assets/objects/sample_bottle_50ml_v1/model.usd
    collision_usd: assets/objects/sample_bottle_50ml_v1/collision.usd
    license: CC-BY-4.0
    sha256: "sha256:..."
    normalized: true
    normalized_by: convert_asset
    affordances:
      - pickable
      - container
      - transparent
    physics:
      rigid_body: true
      mass_kg: 0.08
      collision: convex_decomposition
      friction: 0.45
```

### 11.3 asset_lock.yaml 示例

```yaml
schema_version: asset-lock/v0.2
lock_id: workbench_pick_place_0001_asset_lock
created_by: scenario-forge
assets:
  workbench_table_basic_v1:
    source_kind: curated_registry
    source_uri: registry://scenario-forge/workbench_assets/workbench_table_basic/v1
    resolved_path: assets/objects/workbench_table_basic_v1/model.usd
    content_sha256: "sha256:aaa..."
    metadata_sha256: "sha256:bbb..."
    license: CC-BY-4.0
    normalized_package_sha256: "sha256:ccc..."
    resolver_version: scenario-forge-asset-resolver/0.2.0

  sample_bottle_50ml_v1:
    source_kind: reconstructed_or_curated
    source_uri: registry://scenario-forge/workbench_assets/sample_bottle_50ml/v1
    resolved_path: assets/objects/sample_bottle_50ml_v1/model.usd
    content_sha256: "sha256:ddd..."
    metadata_sha256: "sha256:eee..."
    license: CC-BY-4.0
    normalized_package_sha256: "sha256:fff..."
    resolver_version: scenario-forge-asset-resolver/0.2.0
```

### 11.4 fat package 规则

fat package 必须满足：

```text
1. scene/main.usda 中引用的所有本地 USD 文件都存在。
2. USD 文件引用的材质和贴图都存在。
3. assets/asset_manifest.yaml 中登记的每个 asset 都有本地文件。
4. locks/asset_lock.yaml 中每个 checksum 都能复算通过。
5. 每个 asset 都有 license 信息。
6. 每个 manipulated object 都有 physics profile。
7. 每个 pickable object 都有 collision 信息。
8. 每个 simulator-specific asset export 都放在 adapters/<target>/，不能污染核心资产。
```

### 11.5 locked package 规则

locked package 可以不 materialize 所有资产，但必须满足：

```text
1. asset_lock.yaml 中记录完整 source_uri、version、sha256、license、resolver。
2. resolver 可以在离线 cache 或指定 registry 中恢复资产。
3. 任何外部 URI 都不能没有 checksum。
4. 任何 external asset 都不能直接出现在 scene/main.usda 里，必须通过 resolver 生成可复现路径。
5. EBench export 前必须 materialize 或确认 EBench runner 有相同 resolver/cache。
```

### 11.6 开发默认策略

默认策略：

```text
本地开发：fat package by default。
CI：fat package + checksum validation。
benchmark suite：fat package or locked suite with registry snapshot。
EBench export：prefer fat package。
大型资产库：允许 content-addressed dedupe，但 package 必须有 lockfile。
```

---

## 12. USD Scene Compiler

### 12.1 为什么需要 USD Scene Compiler

Scenario Forge 不应该让任务生成器直接手写 USD。任务生成器应该产出结构化 `scene/instances.yaml` 和 layout constraints，USD Scene Compiler 负责把它们编译成 `scene/main.usda`。

这样做的好处：

- YAML/JSON 是任务语义真相来源。
- USD 是 simulator-friendly 表达。
- 同一个 scene_instances 可以导出不同 simulator 格式。
- 可以统一处理 scale、up-axis、references、metadata、collision、lighting、robot spawn。
- 可以统一插入 instance_id、asset_id、semantic_tags。

### 12.2 scene/instances.yaml 示例

```yaml
schema_version: scene-instances/v0.2
coordinate_system:
  units: meters
  up_axis: Z
instances:
  - id: workbench_table_001
    asset_id: workbench_table_basic_v1
    role: support_surface
    pose:
      xyz: [0.0, 0.0, 0.0]
      wxyz: [1.0, 0.0, 0.0, 0.0]
    semantic_tags:
      - table
      - static
      - support_surface

  - id: sample_bottle_001
    asset_id: sample_bottle_50ml_v1
    role: manipulated_object
    pose:
      xyz: [0.45, 0.0, 0.92]
      wxyz: [1.0, 0.0, 0.0, 0.0]
    semantic_tags:
      - bottle
      - pickable
      - container
      - workbench_assets
    initial_state:
      upright: true
      contains_liquid: false

  - id: target_zone_001
    asset_id: target_marker_zone_v1
    role: target_zone
    pose:
      xyz: [0.65, 0.0, 0.91]
      wxyz: [1.0, 0.0, 0.0, 0.0]
    semantic_tags:
      - zone
      - target
      - non_physical_marker
```

### 12.3 生成的 USD 应包含什么

`scene/main.usda` 至少应该包含：

```text
1. root Xform。
2. units / up-axis metadata。
3. 每个 instance 的 Xform。
4. 每个 instance 对 asset USD 的 reference。
5. pose transform。
6. custom metadata：scenario_instance_id、asset_id、role、semantic_tags。
7. robot spawn。
8. basic lights。
9. optional cameras。
10. optional physics scene metadata。
```

### 12.4 USD 示例

```usda
#usda 1.0
(
    metersPerUnit = 1
    upAxis = "Z"
)

def Xform "World"
{
    def Xform "workbench_table_001" (
        customData = {
            string scenario_instance_id = "workbench_table_001"
            string asset_id = "workbench_table_basic_v1"
            string role = "support_surface"
        }
    )
    {
        double3 xformOp:translate = (0.0, 0.0, 0.0)
        quatd xformOp:orient = (1.0, 0.0, 0.0, 0.0)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient"]
        rel references = @../assets/objects/workbench_table_basic_v1/model.usd@
    }

    def Xform "sample_bottle_001" (
        customData = {
            string scenario_instance_id = "sample_bottle_001"
            string asset_id = "sample_bottle_50ml_v1"
            string role = "manipulated_object"
        }
    )
    {
        double3 xformOp:translate = (0.45, 0.0, 0.92)
        quatd xformOp:orient = (1.0, 0.0, 0.0, 0.0)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:orient"]
        rel references = @../assets/objects/sample_bottle_50ml_v1/model.usd@
    }
}
```

### 12.5 USD Compiler 校验规则

USD Scene Compiler 完成后必须校验：

```text
1. scene/instances.yaml 中每个 asset_id 都能 resolve。
2. 每个 referenced USD 文件存在。
3. 每个 referenced USD 文件路径是包内路径或 lockfile 管理路径。
4. 每个 instance id 唯一。
5. 每个 task predicate 引用的 object/zone 在 scene instances 中存在。
6. 每个 pickable object 有 collision。
7. 每个 manipulated object 有 physics profile。
8. robot base pose 不与静态物体碰撞。
9. 目标物初始 pose 满足 layout constraints。
10. 生成的 USD 能通过 basic parser/load check。
```

---

## 13. Task / Predicate / Metric 设计

### 13.1 task.yaml 示例

```yaml
schema_version: task/v0.2
task_id: workbench_pick_place_0001
task_family: pick_place
domain: scientific_workbench
instruction: "Move the sample bottle onto the target zone."
language_variants:
  - "Place the sample bottle on the marked target area."
  - "Pick up the bottle and put it inside the target zone."
objects:
  manipulated:
    - sample_bottle_001
  targets:
    - target_zone_001
success_predicates:
  - id: success_object_in_zone
    type: object_in_zone
    object: sample_bottle_001
    zone: target_zone_001
    tolerance_m: 0.03
failure_predicates:
  - id: fail_object_dropped
    type: object_dropped
    object: sample_bottle_001
    below_z_m: 0.55
safety_rules:
  - id: safety_no_drop
    type: no_drop
    object: sample_bottle_001
  - id: safety_keep_upright
    type: keep_upright
    object: sample_bottle_001
    max_tilt_deg: 30
```

### 13.2 predicates.yaml 示例

```yaml
schema_version: predicates/v0.2
predicate_definitions:
  object_in_zone:
    parameters:
      object: instance_id
      zone: instance_id
      tolerance_m: float
    evaluator_hint:
      geometry_relation: containment_or_distance
      required_observables:
        - object_pose
        - zone_pose
        - zone_bounds

  object_dropped:
    parameters:
      object: instance_id
      below_z_m: float
    evaluator_hint:
      geometry_relation: z_threshold
      required_observables:
        - object_pose
```

### 13.3 metrics.yaml 示例

```yaml
schema_version: metrics/v0.2
metrics:
  - id: task_success
    type: boolean_success
    source_predicate: success_object_in_zone
    primary: true

  - id: completion_time
    type: episode_time
    unit: seconds
    lower_is_better: true

  - id: safety_violation_count
    type: count
    source: safety_rules
    lower_is_better: true
```

### 13.4 产品原则

EBench 可以有自己的 evaluator runtime，但 Scenario Forge 必须把任务语义写清楚。一个任务包不能只靠自然语言 instruction 来定义成功。

每个任务至少要有：

```text
1. instruction
2. success_predicates
3. failure_predicates or safety_rules
4. manipulated objects
5. target objects/zones
6. robot profile
7. metrics
8. validation requirements
```

---

## 14. Robot Profile 设计

### 14.1 robot.yaml 示例

```yaml
schema_version: robot/v0.2
robot_id: franka_panda_tabletop_v1
embodiment: franka_panda
asset_id: franka_panda_usd_v1
base_pose:
  xyz: [0.0, -0.55, 0.0]
  wxyz: [1.0, 0.0, 0.0, 0.0]
action_space: end_effector_delta_pose
control_frequency_hz: 20
sensors:
  - id: front_rgb
    type: rgb
    pose:
      xyz: [0.6, -0.8, 1.2]
      wxyz: [0.9239, 0.3827, 0.0, 0.0]
  - id: wrist_rgb
    type: rgb
capabilities:
  - pick
  - place
  - push
  - press
workspace:
  type: tabletop_reach_sphere
  center_xyz: [0.45, 0.0, 0.85]
  radius_m: 0.75
limits:
  max_payload_kg: 3.0
```

### 14.2 Robot Profile 的作用

Robot profile 不是一个随便写的配置文件，而是任务生成的约束源。它决定：

- 哪些物体可达。
- 哪些 skill 可用。
- 哪些 action space 可导出。
- 哪些 sensor 可用于 evaluation。
- task graph 是否能映射到该 embodiment。
- EBench adapter 如何创建 robot runtime spec。

### 14.3 多机器人策略

RoboGenesis 的跨 robot profile 思路值得吸收。Scenario Forge 应该允许同一 task intent 生成多个 robot-specific package：

```text
workbench_pick_place_0001_franka
workbench_pick_place_0001_ur5
workbench_pick_place_0001_mobile_manipulator
```

但核心任务语义保持一致，robot.yaml 和 layout constraints 根据机器人变化。

---

## 15. Generation Plan：核心中间层

### 15.1 为什么要有 generation_plan.yaml

Scenario Forge 不应该直接从自然语言跳到 scenario package。中间必须有一个可审计、可复现、可调试的 generation plan。

`generation_plan.yaml` 是“生成意图和约束”的合同。

它应该能被以下来源生成：

- 人手写。
- CLI 参数生成。
- LLM planner 生成。
- LabBuilder-style protocol grounder 生成。
- RoboGenesis-style workflow composer 生成。
- SimFoundry-style real-to-sim ingestor 生成。
- 其他外部系统生成。

Scenario Forge core 只要求 generation plan 满足 schema，然后编译成 package。

### 15.2 generation_plan.yaml 示例

```yaml
schema_version: scenario-generation-plan/v0.2
plan_id: workbench_pick_place_plan_0001
domain: scientific_workbench
targets:
  - ebench
  - embodied-eval-os
package_mode: fat
intent:
  task_family: pick_place
  instruction: "Move the sample bottle onto the target zone."
  difficulty: easy
robot:
  profile_id: franka_panda_tabletop_v1
required_assets:
  - role: support_surface
    asset_type: workbench_table
    constraints:
      - type: stable
  - role: manipulated_object
    asset_type: bottle
    affordances: [pickable, container]
    constraints:
      - type: mass_less_than
        kg: 0.5
  - role: target_zone
    asset_type: target_marker
layout_constraints:
  - type: reachable_by_robot
    object_role: manipulated_object
  - type: reachable_by_robot
    object_role: target_zone
  - type: distance_between
    a: manipulated_object
    b: target_zone
    min_m: 0.15
    max_m: 0.35
success_predicates:
  - type: object_in_zone
    object_role: manipulated_object
    zone_role: target_zone
safety_rules:
  - type: no_drop
    object_role: manipulated_object
validation_requirements:
  minimum_level: adapter_static_validated
  required_checks:
    - package_schema
    - asset_lock
    - usd_references
    - predicate_bindings
    - robot_reachability_static
    - ebench_adapter_export
provenance:
  requested_by: benchmark_designer
  source: manual_seed
```

### 15.3 Generation Plan 的产品意义

有了 generation plan，我们就能做到：

- 生成过程可解释。
- 任务失败可 debug。
- 同一 plan 可以重新编译。
- 可以比较不同 generator 的输出质量。
- 可以让 PM / researcher 审核任务意图，而不是只看最终文件。
- 可以把 LabBuilder、SimFoundry、RoboGenesis 的输出统一接入。

---

## 16. EBench Adapter 设计

### 16.1 EBench Adapter 的职责

EBench adapter 不应该改变核心 package，只能派生 export artifacts。

职责：

```text
1. 读取 manifest.yaml。
2. 读取 scene/main.usda。
3. 读取 task/task.yaml。
4. 读取 robot/robot.yaml。
5. 读取 metrics/metrics.yaml。
6. 读取 asset_lock.yaml。
7. 生成 EBench 需要的 package.yaml / task entrypoint / runtime hints。
8. 记录 adapter_report.yaml。
```

### 16.2 adapters/ebench/package.yaml 示例

```yaml
schema_version: ebench-scenario-export/v0.1
source_package:
  package_id: workbench_pick_place_0001
  schema_version: scenario-package/v0.2
entrypoints:
  scene_usd: ../../scene/main.usda
  task: ../../task/task.yaml
  robot: ../../robot/robot.yaml
  metrics: ../../metrics/metrics.yaml
assets:
  asset_lock: ../../locks/asset_lock.yaml
runtime_hints:
  simulator: isaac_or_usd_capable
  reset_policy: deterministic
  max_episode_steps: 300
  success_metric: task_success
adapter_validation:
  status: passed
  report: adapter_report.yaml
```

### 16.3 EBench Export 命令

```bash
scenario-forge export ebench \
  --package ./workbench_pick_place_0001 \
  --out ./workbench_pick_place_0001/adapters/ebench
```

### 16.4 Suite 级 EBench Export

```bash
scenario-forge generate suite \
  --domain scientific_workbench \
  --target ebench \
  --num-tasks 100 \
  --robot franka_panda_tabletop_v1 \
  --package-mode fat \
  --out ./ebench_workbench_suite_v0
```

Suite 结构：

```text
ebench_workbench_suite_v0/
  suite_manifest.yaml
  suite_asset_lock.yaml
  suite_validation_report.yaml
  packages/
    workbench_pick_place_0001/
    workbench_pick_place_0002/
    workbench_pipette_transfer_0001/
  adapters/
    ebench/
      suite_export.yaml
      task_index.yaml
```

---

## 17. Validation Ladder

### 17.1 为什么 validation 是产品壁垒

自动生成任务不难，难的是自动生成可运行、可复现、可评测、有质量的任务。

Scenario Forge 的壁垒不只是 generation，而是 generation + validation + provenance + export。

### 17.2 Validation Level 设计

建议定义明确的验证等级：

```text
L0 generated
  文件生成完成，但未验证。

L1 package_schema_validated
  manifest、task、scene_instances、robot、metrics schema 校验通过。

L2 asset_locked
  asset_manifest 和 asset_lock 校验通过，checksum/license/path 完整。

L3 usd_static_validated
  scene/main.usda references 可解析，USD 文件结构基本可读。

L4 semantic_validated
  task predicates 引用的 instance 存在，role/affordance 匹配。

L5 layout_static_validated
  机器人静态可达性、碰撞初筛、空间约束、安全约束通过。

L6 adapter_static_validated
  EBench adapter export 成功，entrypoints 可解析。

L7 simulator_smoke_validated
  由 adapter 或 downstream runtime 完成 basic load/reset/sanity check。

L8 runtime_evidence_validated
  有实际 episode rollout 或 evaluator evidence。

L9 benchmark_quality_validated
  suite 级覆盖度、难度分布、泛化维度、重复率、稳定性通过。
```

### 17.3 最低可交付标准

对 EBench 自动任务包，最低交付标准建议是：

```text
单个 package：至少 L6 adapter_static_validated。
正式 benchmark suite：至少 L7 simulator_smoke_validated。
高质量公开 benchmark：至少 L9 benchmark_quality_validated。
```

### 17.4 validation_report.yaml 示例

```yaml
schema_version: validation-report/v0.2
package_id: workbench_pick_place_0001
overall_level: adapter_static_validated
overall_status: passed
checks:
  - id: package_schema
    level: L1
    status: passed
    evidence: evidence/static_checks.yaml

  - id: asset_lock
    level: L2
    status: passed
    evidence: evidence/asset_checks.yaml

  - id: usd_references
    level: L3
    status: passed
    evidence: evidence/usd_checks.yaml

  - id: predicate_bindings
    level: L4
    status: passed
    evidence: evidence/semantic_checks.yaml

  - id: robot_reachability_static
    level: L5
    status: passed
    evidence: evidence/layout_checks.yaml

  - id: ebench_adapter_export
    level: L6
    status: passed
    evidence: adapters/ebench/adapter_report.yaml

  - id: simulator_smoke
    level: L7
    status: not_run
    reason: downstream runtime not invoked in this package build
```

### 17.5 不接受的状态伪装

`not_run` 不是 passed。

没有 checksum 不是 locked。

没有 license 不是 release-ready。

USD 文件存在不代表场景可运行。

任务有自然语言 instruction 不代表可评测。

adapter export 成功不代表模型评测成功。

这些规则必须写进文档和 CI。

---

## 18. Benchmark Suite 设计

### 18.1 单任务包不等于 benchmark

一个 scenario package 是任务单元。一个 benchmark suite 是任务集合。

Suite 需要额外定义：

- task families。
- difficulty distribution。
- train/dev/test split。
- OOD split。
- object variation。
- layout variation。
- robot variation。
- metric aggregation。
- asset reuse policy。
- license release policy。
- suite-level validation。

### 18.2 suite_manifest.yaml 示例

```yaml
schema_version: scenario-suite/v0.2
suite_id: ebench_workbench_suite_v0
suite_name: EBench Workbench Suite v0
domain: scientific_workbench
target: ebench
package_mode: fat
packages:
  - package_id: workbench_pick_place_0001
    path: packages/workbench_pick_place_0001
    split: dev
    difficulty: easy
    task_family: pick_place
  - package_id: workbench_pipette_transfer_0001
    path: packages/workbench_pipette_transfer_0001
    split: test
    difficulty: hard
    task_family: pipette_transfer
coverage:
  task_families:
    pick_place: 30
    container_sorting: 20
    pipette_transfer: 30
    sample_staging: 20
  difficulties:
    easy: 30
    medium: 40
    hard: 30
  robots:
    franka_panda: 100
validation:
  report: suite_validation_report.yaml
assets:
  suite_asset_lock: suite_asset_lock.yaml
exports:
  ebench: adapters/ebench/suite_export.yaml
```

### 18.3 Suite Quality Metrics

Suite 级质量指标：

```text
1. Task diversity：任务类型多样性。
2. Object diversity：物体种类和实例变化。
3. Layout diversity：布局变化。
4. Difficulty balance：难度分布。
5. Predicate coverage：成功条件类型覆盖。
6. Safety coverage：安全规则覆盖。
7. Robot reachability pass rate：机器人可达性通过率。
8. Asset reuse ratio：资产复用比例，避免重复包膨胀。
9. License completeness：license 完整率。
10. Runtime smoke pass rate：仿真 smoke test 通过率。
11. OOD split clarity：OOD 维度清晰度。
12. Leakage risk：train/dev/test 间重复风险。
```

---

## 19. Domain Packs

### 19.1 为什么需要 Domain Pack

不要一开始追求“生成全世界所有 embodied tasks”。那会把产品做散。

Scenario Forge 应该先做 domain pack。每个 domain pack 是一套任务生成知识：

```text
domain ontology
asset vocabulary
affordance rules
task families
atomic skills
layout constraints
success predicates
safety rules
metric presets
robot compatibility
benchmark split policy
```

### 19.2 第一批 Domain Pack

建议第一批：

1. `scientific_workbench`
   核心主线。对齐 LabBuilder、RoboGenesis、LabVLA。

2. `tabletop_manipulation`
   通用机械臂桌面任务，作为基础能力验证场。

3. `real2sim_manipulation`
   对齐 SimFoundry-style 输入，从真实视频/scan 生成 twin/cousin 任务。

### 19.3 scientific_workbench pack 内容

```text
configs/domain_packs/scientific_workbench/
  domain.yaml
  asset_vocabulary.yaml
  affordances.yaml
  hazards.yaml
  task_families.yaml
  atomic_skills.yaml
  predicates.yaml
  safety_rules.yaml
  layout_constraints.yaml
  robot_profiles.yaml
  metrics.yaml
  suite_templates.yaml
```

### 19.4 task_families 示例

```yaml
schema_version: task-families/v0.2
task_families:
  pick_place:
    required_roles:
      - manipulated_object
      - target_zone
      - support_surface
    allowed_skills:
      - move_to_object
      - grasp
      - move_to_zone
      - release
    success_predicates:
      - object_in_zone

  container_sorting:
    required_roles:
      - source_container
      - destination_zone
      - distractor_objects
    allowed_skills:
      - identify
      - grasp
      - place
    success_predicates:
      - object_in_zone
      - distractors_unchanged

  pipette_transfer:
    required_roles:
      - pipette
      - source_container
      - target_container
      - tip_rack
    allowed_skills:
      - grasp_tool
      - aspirate
      - dispense
      - dispose_tip
    success_predicates:
      - liquid_transferred
      - no_spill
```

---

## 20. 系统架构总览

### 20.1 核心分层

```text
scenario_forge/
  core/
    errors.py
    identifiers.py
    paths.py
    contracts.py

  schemas/
    package/
    generation_plan/
    task/
    scene/
    robot/
    assets/
    validation/
    suite/

  generation/
    protocols/
    skills/
    workflows/
    layout/
    cousins/
    suite/

  assets/
    registry/
    resolver/
    locks/
    manifests/
    normalization/
    licenses/
    physics/

  scene/
    usd_compiler/
    layout_compiler/
    instance_binding/

  task/
    task_compiler/
    predicate_binding/
    metric_binding/

  validation/
    package_checks/
    asset_checks/
    usd_checks/
    semantic_checks/
    layout_checks/
    adapter_checks/
    suite_checks/

  artifacts/
    package_writer/
    provenance/
    evidence/
    reports/

  adapters/
    convert_asset/
    ebench/
    embodied_eval_os/
    isaac/
    habitat/
    maniskill/
    omnigibson/
    real2sim/

  cli.py
  sdk.py
```

### 20.2 数据流

```text
BenchmarkRequest
  ↓
GenerationPlan
  ↓
GroundedProtocol
  ↓
TaskGraph
  ↓
AssetRequirements
  ↓
ResolvedAssets + AssetLock
  ↓
LayoutPlan + SceneInstances
  ↓
USD Scene
  ↓
Task / Robot / Metrics
  ↓
Validation Evidence
  ↓
ScenarioPackage
  ↓
EBench Export
```

### 20.3 Adapter 原则

核心层不 import simulator SDK。

Adapters 可以生成 simulator-specific artifacts，但不能改变 portable manifest。

ConvertAsset 通过 CLI command plan 调用。

EBench adapter 是下游 export adapter，不是 runtime。

SimFoundry-style real2sim adapter 是外部 pipeline 接入，不是 core。

---

## 21. CLI 产品设计

### 21.1 基础命令

```bash
scenario-forge package scaffold --out ./pkg
scenario-forge package check ./pkg
scenario-forge package migrate --in ./pkg_v01 --out ./pkg_v02 --to scenario-package/v0.2
```

### 21.2 生成单任务

```bash
scenario-forge generate package \
  --domain scientific_workbench \
  --task-family pick_place \
  --robot franka_panda_tabletop_v1 \
  --target ebench \
  --package-mode fat \
  --out ./workbench_pick_place_0001
```

### 21.3 从自然语言生成

```bash
scenario-forge generate package \
  --domain scientific_workbench \
  --prompt "Move the sample bottle onto the target zone." \
  --robot franka_panda_tabletop_v1 \
  --target ebench \
  --package-mode fat \
  --out ./workbench_pick_place_0001
```

### 21.4 从 protocol 生成

```bash
scenario-forge generate package \
  --domain scientific_workbench \
  --protocol ./inputs/protocol.yaml \
  --robot franka_panda_tabletop_v1 \
  --target ebench \
  --package-mode fat \
  --out ./workbench_protocol_task_0001
```

### 21.5 从真实视频生成

```bash
scenario-forge ingest real2sim \
  --source-video ./inputs/workbench_surface.mp4 \
  --domain scientific_workbench \
  --target ebench \
  --generate-twin \
  --generate-cousins 20 \
  --package-mode fat \
  --out ./real2sim_workbench_suite_001
```

### 21.6 生成 suite

```bash
scenario-forge generate suite \
  --suite-id ebench_workbench_suite_v0 \
  --domain scientific_workbench \
  --target ebench \
  --robot franka_panda_tabletop_v1 \
  --num-tasks 100 \
  --task-families pick_place,container_sorting,pipette_transfer,sample_staging \
  --difficulties easy:30,medium:40,hard:30 \
  --package-mode fat \
  --out ./ebench_workbench_suite_v0
```

### 21.7 验证 suite

```bash
scenario-forge suite check ./ebench_workbench_suite_v0 \
  --minimum-level adapter_static_validated
```

### 21.8 导出 EBench

```bash
scenario-forge export ebench \
  --suite ./ebench_workbench_suite_v0 \
  --out ./ebench_workbench_suite_v0/adapters/ebench
```

---

## 22. Python SDK 设计

### 22.1 SDK 示例

```python
from scenario_forge import ScenarioForge

forge = ScenarioForge.load_default()

suite = forge.generate_suite(
    suite_id="ebench_workbench_suite_v0",
    domain="scientific_workbench",
    target="ebench",
    robot="franka_panda_tabletop_v1",
    num_tasks=100,
    task_families=["pick_place", "container_sorting", "pipette_transfer"],
    package_mode="fat",
)

report = forge.validate_suite(suite, minimum_level="adapter_static_validated")
forge.export_ebench(suite)
```

### 22.2 SDK 原则

SDK 不应该暴露大量 simulator 细节。它应该暴露 Scenario Forge 的核心概念：

```text
GenerationPlan
ScenarioPackage
AssetRegistry
AssetLock
TaskGraph
SceneInstances
ValidationReport
Suite
AdapterExport
```

---

## 23. 阶段规划总览

路线分成多个阶段。每个阶段都产出可用成果，而不是只做基础设施。

```text
Phase 0：愿景锁定与 v0.2 contract 草案
Phase 1：Fat Package / Asset Lock 基础
Phase 2：Package v0.2 包格式固化
Phase 3：USD Scene Compiler
Phase 4：Task Graph / Predicate / Metric Compiler
Phase 5：EBench Adapter v0
Phase 6：RoboGenesis-style Workflow Generator
Phase 7：LabBuilder-style Layout Generator
Phase 8：SimFoundry-style Real2Sim / Cousin Ingestion
Phase 9：Suite Generator / Benchmark Factory
Phase 10：Suite Quality Evidence
Phase 10.1-10.5：Pre-Phase-11 Golden Pack / EOS Import / Runtime Smoke Gates
Phase 11：Workbench UI / Human Review / Dataset Release Flow
Phase 12：Ecosystem Integration / Registry / Multi-simulator Adapters
```

---

## 24. Phase 0：愿景锁定与 v0.2 Contract 草案

### 24.1 目标

把 Scenario Forge 从 bootstrap package compiler 升级为 EBench task package factory 的产品方向写进 docs。

### 24.2 产出

```text
docs/strategy/scenario-forge-ebench-auto-factory-roadmap.md
docs/design/package-v0.2.md
docs/design/asset-lock.md
docs/design/usd-scene-compiler.md
docs/design/ebench-adapter.md
```

### 24.3 决策

```text
1. v0.2 是 product format，不被 v0.1 限制。
2. package mode 默认 fat。
3. 每个正式 package 必须有 asset_lock.yaml。
4. scene/main.usda 是标准场景入口。
5. generation_plan.yaml 是标准生成入口。
6. EBench adapter 是 first-class target。
```

### 24.4 验收标准

```text
1. 文档中明确 package structure。
2. 文档中明确 asset lock schema。
3. 文档中明确 validation ladder。
4. 文档中明确 EBench export contract。
5. README 定位与 docs 一致。
```

---

## 25. Phase 1：Fat Package / Asset Lock 基础

Status: implemented for local package scope. Phase 1 now provides asset manifest reading, asset lock generation,
sha256 calculation, license and local file checks, USD reference lock checks, `assets lock`,
`assets check`, and `package check --require-asset-lock`. Registry/resolver infrastructure remains
later asset-infrastructure work.

### 25.1 目标

从第一阶段开始就建立可复现资产机制。

### 25.2 产出

```text
src/scenario_forge/assets/lock.py
src/scenario_forge/assets/manifest.py
src/scenario_forge/assets/checksum.py
src/scenario_forge/assets/licenses.py
src/scenario_forge/artifacts/package_writer.py
schemas/asset-lock/v0.2.json
schemas/asset-manifest/v0.2.json
```

### 25.3 功能

```text
1. 读取 asset_manifest.yaml。
2. 生成 asset_lock.yaml。
3. 计算 sha256。
4. 检查 license。
5. 校验 local asset 文件是否存在。
6. 校验 USD reference 是否指向 locked asset。
7. package check 增加 asset lock 检查。
```

### 25.4 命令

```bash
scenario-forge assets lock ./pkg
scenario-forge assets check ./pkg
scenario-forge package check ./pkg --require-asset-lock
```

### 25.5 验收标准

```text
1. 没有 asset_lock.yaml 的 EBench target package 检查失败。
2. checksum 不匹配检查失败。
3. license 缺失检查失败。
4. scene/main.usda 引用未登记资产检查失败。
5. fat package 中 assets/ 缺文件检查失败。
```

---

## 26. Phase 2：Package v0.2 包格式固化

Status: implemented for scaffold/load/check scope. Phase 2 now fixes the
`scenario-package/v0.2` manifest contract, default v0.2 scaffold layout,
v0.2 JSON Schema artifact, v0.2 package validation, and v0.2 scene entrypoint
discovery for asset-lock USD reference checks. USD compilation, adapter export,
nested schema validation, and migration remain later work.

### 26.1 目标

把 package contract 从 v0.1 bootstrap 升级到 v0.2 product format，让后续 USD compiler
和 EBench adapter 都围绕稳定 manifest 工作。

### 26.2 产出

```text
src/scenario_forge/package.py
src/scenario_forge/scaffold.py
src/scenario_forge/schemas/jsonschema/scenario-package-v0.2.schema.json
src/scenario_forge/schemas/v2/
tests/test_package_validator.py
tests/test_cli.py
tests/test_asset_schemas.py
```

### 26.3 功能

```text
1. package scaffold 默认生成 v0.2 目录结构。
2. load_package_manifest 支持 v0.1 和 v0.2。
3. v0.2 manifest 校验 package_id、package_mode、targets、entrypoints、assets、validation、provenance。
4. package check 校验 v0.2 引用文件存在。
5. v0.2 package 默认要求并检查 locks/asset_lock.yaml。
6. assets check 可以从 v0.2 entrypoints.scene_usd 找到 USD 场景。
```

### 26.4 验收标准

```text
1. scenario-forge package scaffold --out ./pkg 生成 scenario-package/v0.2。
2. scenario-forge package check ./pkg 通过 v0.2 starter package。
3. 缺失 metrics/metrics.yaml 等 v0.2 引用文件时 package check 失败。
4. validation.minimum_required_level 只能使用 validation ladder 的命名等级，not_run 不允许伪装成等级。
5. scenario-package-v0.2.schema.json 存在并可解析。
```

---

## 26A. Later Work：Asset Registry / Resolver / ConvertAsset Boundary

### 26A.1 目标

把资产来源标准化，让 task generator 面对 asset_id，而不是文件路径。

### 26A.2 产出

```text
src/scenario_forge/assets/registry.py
src/scenario_forge/assets/resolver.py
src/scenario_forge/assets/asset_query.py
src/scenario_forge/assets/physics_profile.py
src/scenario_forge/adapters/convert_asset.py
configs/assets/curated_registry.yaml
examples/assets/minimal_workbench_assets/
```

### 26A.3 功能

```text
1. 根据 asset_id resolve USD 文件。
2. 根据 asset_type + affordances 搜索候选资产。
3. 选择 license 合规资产。
4. 输出 resolved asset package。
5. 调用 ConvertAsset command plan 规范化非 USD 资产。
6. 写入 asset_manifest 和 asset_lock。
```

### 26A.4 资产查询示例

```yaml
query:
  asset_type: bottle
  affordances:
    - pickable
    - container
  domain_tags:
    - workbench_assets
  max_mass_kg: 0.5
  license_allowlist:
    - CC-BY-4.0
    - Apache-2.0
```

### 26A.5 验收标准

```text
1. 给定 asset_id 可以 resolve 到本地 USD。
2. 给定 affordance query 可以返回候选资产。
3. 非 USD 资产生成 ConvertAsset normalize plan。
4. resolver 输出能写入 asset_lock。
5. package check 能验证 resolved assets。
```

---

## 27. Phase 3：USD Scene Compiler

Status: implemented for static USDA reference-stage scope. Phase 3 now provides
`scene/instances.yaml` loading, asset-lock-backed `asset_id` resolution, pure
Python USDA stage writing, instance customData metadata, robot spawn metadata,
basic light/camera prims, static locked-reference checks, predicate-to-instance
binding checks, a `scene-instances/v0.2` JSON Schema artifact, and
`scenario-forge scene compile`. Runtime USD loading, physics smoke checks,
layout solving, and richer semantic physics validation remain later adapter or
layout phases.

### 27.1 目标

从 scene instances 和 asset resolver 编译出 `scene/main.usda`。

### 27.2 产出

```text
src/scenario_forge/scene/usd_compiler.py
src/scenario_forge/scene/instance_binding.py
src/scenario_forge/scene/usd_paths.py
src/scenario_forge/validation/usd_checks.py
src/scenario_forge/schemas/jsonschema/scene-instances-v0.2.schema.json
```

### 27.3 功能

```text
1. 读取 scene/instances.yaml。
2. resolve 每个 asset_id。
3. 写出 USD stage。
4. 注入 customData metadata。
5. 写出 robot spawn。
6. 写出 basic lights/cameras。
7. 检查 USD references。
8. 检查 instance id 和 task predicate binding。
```

### 27.4 命令

```bash
scenario-forge scene compile \
  --instances ./pkg/scene/instances.yaml \
  --asset-lock ./pkg/locks/asset_lock.yaml \
  --out ./pkg/scene/main.usda
```

### 27.5 验收标准

```text
1. scene/main.usda 生成成功。
2. 每个 instance 都有对应 USD prim。
3. 每个 prim reference 都指向 locked asset。
4. customData 包含 instance_id 和 asset_id。
5. USD static check 通过。
```

---

## 28. Phase 4：Task Graph / Predicate / Metric Compiler

Status: implemented for `pick_place` static compiler scope. Phase 4 now maps
`task_family=pick_place` to required scene roles, binds the manipulated object
and target zone from `scene/instances.yaml`, writes `task/task.yaml`,
`task/task_graph.yaml`, `task/predicates.yaml`, `task/safety_rules.yaml`, and
`metrics/metrics.yaml`, emits an EBench-readable primary success metric hint,
and exposes `scenario-forge task compile`. Broader task families, natural
language task-intent parsing, and richer semantic validation remain future
generator work.

### 28.1 目标

从 task intent 或 task graph 编译出任务定义、成功条件、安全规则和 metrics。

### 28.2 产出

```text
src/scenario_forge/task/task_compiler.py
src/scenario_forge/task/predicates.py
src/scenario_forge/task/metrics.py
src/scenario_forge/generation/workflows/task_graph.py
src/scenario_forge/schemas/jsonschema/task-v0.2.schema.json
src/scenario_forge/schemas/jsonschema/task-graph-v0.2.schema.json
src/scenario_forge/schemas/jsonschema/predicates-v0.2.schema.json
src/scenario_forge/schemas/jsonschema/metrics-v0.2.schema.json
```

### 28.3 功能

```text
1. task_family → required roles。
2. required roles → scene instance binding。
3. task graph → success predicates。
4. safety rules → validation checks。
5. predicates → EBench metric hints。
6. task.yaml / task_graph.yaml / metrics.yaml 统一生成。
```

### 28.4 验收标准

```text
1. pick_place 任务可以自动生成 task.yaml。
2. success_predicates 引用 scene instance。
3. 缺少 target_zone 时 semantic validation 失败。
4. metric primary success 绑定成功。
5. EBench adapter 能读取 metric hints。
```

---

## 29. Phase 5：EBench Adapter v0

Status: implemented for static package and suite-index export scope. Phase 5
now reads the v0.2 manifest, checks the `ebench` target, validates required
scene/task/robot/metrics/asset-lock files, requires a primary success metric,
writes `adapters/ebench/package.yaml`, `task_entrypoint.yaml`, and
`adapter_report.yaml`, and exports suite-level `task_index.yaml` from
`suite_manifest.yaml`. Runtime execution, trace capture, model adapters, and
leaderboard/reporting remain outside this repo.

### 29.1 目标

让 Scenario Forge 生成的 package 能导出 EBench-compatible package。

### 29.2 产出

```text
src/scenario_forge/adapters/ebench/exporter.py
src/scenario_forge/adapters/ebench/schema.py
src/scenario_forge/adapters/ebench/report.py
schemas/ebench-export/v0.1.json
examples/ebench_export_package/
```

### 29.3 功能

```text
1. 读取 Scenario Forge manifest。
2. 检查 target 包含 ebench。
3. 检查 scene USD、task、robot、metrics、asset_lock。
4. 生成 adapters/ebench/package.yaml。
5. 生成 adapter_report.yaml。
6. suite 级 task index 导出。
```

### 29.4 命令

```bash
scenario-forge export ebench --package ./pkg
scenario-forge export ebench --suite ./suite
```

### 29.5 验收标准

```text
1. 单任务 package 可导出 adapters/ebench/package.yaml。
2. 缺 asset_lock 导出失败。
3. 缺 scene/main.usda 导出失败。
4. 缺 primary success metric 导出失败。
5. adapter_report 记录所有 entrypoint。
```

---

## 30. Phase 6：RoboGenesis-style Workflow Generator

Status: implemented for deterministic domain-pack workflow composition scope. Phase 6 now loads
scientific workbench atomic skills and workflow templates, writes task graphs, predicates,
safety rules, metrics, required assets, and rejects robot profiles missing required capabilities.

### 30.1 目标

把实验 workflow 生成任务图，不再只做单步 pick-place scaffold。

### 30.2 产出

```text
src/scenario_forge/generation/skills/skill_library.py
src/scenario_forge/generation/workflows/workflow_composer.py
src/scenario_forge/generation/workflows/rollout_filter.py
configs/domain_packs/scientific_workbench/atomic_skills.yaml
configs/domain_packs/scientific_workbench/workflow_templates.yaml
```

### 30.3 第一批 atomic skills

```text
move_to_object
grasp
release
move_to_zone
place_on_surface
open_container
close_container
press_button
aspirate
dispense
insert_tip
dispose_tip
wait_for_settle
```

### 30.4 第一批 workflow templates

```text
pick_place
container_sorting
sample_staging
pipette_transfer_light
button_press_instrument
open_place_close
```

### 30.5 验收标准

```text
1. 给定 task_family 自动生成 task_graph.yaml。
2. task_graph 自动推导 required assets。
3. task_graph 自动推导 success predicates。
4. task_graph 自动推导 safety rules。
5. 不支持的 robot capability 会导致 generation plan validation 失败。
```

---

## 31. Phase 7：LabBuilder-style Layout Generator

Status: implemented for deterministic baseline layout scope. Phase 7 now maps required assets
and workflow bindings into `scene/layout.yaml`, `scene/instances.yaml`, layout checks,
package-local placeholder assets where needed, and refreshed asset locks. This is the baseline
for future LabBuilder-style adapter comparison, not a vendored LabBuilder pipeline.

### 31.1 目标

让任务不是随机摆物体，而是 protocol-grounded、安全、可达、可执行的布局。

Phase 7 的工程策略是 baseline-first：

```text
1. 先做 Scenario Forge deterministic layout baseline。
2. 再接 LabBuilder-style protocol/layout outputs。
3. 最后用 golden tasks 做 A/B，决定是否把外部 pipeline 升级为 supported adapter。
```

### 31.2 产出

```text
src/scenario_forge/generation/layout/layout_planner.py
src/scenario_forge/generation/layout/constraint_solver.py
src/scenario_forge/generation/layout/reachability.py
src/scenario_forge/generation/layout/safety.py
configs/domain_packs/scientific_workbench/layout_constraints.yaml
configs/domain_packs/scientific_workbench/hazards.yaml
```

### 31.3 功能

```text
1. required assets → initial layout candidates。
2. robot workspace → reachable placement。
3. safety rules → spatial constraints。
4. layout constraints → scene instances。
5. difficulty → distance/occlusion/clutter variations。
6. layout validation report。
```

### 31.4 难度控制

```yaml
difficulty_profiles:
  easy:
    clutter_level: low
    target_distance_range_m: [0.15, 0.25]
    occlusion: none
    distractor_count: 0
  medium:
    clutter_level: medium
    target_distance_range_m: [0.25, 0.45]
    occlusion: partial
    distractor_count: 2
  hard:
    clutter_level: high
    target_distance_range_m: [0.35, 0.65]
    occlusion: partial
    distractor_count: 5
```

### 31.5 验收标准

```text
1. 给定 generation_plan 自动生成 scene/instances.yaml。
2. 所有 manipulated objects 在 robot workspace 内。
3. safety constraints 可检查。
4. difficulty profiles 对布局产生可解释变化。
5. layout check 报告具体失败原因。
6. golden tasks 能比较 baseline、LabBuilder-style output 和 hand-authored reference。
```

---

## 32. Phase 8：SimFoundry-style Real2Sim / Cousin Ingestion

Status: implemented for importer-first static package scope. Phase 8 now imports
`real2sim-result/v0.1` YAML into v0.2 packages, materializes reconstructed USD assets into
asset manifests/locks, records provenance/evidence, compiles USD, and generates digital cousin
packages while preserving task predicates. It does not import or run SimFoundry code.

### 32.1 目标

接收外部 real-to-sim pipeline 的输出，并把它们标准化成 Scenario Forge package。

Phase 8 的工程策略是 importer-first：

```text
1. 先定义 real2sim-result/v0.1 import contract。
2. 再写 adapters/real2sim/importer.py。
3. SimFoundry-style pipeline 只作为 upstream producer，不进入 core。
4. 所有 reconstructed assets 必须进 asset_manifest + asset_lock。
5. source media、model versions、reconstruction steps 只能进 provenance/evidence。
```

### 32.2 产出

```text
src/scenario_forge/adapters/real2sim/base.py
src/scenario_forge/adapters/real2sim/importer.py
src/scenario_forge/generation/cousins/cousin_plan.py
src/scenario_forge/generation/cousins/cousin_generator.py
schemas/real2sim-result/v0.1.json
schemas/cousin-plan/v0.1.json
```

### 32.3 功能

```text
1. 导入 reconstructed scene metadata。
2. 导入 reconstructed object meshes。
3. 写入 asset_manifest。
4. 生成 asset_lock。
5. 编译 digital twin package。
6. 生成 digital cousin variants。
7. 保持 task semantics 不变。
8. 记录 real2sim provenance。
9. 记录 upstream pipeline license / artifact contract / dependency boundary。
```

### 32.4 cousin_plan.yaml 示例

```yaml
schema_version: cousin-plan/v0.1
base_package: packages/real_workbench_twin_001
cousins:
  count: 20
variation_axes:
  - type: object_substitution
    roles:
      - manipulated_object
    preserve_affordances: true
  - type: pose_perturbation
    max_translation_m: 0.1
    preserve_reachability: true
  - type: distractor_injection
    max_count: 3
  - type: lighting_variation
    presets: [bright, neutral, dim]
constraints:
  - preserve_success_predicates: true
  - preserve_robot_profile: true
  - require_asset_lock: true
```

### 32.5 验收标准

```text
1. real2sim result 可以导入为 package。
2. reconstructed assets 进入 asset_manifest。
3. twin package 可导出 EBench。
4. cousin packages 共享任务语义但有明确变化记录。
5. cousin suite 有 coverage report。
```

---

## 33. Phase 9：Suite Generator / Benchmark Factory

Status: implemented for static suite factory scope. Phase 9 now reads `suite-spec/v0.2`,
generates multiple packages through the workflow/layout/USD/EBench export chain, assigns
task-family, difficulty, and split distributions, and writes suite manifests, coverage,
validation, suite asset-lock summaries, and EBench suite indexes.

### 33.1 目标

从单任务生成进入 benchmark suite 自动生成。

### 33.2 产出

```text
src/scenario_forge/generation/suite/suite_generator.py
src/scenario_forge/generation/suite/splitter.py
src/scenario_forge/generation/suite/coverage.py
src/scenario_forge/artifacts/suite_writer.py
schemas/scenario-suite/v0.2.json
```

### 33.3 功能

```text
1. 根据 suite spec 批量生成 packages。
2. 自动分配 difficulty。
3. 自动分配 splits。
4. 控制 task family distribution。
5. 控制 asset reuse。
6. 生成 suite_manifest。
7. 生成 suite_asset_lock。
8. 生成 suite_validation_report。
9. 导出 EBench suite。
```

### 33.4 suite_spec.yaml 示例

```yaml
schema_version: suite-spec/v0.2
suite_id: ebench_workbench_suite_v0
domain: scientific_workbench
target: ebench
package_mode: fat
robot_profiles:
  - franka_panda_tabletop_v1
num_tasks: 100
task_families:
  pick_place: 30
  container_sorting: 20
  pipette_transfer: 30
  sample_staging: 20
difficulties:
  easy: 30
  medium: 40
  hard: 30
splits:
  dev: 20
  test: 80
variation_axes:
  - object
  - layout
  - instruction_language
  - distractors
validation:
  minimum_package_level: adapter_static_validated
  require_asset_lock: true
  require_suite_coverage_report: true
```

### 33.5 验收标准

```text
1. 一条命令生成 100 个 packages。
2. 每个 package 都有 asset_lock；fat package 同时 materialize assets。
3. suite_manifest 正确索引所有 packages。
4. suite coverage report 记录分布。
5. EBench suite export 成功。
```

---

## 34. Phase 10：Suite Quality Evidence

Status: implemented for construction-quality evidence scope. Phase 10 now writes
`suite_quality_evidence.yaml` with family/split/difficulty distributions, duplicate scene and
instruction rates, split leakage findings, and asset license/checksum completeness. It does not
report model performance or leaderboard metrics.

### 34.1 目标

从“能生成任务包”升级到“能生成高质量 suite construction evidence”。

这里的 quality evidence 只覆盖任务包质量、覆盖度、分布、复现性和验证证据，不生成模型性能
benchmark report，不做 leaderboard，也不替代 EBench / embodied-eval-os 的报告系统。

### 34.2 产出

```text
src/scenario_forge/evaluation/coverage.py
src/scenario_forge/evaluation/diversity.py
src/scenario_forge/evaluation/difficulty.py
src/scenario_forge/evaluation/leakage.py
src/scenario_forge/evaluation/stability.py
src/scenario_forge/evaluation/suite_quality_evidence.py
```

### 34.3 质量证据

```yaml
schema_version: suite-quality-evidence/v0.1
suite_id: ebench_workbench_suite_v0
overall_status: passed
coverage:
  task_family_entropy: 0.92
  object_diversity_score: 0.87
  layout_diversity_score: 0.81
  predicate_coverage_score: 0.76
difficulty:
  easy: 30
  medium: 40
  hard: 30
leakage:
  duplicate_scene_rate: 0.0
  duplicate_instruction_rate: 0.04
  shared_asset_policy: allowed_with_variation
assets:
  license_completeness: 1.0
  checksum_completeness: 1.0
runtime:
  evidence_source: downstream_smoke_adapter
  smoke_pass_rate: 0.98
quality_findings:
  - id: hard_task_distribution
    status: passed
    evidence: difficulty distribution matches suite spec
  - id: asset_reproducibility
    status: passed
    evidence: asset lock completeness is 1.0
```

### 34.4 验收标准

```text
1. suite quality evidence 自动生成。
2. 重复任务被识别。
3. split leakage 被识别。
4. difficulty distribution 可解释。
5. asset/license/checksum 完整率可报告。
```

### 34.5 Phase 10.x：进入 Phase 11 前的收口阶段

Phase 10 已经回答“Scenario Forge 能不能批量生成 suite quality evidence”。进入 Phase 11
之前，还需要回答一个更产品化的问题：能不能把一组小而完整的 USD task package 交给
EOS / EBench 接住，并留下可复查证据。

Phase 10.x 不做 UI，不做 leaderboard，不接管模型评测。它只把“静态包工厂”收口成
“可交付给 downstream runtime 的 release candidate”。

Implemented command:

```bash
scenario-forge suite phase10x \
  --suite ./suite \
  --eos-python "$EEOS_PYTHON" \
  --external-evidence examples/phase10x_external_evidence.yaml \
  --runtime-smoke examples/phase10x_runtime_smoke.yaml \
  --strict
```

该命令生成 `evidence/golden_task_pack.yaml`、`external_input_hardening.yaml`、
`eos_static_import.yaml`、`runtime_smoke.yaml` 和 `phase10x_rc_gate.yaml`。其中
runtime smoke 只导入 EOS / EBench 产出的 evidence，不在 Scenario Forge 内启动仿真或模型。

```text
Phase 10.1：Golden USD Task Pack Freeze
  冻结 10-20 个黄金任务，覆盖核心 task families、split、difficulty、asset locks、USD entrypoints。
  目标是得到一个可反复生成、可 debug、可作为所有 downstream gate 输入的小套件。

Phase 10.2：Asset / External Input Hardening
  对内部 layout、LabBuilder-style layout import、SimFoundry-style real2sim/cousin import 做 A/B 证据对齐。
  不判断哪条路线“理念更好”，只看 package validity、asset lock coverage、predicate binding、
  reachability/layout_checks、license/checksum completeness 和 EBench export 是否更稳。

Phase 10.3：EOS Static Import Contract Gate
  用 EOS 的普通项目环境读取 Scenario Forge suite/package 输出，验证 suite_manifest、adapters/ebench、
  task_entrypoint、scene/main.usda、locks/asset_lock.yaml 和 evidence 索引能被 downstream 静态导入。
  这一阶段不启动 simulator，不加载模型，不声称 runtime pass。

Phase 10.4：Runtime Smoke Evidence Gate
  在 EOS 的 backend-specific runtime lane 中挑 1-3 个黄金任务做最小 smoke。
  目标是证明“USD package 能被某个真实 runtime lane 接住并产生 evidence”，不是证明模型分数。

Phase 10.5：Release Candidate Gate
  扩到 50-100 个任务的 RC suite，汇总 package validation、suite_quality_evidence、
  EOS static import evidence、runtime smoke evidence 和已知 blockers，作为进入 Phase 11 的 go/no-go。
```

### 34.6 EOS conda 环境边界

2026-07-04 对 `/cpfs/user/zhuzihou/dev/embodied-eval-os` 的只读检查结论：

```bash
# EOS 普通开发 / 静态导入 / 全局检查环境
export EEOS_ENV_ROOT=/cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-py310
export EEOS_PYTHON="$EEOS_ENV_ROOT/bin/python"
```

该环境当前可执行，Python 版本为 3.10.20。Phase 10.3 的 EOS static import gate
默认使用这个环境。不要使用 DSW 默认 `python`，因为它可能解析到 Isaac Sim 镜像里的
`/usr/bin/python3`。

Runtime smoke 不能复用一个通用解释器糊过去，必须按 lane 选择：

```text
IsaacSim41 local runtime:
  /cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-isaacsim41-py310/bin/python

Newton / EBench experimental runtime:
  /cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/embodied-eval-os-sim-newton-ebench-experimental-py310/bin/python

OpenPI EBench model sidecar:
  /cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-sidecar-openpi-ebench-py311/bin/python
```

OpenPI sidecar 是模型 lane，不替代 `EEOS_PYTHON`。IsaacSim / Newton runtime gate
通过时，只能声明对应 lane 的 smoke evidence；不能把它扩大解释成完整 benchmark 或
leaderboard ready。

### 34.7 进入 Phase 11 的门槛

```text
1. Phase 10.1 黄金任务包可 deterministic regenerate。
2. Phase 10.2 给出 internal layout vs external pipeline 的证据结论和采用策略。
3. Phase 10.3 EOS static import gate 通过，且证据文件被纳入 suite evidence 索引。
4. Phase 10.4 至少一个 backend runtime smoke 产出非 not_run 证据，并清楚标注 lane。
5. Phase 10.5 RC suite 有完整 quality evidence、asset/license/checksum evidence、known blockers。
6. 仍然不在 Scenario Forge 中新增 episode runner、model adapter、leaderboard 或 simulator SDK import。
```

---

## 35. Phase 11：Workbench UI / Human Review / Dataset Release Flow

### 35.1 目标

让产品经理、研究员和 benchmark designer 可以审查和编辑生成结果。

### 35.2 UI 页面

```text
1. Suite Spec Editor
2. Generation Plan Viewer
3. Task Graph Viewer
4. Scene Preview
5. Asset Browser
6. Validation Report Dashboard
7. EBench Export Dashboard
8. Release Checklist
```

### 35.3 Human Review 不等于保守

我们不是因为系统不行才加 human review，而是因为 benchmark release 本身需要审核：

- 任务有没有意义。
- 指标是否合理。
- 资产 license 是否可发布。
- suite 难度是否符合产品目标。
- OOD split 是否设计正确。

自动生成是主线，人类审核是发布治理。

---

## 36. Phase 12：Ecosystem Integration / Registry / Multi-simulator Adapters

### 36.1 目标

让 Scenario Forge 成为跨 evaluator / simulator 的 package standard。

### 36.2 产出

```text
1. Hosted asset registry。
2. Registry snapshot release。
3. Package viewer。
4. EBench integration examples。
5. embodied-eval-os integration examples。
6. Isaac adapter export。
7. Habitat adapter export。
8. ManiSkill adapter export。
9. OmniGibson adapter export。
```

### 36.3 原则

Multi-simulator 是导出能力，不是核心格式污染。

核心永远是：

```text
manifest + task + scene instances + USD + assets + locks + validation + provenance
```

---

## 37. 推荐的 repo 结构演进

```text
scenario-forge/
  README.md
  AGENTS.md
  pyproject.toml
  src/
    scenario_forge/
      core/
      schemas/
      generation/
        protocols/
        skills/
        workflows/
        layout/
        cousins/
        suite/
      assets/
        registry/
        resolver/
        locks/
        manifests/
        normalization/
        physics/
        licenses/
      scene/
        usd_compiler/
        instance_binding/
      task/
        compiler/
        predicates/
        metrics/
      validation/
        package_checks/
        asset_checks/
        usd_checks/
        semantic_checks/
        layout_checks/
        adapter_checks/
        suite_checks/
      artifacts/
        package_writer/
        suite_writer/
        provenance/
        evidence/
      adapters/
        convert_asset/
        ebench/
        embodied_eval_os/
        isaac/
        habitat/
        maniskill/
        omnigibson/
        real2sim/
      cli.py
      sdk.py
  configs/
    domain_packs/
      scientific_workbench/
      tabletop_manipulation/
      real2sim_manipulation/
    assets/
      curated_registry.yaml
    robots/
      robot_profiles.yaml
  schemas/
    jsonschema/
      scenario-package-v0.2.schema.json
      generation-plan-v0.2.json
      asset-lock-v0.2.json
      scene-instances-v0.2.json
      task-v0.2.json
      task-graph-v0.2.json
      robot-v0.2.json
      validation-report-v0.2.json
      suite-v0.2.json
  examples/
    packages/
      workbench_pick_place_fat/
      workbench_pipette_transfer/
    suites/
      ebench_workbench_suite_small/
    assets/
      minimal_workbench_assets/
  docs/
    strategy/
    design/
    operations/
    records/
    reference/
  tests/
    test_asset_lock.py
    test_asset_resolver.py
    test_usd_scene_compiler.py
    test_task_compiler.py
    test_ebench_adapter.py
    test_suite_generator.py
    test_validation_ladder.py
```

---

## 38. 产品 OKR / KPI

### 38.1 North Star Metric

```text
Number of validated EBench-compatible scenario packages generated per suite with reproducible assets and explicit success predicates.
```

中文：

```text
每个 suite 中自动生成并通过验证的、资产可复现且成功条件明确的 EBench-compatible 任务包数量。
```

### 38.2 阶段性 KPI

```text
1. Package generation success rate
2. Asset lock completeness
3. USD reference validity rate
4. Predicate binding validity rate
5. EBench export success rate
6. Runtime smoke pass rate
7. Suite coverage score
8. License completeness
9. Duplicate task rate
10. Human review pass rate
```

### 38.3 产品质量红线

```text
1. 没有 asset lock 的任务包不能进入 EBench export。
2. 没有 success predicate 的任务不能进入 suite。
3. 没有 license 的资产不能进入 release。
4. USD reference 不可解析的 package 不能通过 validation。
5. 任务语义只写在自然语言里是不合格的。
6. not_run 不能伪装成 passed。
```

---

## 39. 风险与直接决策

这里不写“未来再研究”的保守话术，直接给默认决策。

### 39.1 风险：资产包太大

默认决策：

```text
仍然以 fat package / locked package 为标准。
用 content-addressed dedupe 和 suite-level asset store 解决体积问题，不牺牲复现性。
```

### 39.2 风险：USD 生态复杂

默认决策：

```text
Scenario Forge 只生成 USD reference stage 和基础 metadata。
复杂材质、mesh 修复、MDL 转换交给 ConvertAsset 或外部工具。
核心 package 不 import heavy simulator SDK。
```

### 39.3 风险：EBench 真实格式变化

默认决策：

```text
核心 package 不跟 EBench 格式强绑定。
EBench adapter 独立演进。
Scenario Forge 的 portable contract 保持稳定。
```

### 39.4 风险：自动生成任务质量不稳定

默认决策：

```text
引入 validation ladder 和 suite quality evidence。
低质量任务可以生成，但不能进入 release suite。
```

### 39.5 风险：LabBuilder / SimFoundry / RoboGenesis 没有可复用代码

默认决策：

```text
不把外部项目作为 core code source。
先实现 Scenario Forge deterministic baseline。
外部 pipeline 通过 importer / adapter 接入。
用 A/B gate 决定是否扩大采用。
我们吸收能力模型：protocol grounding、layout constraints、real2sim ingestion、cousin generation、workflow composition、rollout filtering。
```

当前事实：

```text
LabBuilder：LabForge 已公开；LabGen / LabTouchstone 仍未完整公开；data/assets 有非商业约束。
SimFoundry：公开论文和项目页显示 real-to-sim 能力很强；稳定可依赖代码和 artifact contract 尚未成为 Scenario Forge 可用前提。
```

进入 Scenario Forge 的唯一方式：

```text
External capability
  -> Scenario Forge importer / adapter
  -> Scenario Forge-owned schemas
  -> asset_manifest + asset_lock
  -> provenance + evidence
  -> package check / adapter check
```

### 39.6 风险：早期 schema 频繁变化

默认决策：

```text
v1.0 前不背兼容包袱。
每次 schema 变化提供 migration。
v0.2 直接面向产品目标设计。
```

---

## 40. 近期执行清单

### 40.1 立即更新文档

```text
1. 添加 docs/strategy/scenario-forge-ebench-auto-factory-roadmap.md。
2. 添加 docs/design/package-v0.2.md。
3. 添加 docs/design/asset-lock.md。
4. 添加 docs/design/usd-scene-compiler.md。
5. 添加 docs/design/ebench-adapter.md。
6. README 增加“EBench task package factory”路线说明。
```

### 40.2 立即更新 package scaffold

Status: implemented in Phase 2 scaffold/load/check scope. `scenario-forge package scaffold`
now generates the v0.2 product layout:

```text
manifest.yaml
generation_plan.yaml
scene/main.usda
scene/instances.yaml
task/task.yaml
task/task_graph.yaml
robot/robot.yaml
metrics/metrics.yaml
assets/asset_manifest.yaml
locks/asset_lock.yaml
evidence/validation_report.yaml
provenance/provenance.yaml
adapters/ebench/package.yaml
```

Adapter files remain future generated artifacts; the current starter focuses on
the portable manifest, package entrypoints, assets, locks, evidence, and provenance.

### 40.3 立即新增测试

```text
tests/test_asset_lock.py
tests/test_fat_package.py
tests/test_usd_scene_compiler.py
tests/test_predicate_bindings.py
tests/test_ebench_adapter.py
tests/test_package_v02_scaffold.py
```

### 40.4 立即新增 CLI

```text
scenario-forge assets check
scenario-forge assets lock
scenario-forge scene compile
scenario-forge export ebench
scenario-forge generate package
scenario-forge generate suite
```

### 40.5 立即构建最小演示

第一个 demo 不要太复杂：

```text
Domain: scientific_workbench
Task family: pick_place
Robot: franka_panda_tabletop_v1
Assets: workbench_table, sample_bottle, target_marker, franka
Package mode: fat
Target: EBench
Validation level: adapter_static_validated
```

Demo 命令：

```bash
scenario-forge generate package \
  --domain scientific_workbench \
  --task-family pick_place \
  --robot franka_panda_tabletop_v1 \
  --target ebench \
  --package-mode fat \
  --out examples/packages/workbench_pick_place_fat

scenario-forge package check examples/packages/workbench_pick_place_fat \
  --minimum-level adapter_static_validated
```

---

## 41. 最小可行产品：MVP 定义

### 41.1 MVP 不是普通 scaffold

MVP 必须证明：

```text
Scenario Forge 能自动生成一个带真实资产锁、USD 场景、任务语义、机器人配置、成功条件、验证报告和 EBench export 的 package。
```

### 41.2 MVP 必须包含

```text
1. generation_plan.yaml
2. asset_manifest.yaml
3. asset_lock.yaml
4. scene/instances.yaml
5. scene/main.usda
6. task/task.yaml
7. robot/robot.yaml
8. metrics/metrics.yaml
9. evidence/validation_report.yaml
10. adapters/ebench/package.yaml
```

### 41.3 MVP 不需要包含

```text
1. 真正运行 EBench episode。
2. 大规模 suite。
3. 复杂 real-to-sim。
4. 完整 LabBuilder-style chemical safety。
5. 完整 RoboGenesis-style demonstration export。
6. 多 simulator runtime。
```

MVP 的关键是把 package factory 的端到端链路打通。

---

## 42. Product Bet：我们真正的壁垒是什么

Scenario Forge 的壁垒不是“能生成一个 3D 场景”。很多项目都能生成场景。

真正壁垒是：

```text
1. 自动生成 embodied evaluation 任务。
2. 任务语义明确。
3. USD 场景可加载。
4. 资产可复现。
5. 成功条件可评测。
6. 安全规则可检查。
7. 验证证据可追溯。
8. 能导出给 EBench。
9. 能批量生成 suite。
10. 能控制 benchmark 质量。
```

一句话：

> Scenario Forge 的护城河是“标准化、可复现、可验证的 embodied evaluation task factory”，不是“又一个场景生成器”。

---

## 43. 与 LabBuilder / SimFoundry / RoboGenesis 的最终关系

最终关系图：

```text
                     ┌──────────────────────────┐
                     │      Benchmark Spec       │
                     └────────────┬─────────────┘
                                  │
                                  ▼
                     ┌──────────────────────────┐
                     │     Scenario Forge        │
                     │  Generation Plan Layer    │
                     └────────────┬─────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
┌───────────────┐        ┌────────────────┐        ┌────────────────┐
│ LabBuilder    │        │ RoboGenesis     │        │ SimFoundry      │
│ style ability │        │ style ability   │        │ style ability   │
│               │        │                 │        │                 │
│ protocol      │        │ atomic skills   │        │ real-to-sim     │
│ layout        │        │ workflows       │        │ twins/cousins   │
│ safety        │        │ rollout filters │        │ reconstructed   │
│ reachability  │        │ demos           │        │ assets          │
└───────┬───────┘        └───────┬────────┘        └───────┬────────┘
        │                        │                         │
        └────────────────────────┼─────────────────────────┘
                                 ▼
                  ┌────────────────────────────┐
                  │ Scenario Package Compiler   │
                  │ manifest / USD / task /     │
                  │ assets / locks / validation │
                  └─────────────┬──────────────┘
                                ▼
                  ┌────────────────────────────┐
                  │        EBench Export        │
                  └────────────────────────────┘
```

---

## 44. 关键命名建议

### 44.1 产品级命名

```text
Scenario Forge
  Product identity：EBench task package factory
  Technical identity：portable scenario package compiler
```

### 44.2 内部模块命名

```text
Generation Plan
Asset Resolver
Asset Lock
USD Scene Compiler
Task Graph Compiler
Predicate Binder
Validation Ladder
EBench Exporter
Suite Factory
Domain Pack
Cousin Generator
```

### 44.3 避免命名

不要把项目改名为 LabForge / LabBuilder / RoboGenesis / SimFoundry 的变体。

这些是能力来源，不是我们的产品身份。

---

## 45. 参考资料

以下资料用于本规划中的能力映射和产品判断：

1. Scenario Forge 当前仓库 README 与架构文档：`https://github.com/jandan138/scenario-forge`
2. LabVLA / RoboGenesis：`https://arxiv.org/abs/2606.13578`
3. LabBuilder：`https://arxiv.org/abs/2605.02288`
4. LabBuilder 项目页：`https://che-0212.github.io/LabBuilder-site/`
5. LabBuilder public repo：`https://github.com/che-0212/LabBuilder`
6. NVIDIA SimFoundry 项目页：`https://research.nvidia.com/labs/gear/simfoundry/`
7. SimFoundry paper：`https://arxiv.org/abs/2606.28276`

2026-07-03 外部能力采用判断还参考了公开 release 状态：

- LabBuilder public repo 当前显示 `LabForge` released，`LabGen` / `LabTouchstone`
  coming soon，且 code / data-assets license 分离。
- SimFoundry public page and paper 展示 real-to-sim / digital-cousin 能力，但没有稳定、
  可直接作为 Scenario Forge core dependency 的 artifact contract。

---

## 46. 最终建议

Scenario Forge 下一步不要只是继续做小 scaffold。它应该直接升级成：

```text
EBench-compatible embodied evaluation task package factory
```

核心路线：

```text
v0.2 package contract
  ↓
fat package / asset lock
  ↓
asset resolver
  ↓
USD scene compiler
  ↓
task graph / predicates / metrics
  ↓
EBench adapter
  ↓
RoboGenesis-style workflow generator
  ↓
LabBuilder-style layout generator
  ↓
SimFoundry-style real2sim and cousins
  ↓
suite generator
  ↓
suite quality evidence
```

最重要的产品决策：

```text
1. 开发阶段就使用 asset lock；正式 EBench export 优先 fat package。
2. scene/main.usda 是标准场景入口。
3. USD 资产必须来自 asset registry / resolver。
4. EBench adapter 是 first-class target。
5. generation_plan.yaml 是生成流程的可审计中间层。
6. v0.2 不背 v0.1 历史包袱。
7. LabBuilder / SimFoundry / RoboGenesis 是 capability inspirations，不是依赖、代码来源或项目边界。
8. Scenario Forge 的核心价值是可复现、可验证、可追溯、可批量的任务包生成。
```

一句话收束：

> **Scenario Forge 要成为 embodied AI evaluation 的“任务包自动工厂”：上游参考 LabBuilder 的实验室布局能力、SimFoundry 的 real-to-sim/cousin 能力、RoboGenesis 的 workflow/atomic-skill 能力，并把这些 capability patterns 映射到 Scenario Forge-owned contracts；中间用自己的 package contract、asset lock、USD compiler、validation ladder 统一标准化；下游稳定导出给 EBench。**
