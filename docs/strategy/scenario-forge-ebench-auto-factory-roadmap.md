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
Phase 11：Automated Review / EOS Execution / Release Gate
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
  目标是证明“Scenario Forge 生成的 USD package 能被某个真实 runtime lane 接住并产生 evidence”，
  不是证明模型分数。只跑 GenManip native task 可以证明后端 lane 可用，但不能替代
  Scenario Forge package-linked runtime evidence。

Phase 10.5：Release Candidate Gate
  扩到 50-100 个任务的 RC suite，汇总 package validation、suite_quality_evidence、
  EOS static import evidence、package-linked runtime smoke evidence 和已知 blockers，
  作为进入 Phase 11 的 go/no-go。
```

2026-07-04 runtime audit update:

```text
EOS / GenManip native smoke:
  status: executed
  retained trace:
    docs/records/evidence/2026-07-04-phase10x-eos-native-smoke/eos_genmanip_native_smoke_trace.json
  evidence boundary:
    backend lane readiness only; trace asset_provenance is genmanip_runtime

Package-linked Phase 10.4 / 10.5 closure:
  EOS runtime evidence now consumes Scenario Forge package output and records
  the package id, USD entrypoint, adapter descriptor, task entrypoint, asset
  lock, and downstream trace. These artifact paths are suite-relative and
  resolve to the expected files inside the package.

  Retained evidence:
    docs/records/evidence/2026-07-04-phase10x-package-linked-runtime-smoke/

  Result:
    Phase 10.x strict gate passed on a 50-task RC suite with
    phase10x_rc_suite_000 loaded by the eos_usd_stage_open_smoke lane.

  Boundary:
    This is package handoff / USD Stage.Open evidence only. It does not claim
    model score, task success, physics fidelity, official EBench reproduction,
    or leaderboard comparability.
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
4. Phase 10.4 至少一个 backend runtime smoke 产出 package-linked executed evidence，
   并清楚标注 lane、Scenario Forge package id、USD entrypoint、task entrypoint、
   asset lock、adapter descriptor 和 trace URI。
5. Phase 10.5 RC suite 有完整 quality evidence、asset/license/checksum evidence、
   package-linked runtime evidence 和 known blockers。
6. 仍然不在 Scenario Forge 中新增 episode runner、model adapter、leaderboard 或 simulator SDK import。
```

### 34.8 Phase 10.6-10.10：真实 EBench 单任务 USD Canary

Phase 10.1-10.5 已经证明了 package handoff：Scenario Forge 能生成带 USD entrypoint
和 asset lock 的包，EOS 能读取 package descriptor 并打开 USD stage。但这里的 USD 仍然是
package-compiler 级别的可加载 stage，不等于某个真实 EBench 任务的官方物体资产 stage。

进入 Phase 11 UI 之前，应该追加一条很窄的 pre-Phase-11 canary：只做
`mobile_manip/apple_to_fruit_bowl`，目标是尽快产出一个真正引用官方 EBench apple、bowl、
scene、Lift2 robot USD 资产的 Scenario Forge package。

已知事实：

```text
EOS retained evidence 已经解析出 apple_to_fruit_bowl 的官方资产：
  task: mobile_manip/apple_to_fruit_bowl
  instruction: Pick up the apple from the dining table and place it into the fruit bowl.
  scene: official EBench simple_pnp/task4 scene USD
  object assets: official EBench apple USD and bowl USD
  robot: official Lift2 robot USD
  camera: GenManip fixed_camera_lift2_simbox.yml

这些源资产位于本地 CPFS EBench-Assets mount，并带有 sha256 / source_path evidence。
这意味着第一版真实资产 USD 不需要等待资产制作，主要工作是 asset intake、package-local
materialization、asset lock、USD composition 和 EOS smoke。
```

推荐拆分：

```text
Phase 10.6：Official EBench Asset Intake Freeze
  固化 apple、bowl、scene、robot、camera 的 source_path、sha256、license/use restriction、
  bundle files 和 provenance。输出只提交小型 YAML/JSON manifest，不提交大 USD asset payload。

Phase 10.7：Single-Task Real-Asset USD Package
  生成一个 `ebench_apple_to_fruit_bowl_canary` package。它的 `scene/main.usda` 必须引用
  package-local materialized copies of official EBench USD assets，而不是 placeholder Xform。
  package 内必须包含 `assets/asset_manifest.yaml`、`locks/asset_lock.yaml`、`scene/instances.yaml`、
  `task/task.yaml`、`metrics/metrics.yaml`、`adapters/ebench/package.yaml`。

Phase 10.8：EOS Package-Linked Real-Asset USD Smoke
  用 EOS bridge 读取该 package，执行 `pxr.Usd.Stage.Open(scene/main.usda)`，并验证 trace 中
  包含 package id、official asset hashes、apple/bowl/scene/robot references。仍然不跑模型。

Phase 10.9：Newton / EBench Visual Canary
  在 EOS runtime lane 中打开同一个 Scenario Forge package，产出至少一帧非空渲染或可检查的
  scene inspection evidence。该阶段可以声明“真实资产 geometry 被 runtime lane 看到”，仍然
  不能声明 task success、official camera parity、material parity 或 leaderboard readiness。
  验收优先使用引擎原生 camera / sensor API 放置一个 `tabletop_overview` 相机，而不是用
  离线拼图或代码里假造截图。相机目标是拍到完整桌面工作面，并让 apple、bowl、scene
  context 和 robot / robot spawn 一起可见。渲染 PNG 必须和 camera pose、engine/runtime、
  package id、scene USD、asset hashes 一起保留，然后用 clean-room visual review 审核：
  图片是否非空、桌面是否完整可见、苹果和碗是否可识别、是否存在严重遮挡/裁切/黑材质/
  贴图丢失/几何破损/placeholder 资产。Phase 10.9 strict pass 需要视觉 review 给出 PASS；
  WARN 只能作为调参依据，不能作为产品展示闭环。

  相机位置决策不能靠临时手调坐标，要作为 Phase 10.9 evidence 的一部分记录下来。2026-07-04
  调研 GenManip `fixed_camera_lift2_simbox.yml` 后，结论是它应该作为官方 camera hint，
  但 Phase 10.9 不能直接声明 official camera parity。该 YAML 里有一个外部 `camera1`
  (`exists: false`, 1280x720, position 约 `[0.2807, -0.0233, 1.6858]`)，也有挂在
  Lift2 robot prim 下的 `left_camera`、`right_camera`、`top_camera` 和 `overlook_camera`
  (`exists: true`)。`overlook_camera` 是优先候选，但只有当 EOS runtime stage 里真实存在
  对应 robot camera prim，并且画面覆盖 apple、bowl、桌面和 robot/spawn 时才能选用。

  更稳妥的 Phase 10.9 策略是：
  1. Scenario Forge package 保留 `fixed_camera_lift2_simbox.yml` 的 source path、hash、
     license/use restriction，把它作为 camera hint。
  2. EOS render CLI 先读取官方 YAML，列出 `camera1`、`overlook_camera` 等候选，并在
     metadata 里记录 selected/skipped/rejected reason。
  3. 如果官方候选不能稳定拍到完整桌面，则 EOS 用引擎原生 camera/sensor API 创建
     `tabletop_overview`，优先复用官方 1280x720/intrinsics，pose 由 runtime 决定。
  4. pose 目标点来自 task anchors，而不是整场景 bbox：table/table_top prim、apple center、
     bowl center、robot spawn。调研当前 canary 时发现 `/World` bbox 会被 environment 背景
     扩到约 516m，不能用于放相机；`/World/Instances/environment_scene/obj_table` 才是
     task-relevant table anchor。object bbox 也可能因为资产 origin/scale 过大，所以 object
     instance translation 比 raw mesh extent 更可靠。
  5. EOS 用 runtime 的 look-at helper 或等价 sensor API，从桌面斜上方 45-60 度视角放置
     camera，距离由过滤后的 workspace anchors/FOV/margin 计算，保留 10-20% 画面余量。
  6. metadata 必须记录 camera source YAML、候选相机、target anchors、最终 pose、FOV 或
     intrinsics、resolution、engine/runtime、scene USD、asset hashes，以及“visual canary only”
     边界。视觉 review 如果给 WARN/FAIL，就调整 pose 重拍，Phase 10.9 不能关闭。

  Phase 10.9 还必须把 Isaac Sim 的 material / MDL runtime closure 纳入验收。调研
  ConvertAsset 的 AAN 经验后，结论是 `Usd.Stage.Open` 成功不等于渲染材质闭合；缺 helper
  MDL、缺 texture、MDL import 写法不兼容、runtime search path 没配好，都可能在 Isaac Sim
  里出现异常红色/粉色 fallback 材质。ConvertAsset 的 AAN-03/AAN-04/AAN-11 分别处理
  USD dependency closure、UsdShade material closure、MDL runtime dependency closure，并会
  记录 `MDLC`、`rtx.mdltranslator`、`usd_mdl`、`Failed to create MDL shade node`、
  `missing texture`、`could not find texture/module` 等日志信号。Phase 10.9 的
  门禁把普通 `MDLC` warning（例如 `C183 unused parameter`）作为 warning evidence，
  不是自动 blocker；MDL compiler error、缺 texture/module、shader node 失败或视觉上出现
  异常红/粉 fallback material 才是 blocker。

  当前 apple-to-bowl canary 也已经出现这个信号：`UsdUtils.ComputeAllDependencies` 能打开
  `scene/main.usda`，大多数 PNG/MDL sidecar 已是 package-local，但仍报告 `OmniPBR.mdl`
  和 `gltf/pbr.mdl` unresolved。它们在 Isaac Sim runtime 中存在：
  `/isaac-sim/kit/mdl/core/Base/OmniPBR.mdl` 和
  `/cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/embodied-eval-os-sim-isaacsim41-genmanip-py310/lib/python3.10/site-packages/omni/mdl/core/mdl/gltf/pbr.mdl`。
  同时 GenManip 官方 task 会设置 `MDL_SYSTEM_PATH=/isaac-sim/materials/:{ASSETS_DIR}/miscs/mdl/ebench/mdl:{ASSETS_DIR}/scene_usds/.../SubUSDs/materials`。
  所以 10.9 strict pass 应记录实际 MDL search roots，并把 `OmniPBR.mdl`、`gltf/pbr.mdl`
  归类为 approved runtime dependencies；如果出现缺 helper MDL、缺 texture、package-escape
  texture literal、MDL compiler error，或视觉 review 看到异常红/粉 fallback material，则
  Phase 10.9 保持 open。这里不能把 ConvertAsset no-MDL 转换逻辑搬进 Scenario Forge；
  no-MDL 只能作为调试/救援路径，不能用于声明 official material parity。

  材质问题的处置边界也要写进 10.9 的工作流：Scenario Forge 负责发现、分类、门禁和证据，
  ConvertAsset 负责 USD/MDL/mesh/texture 转换与修复。若问题是 Scenario Forge package
  自己造成的，例如 lock/provenance 漏资产、贴图路径没有打进 package、adapter 没记录实际
  search root，则在 Scenario Forge 内修复。若问题是 EOS/Isaac Sim runtime search path
  配置，例如 runtime 自带的 `OmniPBR.mdl` 或 `gltf/pbr.mdl` 找不到，则在 EOS adapter/render
  lane 修复并补 evidence。若问题落在资产转换产物本身，例如 MDL import 写法不兼容、
  helper MDL 缺失、texture literal 逃出 package、mesh/USD 转换异常、Isaac Sim 出现红/粉
  fallback，则 Phase 10.9 开 ConvertAsset handoff：交付 failing USD package、dependency
  closure 报告、runtime log、render PNG、资产 source/provenance/hash。ConvertAsset 或外部
  conversion lane 产出修复资产后，Scenario Forge 只重新 ingest、hash、lock、记录 provenance，
  然后重跑 10.9 preflight/render/review；不能在本 repo 里复制 ConvertAsset 的转换逻辑。

  2026-07-04 执行结果：Phase 10.9 已通过一次 EOS/IsaacSim41 engine-native
  `tabletop_overview` visual canary。正式 evidence 保存在
  `docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/`：
  `tabletop_overview.png`、`tabletop_overview_render_metadata.json`、
  `tabletop_overview_runtime.log`、`tabletop_overview_visual_review.md`。
  metadata 记录 `render_status=pass`、`camera.engine_native=true`、
  `material_runtime_preflight.status=pass`、`blocked_dependency_count=0`，
  `MDLC` 仅为 warning evidence；clean-room visual review verdict 为 PASS，
  apple、bowl、桌面、scene context 和 robot/spawn 可见。该证据仍只表示 visual
  canary pass，不表示 task success、official camera/material parity、physics fidelity 或
  leaderboard readiness。

Phase 10.10：EBench Task Contract Canary
  把 `apple_to_fruit_bowl` 的 task semantics、success predicate、robot/camera hints 和 adapter
  contract 固化为一个可复查的 single-task EBench-compatible package。它是进入 Phase 11
  automated review / EOS execution / release gate 的第一个真实任务包样本。
```

时间判断（从 2026-07-04 继续推进的保守口径）：

```text
最快能看到“真的用了官方 apple/bowl/scene/robot USD 的 scene/main.usda”：
  Phase 10.7 结束；如果 CPFS asset mount 继续可用，目标是 2026-07-04 当天或
  2026-07-05 产出第一个本地 canary package。

能比较稳地对外展示“下游 EOS 能打开这个真实资产 USD package”：
  Phase 10.8 结束；目标是 2026-07-05 到 2026-07-06。

能给产品看“一张由引擎原生相机拍到的真实资产桌面渲染图”：
  Phase 10.9 已在 2026-07-04 得到第一张 PASS evidence。该图通过视觉 review skill 的
  clean-room QA，不能被解释为 task success 或 official parity。

能说“这是一个真实 EBench apple-to-bowl 单任务包 canary，不只是 USD 文件”：
  Phase 10.10 结束；目标是 2026-07-06 到 2026-07-07，前提是 license/use restriction
  允许以 locked 或 fat package 形式交付，并且 EOS runtime 依赖环境可用。
```

边界：

- Phase 10.7 的真实 USD 是 packaging / composition milestone，不代表模型会成功把苹果放进碗。
- 大资产不进入 git；git 里只放 manifest、lock、source index、checks 和 retained evidence。
- 如果官方资产 license 不允许复制到公开 fat package，则先交付 locked package；fat package
  只在受控 artifact storage 中保留。
- Scenario Forge 继续不导入 Newton、Isaac、GenManip、OpenPI 或 EBench runner SDK；真实 runtime
  smoke 和 render evidence 保持在 EOS adapter lane。
- Phase 10.9 的渲染图是 visual canary evidence，不代表 official material/camera parity。
  它只能证明“真实资产在某个 runtime lane 中以可检查的方式被看到”。

2026-07-04 执行状态：

```text
Phase 10.6：已完成。
  已新增 official EBench apple-to-bowl asset source manifest 和 asset intake 代码。

Phase 10.7：已完成。
  已生成 /tmp/ebench-apple-to-bowl-canary；scene/main.usda 引用 package-local
  official EBench scene、Lift2 robot、apple、bowl USD assets；package check 和
  asset lock check 通过。

Phase 10.8：已完成。
  EOS bridge 已对 /tmp/ebench-apple-to-bowl-canary 执行 package-linked
  Usd.Stage.Open smoke，runtime_status=executed，stage_open_status=passed。

Phase 10.9：已完成第一版 visual canary。
  EOS render CLI 已在 IsaacSim41 runtime 中打开同一个 package，产出
  tabletop_overview.png；metadata 记录 engine-native camera、MDL runtime roots、
  material preflight pass 和 image sha256；clean-room visual review verdict=PASS。

Phase 10.10：已完成第一版 task contract canary。
  Scenario Forge package 现在包含 `task/task_contract.yaml`，并在 manifest 和
  `adapters/ebench/package.yaml` 中暴露 `task_contract` entrypoint。该 contract 把
  `mobile_manip/apple_to_fruit_bowl` 绑定到官方 instruction、`apple_001`、
  `bowl_001`、`apple_in_bowl` / `object_in_container`、Lift2 robot hint、
  `fixed_camera_lift2_simbox.yml` camera hint，以及 EOS/EBench adapter 边界。
  证据文件包括 `apple_to_bowl_task_contract.yaml`、`apple_to_bowl_adapter_report.yaml`
  和 `phase10_10_task_contract_gate.yaml`。

Retained evidence:
  docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/

仍未完成：
  Phase 11 automated review / EOS execution / release gate；模型运行、task success、physics fidelity、
  official camera/material parity、score release 和 leaderboard comparability 仍不在
  Scenario Forge 10.10 的声明范围内。
```

---

## 35. Phase 11：Automated Review / EOS Execution / Release Gate

Phase 11 不再包含任何必须人工确认的 gate。产品经理、研究员和 benchmark designer
仍然可以查看 dashboard 和证据，但通过/失败结论由自动证据决定：

- 渲染图、关键帧和 USD/Isaac Sim 截图由 `render-visual-reviewer` 做 clean-room
  visual review，输出 PASS/WARN/FAIL。
- package/schema/asset/contract 由 Scenario Forge 静态校验和证据 gate 判断。
- license/release 权限由 policy gate 判断，不能靠视觉 review 放行。
- task success 由 EOS/EBench predicate evaluator 判断，视觉 review 只能辅助发现明显
  视觉异常，不能替代 predicate。
- episode execution、model adapter、runtime trace 和 simulator SDK 仍归 EOS/EBench，
  不进入 Scenario Forge repo。

无人化 gate 的硬规则：

```text
1. 人工查看可以产生 issue、备注或后续需求，但不能把 gate 从 failed/blocked 改成 passed。
2. 每个 gate 都必须有机器可读 evidence，记录 owner、输入 artifact、hash/路径、status/verdict、
   blockers、next_stage 和 claim_boundary。
3. 视觉问题只由 `render-visual-reviewer` 的结构化输出判定；没有该输出时，视觉 gate 为 blocked。
4. 非视觉问题由对应 owner 的 evidence 判定：Scenario Forge 判 package/schema/asset/contract，
   EOS 判 execution/trace/predicate，policy gate 判 license/release 权限。
5. 任一 release-critical gate 缺 evidence、证据过期、输入 artifact 不存在或 owner 不匹配，都必须
   自动 blocked，不能靠口头确认补齐。
```

2026-07-05 用户确认后的规划约束：

```text
Phase 11 和后续 11.x 不再保留“人工看过就通过”的 fallback。

视觉类人工判读全部替换为 render-visual-reviewer skill 的 clean-room evidence：
  overview render、initial/final keyframes、USD/Isaac Sim 截图只能由
  reviewer=render-visual-reviewer 且 review_mode=clean_room_visual_skill 的结构化
  PASS/WARN/FAIL 进入 gate。人可以看图，但人工结论只能变成 issue、retake request
  或 blocker triage，不能成为 gate input。

非视觉类人工判读也必须拆回 owner evidence：
  task success 归 EOS/EBench simulator-state predicate；
  episode lifecycle 归 EOS reset/step/close + trace/log/keyframe evidence；
  license/release 归 policy gate；
  package/schema/asset/contract 归 Scenario Forge static gates。
  visual review 不能替代这些 gate。

产品汇报里的“完成”必须引用 passed gate 和 retained artifact name。没有 gate evidence
就只能说 blocked / failed / pending，不能说人工已经确认通过。
```

自动验收链路：

```text
1. EOS / Isaac Sim 产出 engine-native render 或 execution keyframes，并保留确切路径、
   hash、camera metadata、runtime log 和 trace URI。
2. render-visual-reviewer 只接收图片路径和视觉期望包，按 clean-room 规则输出
   PASS / WARN / FAIL、可见证据和 retake recommendation。它不能读取代码、manifest、
   gate 结果或实现细节。
3. Scenario Forge 只消费结构化 visual-review evidence，并检查 reviewer、
   review_mode、image artifact、upstream gate reference、visible evidence 和 blockers。
4. WARN / FAIL / missing review 都会让视觉 gate failed 或 blocked；修复方式是让
   EOS/renderer/asset pipeline 重新产出 keyframe 或 render，再重新跑 visual review。
5. Phase 11.3 的 simulator-state predicate 和 Phase 11.4 的 visual review 互相不能替代：
   predicate 决定任务是否成功，visual review 决定画面是否足以支撑人工可读的证据包。
6. 只有 Phase 11.0-11.4 都由各自 owner 的 evidence 通过后，Phase 11.5 才能聚合成
   single-task complete evidence bundle；人工口头确认不进入聚合输入。
```

2026-07-05 无人工验收替换表：

```text
原人工步骤：人工看 overview render，判断任务包是否“看起来对”。
替换方式：Phase 11.0 只接受 render-visual-reviewer 的 clean-room PASS evidence，
        再由 Scenario Forge strict visual gate 消费。WARN/FAIL/missing review 都是
        blocked/failed，不能人工改成 PASS。

原人工步骤：人工看执行后截图，判断任务是否成功。
替换方式：任务成功只由 Phase 11.3 EOS/EBench simulator-state predicate 决定。
        Phase 11.4 的 visual review 只证明 initial/final keyframes 可读、无明显
        材质/相机/几何异常；它不能替代 success predicate。

原人工步骤：人工确认“这张图没问题，可以继续”。
替换方式：只能形成 issue、retake request 或 blocker triage。继续推进必须来自
        对应 gate 的 machine-readable evidence：package/schema/asset/contract 归
        Scenario Forge，render/keyframe 归 render-visual-reviewer，execution/predicate
        归 EOS/EBench，license/release 归 policy gate。

原人工步骤：人工决定 release candidate 可以发布。
替换方式：Phase 11.5 / 11.7 只聚合自动 gate 和 policy evidence。只要
        redistribution approval 缺失或 official assets 仍是 research-use，结果就是
        internal RC / blocked-for-public-release。
```

产品口径：

```text
Phase 11.0 关闭后，只能说“overview render 已由视觉 review skill 验收”。
Phase 11.1 关闭后，才能说“EOS 已经能消费 Scenario Forge package 并启动真实 episode”。
Phase 11.2 关闭后，只能说“一次完整 episode 证据已保留”，不能说任务成功。
Phase 11.3 关闭后，才能说“EOS/EBench simulator-state predicate 判断这次苹果入碗成功”。
Phase 11.4 关闭后，才能说“苹果入碗有一次完整执行、predicate 成功和执行后视觉证据”。
Phase 11.5 关闭后，才是用户真正要的第一个 single-task complete evidence bundle：
  一个带真实 USD 资产、task contract、EOS 执行证据、success predicate、前后视觉 review、
  license/release policy 结论的 EBench-compatible 任务包。
如果 license 仍是 research-use 或 redistribution approval 缺失，11.5 结果必须是 internal RC /
blocked-for-public-release，不能叫 public dataset release 或 official score release。
```

### 35.0 Automated Visual Review Gate

替代原来的人工看图步骤。每个 canary 或 release candidate 至少保留一张 engine-native
overview render，并交给 `render-visual-reviewer`：

```text
input:
  render PNG / keyframe PNG
  visual expectation packet
  package id
  task id
output:
  visual_review.yaml 或 visual_review.md
  verdict: PASS / WARN / FAIL
```

PASS 才能继续；WARN/FAIL 必须保留 retake recommendation 或 blocker。该 gate 只判断可见内容：
目标物是否可见、相机是否可用、是否有红/粉 fallback material、严重遮挡、穿模、空画面或明显
几何/材质异常。

2026-07-04 执行结果：apple-to-bowl canary 已产出结构化
`tabletop_overview_visual_review.yaml` 和 `phase11_visual_review_gate.yaml`。
gate status 为 `passed`，blockers 为空，`next_stage=eos_task_execution_integration`。
这关闭 Phase 11.0 的单任务 canary 版本；后续多任务版本仍需在 35.6 扩展验证。

Scenario Forge 在这一阶段只消费 review evidence 并生成 gate evidence，例如
`phase11_visual_review_gate.yaml`。它不读取 simulator SDK，不判断 task success，也不替代
license/release policy。

### 35.1 EOS Task Execution Integration

EOS 读取 Scenario Forge package 和 `task/task_contract.yaml`，映射成 EOS 可执行任务配置。
该阶段的目标不是模型成功，而是证明 runtime 能消费 contract 并启动真实 apple-to-bowl episode。

通过标准：

```text
1. EOS 能读取 manifest、asset lock、adapter descriptor、task entrypoint 和 task contract。
2. EOS 能把 task contract 映射成内部 task execution config。
3. EOS 能启动一次 apple-to-bowl episode。
4. EOS 保留 trace URI、runtime log、reset/step/close 状态和关键帧。
5. 失败也必须结构化记录 blocker，不能口头判断。
```

Scenario Forge 侧只做 evidence adapter / gate：

```text
input evidence:
  schema_version: phase11-eos-task-execution/v0.1
  runtime_owner: embodied-eval-os
  package_id: ...
  task_id: ...
  contract_consumed: true
  execution_config_status: generated
  episode_status: started | completed | blocked | failed
  trace_uri: ...
  runtime_log: ...
  lifecycle:
    reset: passed | failed | blocked
    step: passed | failed | blocked
    close: passed | failed | blocked
  keyframes:
    initial: ...
  blockers: []

output gate:
  schema_version: phase11-task-execution-gate/v0.1
  phase: 11.1
  status: passed | failed
  next_stage: executed_episode_evidence_gate | blocked
```

通过 Phase 11.1 只说明“EOS 能启动并记录 episode”，仍不能声明任务成功、模型能力、物理真实度、
release 通过或 leaderboard 可比。

2026-07-04 Scenario Forge 侧已固化该阶段的 evidence contract、JSON Schema 和 CLI
gate：

```bash
scenario-forge package phase11-task-execution \
  --package <package-dir> \
  --execution-evidence <phase11-eos-task-execution.yaml> \
  --strict
```

Scenario Forge 的单元测试 fixture 不能替代真实 EOS 运行证据。Phase 11.1 必须由
EOS 产出的 `phase11-eos-task-execution/v0.1` evidence 关闭。

2026-07-04 当前真实 canary 状态：Scenario Forge 已保留
`phase11_task_execution_blocked_evidence.yaml`、
`phase11_task_execution_blocked_runtime.log` 和
`phase11_task_execution_gate_blocked.yaml`。严格 gate 结果为 `status=failed`、
`next_stage=blocked`，原因是 EOS 尚未消费 Scenario Forge package / task contract
并启动 apple-to-bowl episode。这是进入 EOS 侧 Phase 11.1 实作的明确 blocker。

2026-07-04 后续推进：EOS 隔离 worktree
`phase11-scenario-forge-execution` 已实现 package consumption / execution config
lane，并在真实 `/tmp/ebench-apple-to-bowl-canary` 上产出
`phase11_eos_task_execution_config_blocked_evidence.yaml`、
`phase11_task_execution_config_trace.json`、
`phase11_task_execution_config_runtime.log` 和
`phase11_task_execution_gate_config_blocked.yaml`。这组证据把 Phase 11.1 blocker
从“EOS 完全没有消费 Scenario Forge package”推进为“EOS 已消费 contract 并生成
execution config，但尚未启动真实 simulator episode”。因此：

```text
11.1.a EOS package discovery: closed for apple-to-bowl canary.
11.1.b EOS execution config generation: closed for apple-to-bowl canary.
11.1.c episode start and initial keyframe: closed for apple-to-bowl canary.
```

随后 EOS 侧修复了 `adapters.ebench.smoke_run` 的 cold-start reset_result timeout
配置和 TraceStore 的 slash-containing episode_id 保存问题，并在
`scenario_forge_phase11_apple_to_bowl_tracefix_20260704T151344Z` run 上产出 live
evidence。Scenario Forge strict gate 已通过，保留证据包括
`phase11_eos_task_execution_live_evidence.yaml`、
`phase11_task_execution_live_trace.json`、
`phase11_task_execution_live_runtime.log`、
`phase11_task_execution_initial_overlook.png` 和
`phase11_task_execution_gate_live.yaml`。

因此 Phase 11.1 已对 apple-to-bowl canary 关闭：EOS 已消费 Scenario Forge package
和 task contract，生成 runtime execution config，启动真实 GenManip/IsaacSim41 episode，
完成 reset、一次 zero-policy step、cleanup close，并保留 trace/log/initial keyframe。
下一阶段不是继续补 11.1，而是 Phase 11.2 completed episode evidence。

早期对现有 EOS `adapters.ebench.smoke_run` 的 runtime 探测也确认：该路径能连接一个已经
启动的 GenManip EvalServer 做 reset/step，但当前 `http://127.0.0.1:8087` 没有 server，
probe 产出 `phase11_genmanip_server_probe_skipped_trace.json`，状态为
`runtime_status=skipped`、`runtime_attempted=true`、
`server_connection_attempted=true`，原因是 connection refused。该 skipped probe 已被
live passed evidence supersede，只作为故障定位历史保留。

### 35.2 Executed Episode Evidence Gate

把 EOS 的真实执行结果回填为 evidence，而不是把 runner 放进 Scenario Forge。

最低 evidence：

```text
schema_version: phase11-executed-episode-evidence/v0.1
package_id: ebench_apple_to_bowl_canary
task_id: mobile_manip/apple_to_fruit_bowl
runtime_owner: embodied-eval-os
episode_status: completed | failed | blocked
trace_uri: ...
runtime_log: ...
keyframes:
  initial: ...
  final: ...
blockers: []
```

Phase 11.2 和 Phase 11.1 的区别是：11.1 接受 `episode_status=started` 作为集成打通；
11.2 必须保留一次完整 episode 的结束状态、final keyframe、trace artifact 和 runtime log。
如果 episode 中途失败，也可以进入 11.2 evidence，但 gate 结果必须是 failed/blocked，并带上
EOS blocker。

2026-07-04 Scenario Forge 侧已固化 11.2 的 evidence contract、JSON Schema 和 CLI
gate：

```bash
scenario-forge package phase11-executed-episode \
  --package <package-dir> \
  --episode-evidence <phase11-executed-episode-evidence.yaml> \
  --strict
```

该 gate 要求 `episode_status=completed`，并检查 trace/log、initial/final keyframe 和
final state 证据。

2026-07-04 最新执行结果：apple-to-bowl canary 已通过 Phase 11.2。EOS 在
GenManip/IsaacSim41 lane 上用 `step_chunk_size=1000` 跑满 `num_steps=1000`，trace 中
保留 terminal `episode_result`，并从 engine-native `overlook_camera.mp4` 抽取
initial/final keyframes。Scenario Forge strict gate 只消费 EOS evidence，并写出
`phase11_executed_episode_gate_completed.yaml`，status=passed，blockers=[]。

保留证据：

```text
phase11_executed_episode_completed_trace.json
phase11_executed_episode_completed_runtime.log
phase11_executed_episode_result_info.json
phase11_executed_episode_completed_evidence.yaml
phase11_executed_episode_initial_overlook.png
phase11_executed_episode_final_overlook.png
phase11_executed_episode_gate_completed.yaml
```

边界：该 episode 已 completed，但 `score=0.0`、`sr=0.0`。因此 Phase 11.2 关闭只证明
“完整 episode 证据已保留”，不证明 apple-to-bowl 成功。下一步必须进入 Phase 11.3，
由 EOS/EBench predicate evidence 记录 `object_in_container(apple_001, bowl_001)` 或等价
predicate 的 true/false/blocked 结果。

技术注记：GenManip 在 episode 000 完成后会立即 reset 到下一个 episode，因此 terminal
response 中可能同时包含 episode 000 的 `episode_result` 和 episode 001 的 reset
observation。11.2 evidence 已显式标注
`observation_status=post_completion_reset_observation`，并以 completed `episode_result`
和 final keyframe 作为 completed episode 的权威 artifact。

### 35.3 Success Predicate Evaluation Gate

EOS/EBench 根据 simulator state 计算 `object_in_container(apple_001, bowl_001)`。
这一步才允许声明 task success。视觉 review 不能替代该 gate。

通过标准：

```text
success_metric: apple_in_bowl
predicate: object_in_container
object: apple_001
container: bowl_001
evaluator_owner: embodied-eval-os-ebench-adapter
predicate_status: true | false | blocked
```

2026-07-04 Scenario Forge 侧已固化 11.3 的 evidence contract、JSON Schema 和 CLI
gate：

```bash
scenario-forge package phase11-success-predicate \
  --package <package-dir> \
  --predicate-evidence <phase11-success-predicate-evaluation.yaml> \
  --strict
```

该 gate 只消费 EOS/EBench predicate evidence，并要求引用的 Phase 11.2 executed episode
gate 已经 passed。真实 apple-to-bowl canary 仍需 EOS/EBench 根据 simulator state 产出
`object_in_container(apple_001, bowl_001)` 之类的 predicate evidence 后才能关闭 Phase 11.3。

2026-07-04 当前执行结果：Phase 11.3 已完成一次自动 predicate gate 评估，但结果为
failed。输入 evidence 为 `phase11_success_predicate_failed_evidence.yaml`，引用已经通过的
`phase11_executed_episode_gate_completed.yaml`；由于 completed episode 的 EOS result 为
`score=0.0`、`sr=0.0`，predicate evidence 记录 `predicate_status=false`，strict gate
输出 `phase11_success_predicate_gate_failed.yaml`，blockers 为：

```text
predicate_status must be true; got False
episode_result_sr_zero
```

这说明自动流程已经正确阻断在 11.3：不能进入“任务成功”的 11.4/11.5 passed 路线。下一步
需要 EOS 接入能完成 apple-to-bowl 的 policy/adapter，或用官方成功 rollout 产出新的
completed episode，再重新运行 11.2 和 11.3。人工看图和 visual review 不能把该 failed
predicate 改成 passed。

11.3 的 blocker 修复路线必须保持 Scenario Forge 边界：

```text
11.3.b successful rollout source selection:
  owner: EOS / EBench adapter, with Scenario Forge consuming only evidence
  goal: 找到能让 apple-to-bowl 成功的真实执行来源。优先调查 GenManip 已有
        demonstration_configs / cuRobo / generalized oracle rule lane；其次调查
        官方 successful rollout 是否可以 package-linked rerun。零动作 policy 只能作为
        failure evidence，不能升级为成功样本。
  evidence: 记录所选来源、run config、task config、policy/oracle identity、runtime
        environment、package id、task id 和 artifact paths。

11.3.c package-linked successful completed episode rerun:
  owner: EOS / GenManip / EBench runtime
  goal: 使用 Scenario Forge apple-to-bowl package 或可证明等价的 package-linked
        execution config，重新跑 completed episode，并保留 terminal episode_result、
        trace、runtime log、initial/final keyframes 和 simulator-state projection。
  evidence: 新的 phase11-executed-episode-evidence/v0.1；如果 rollout 不是直接从
        Scenario Forge package 启动，必须记录 package linkage 或保持 blocked。

11.3.d strict predicate re-gate:
  owner: Scenario Forge gate ingestion
  goal: 只消费 EOS/EBench 的 predicate evidence，重新运行
        scenario-forge package phase11-success-predicate --strict。
  pass condition: predicate_status=true, score/sr evidence consistent with success,
        referenced Phase 11.2 gate passed, blockers=[]。
```

2026-07-05 source-selection update: 11.3.b 的第一候选来源选为 EOS BPL-19R.R2
same-checkpoint online lane，而不是 zero-policy run。该 lane 使用
`pi05-ebench-generalist` checkpoint、`pi05_ebench_all` policy config、
`openpi_ebench_pi05_generalist_sidecar` model profile 和 GenManip native task config
`/cpfs/shared/simulation/zhuzihou/dev/GenManip/configs/tasks/ebench/mobile_manip/test_mini/apple_to_fruit_bowl.yml`。
保留的历史 cohort 证据显示 10 次 EOS online attempts 中 4 次成功：
attempt_005、attempt_006、attempt_007、attempt_009 的 `score=1.0`、
`success_rate=1`。对应历史 evidence root 为 EOS repo 中的
`docs/records/evidence/2026-06-20-bpl19r-r2-pi05-10-attempt-eos-cohort/`，
GenManip retained result root 为
`/cpfs/shared/simulation/zhuzihou/dev/GenManip/saved/eval_results/ebench/bpl19r_r2_pi05_10_attempt_curobo/ebench/mobile_manip/apple_to_fruit_bowl_test_mini/`。

这条选择只关闭“下一步应该用哪条成功 lane 来重跑”的讨论，不关闭 Phase 11.3。
BPL-19R.R2 的历史成功是 debugging/reference evidence，因为它当时消费的是 native
GenManip task config，不是 Scenario Forge package。11.3.c 必须在 EOS 侧新增或使用一个
package-linked wrapper：加载 `/tmp/ebench-apple-to-bowl-canary`，读取
`task/task_contract.yaml`、`adapters/ebench/package.yaml`、`scene/main.usda` 和
`locks/asset_lock.yaml`，把 `mobile_manip/apple_to_fruit_bowl` 映射到上述 native
GenManip config，并在新的 run id / evidence 中记录 package id、task id、task contract、
scene USD、asset lock、mapping source、policy/checkpoint identity 和 runtime env。只有这次
package-linked rerun 产出新的 completed episode、`predicate_status=true` 且 strict gate
passed，Phase 11.3 才能关闭。

2026-07-05 implementation update: EOS worktree
`/root/.config/superpowers/worktrees/embodied-eval-os/phase11-scenario-forge-execution`
已新增 package-linked BPL-19R wrapper 和 CLI：
`adapters/ebench/scenario_forge_bpl19r.py`、
`scripts/run_phase11_scenario_forge_bpl19r_rerun.py`，测试覆盖在
`tests/test_phase11_scenario_forge_bpl19r_rerun.py`。wrapper 已能加载
`/tmp/ebench-apple-to-bowl-canary`，验证 `task_id=mobile_manip/apple_to_fruit_bowl`，
静态映射到 native GenManip config，支持多次 package-scoped attempts 并在第一条成功后停止，
然后输出 package-linkage evidence。Scenario Forge 已保留一次 `attempt_count=10` 的 dry-run
plan evidence：
`docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/phase11_3c_bpl19r_package_linked_plan/phase11_package_linked_bpl19r_rerun.yaml`。
该 evidence 的 `rerun_status=planned`，blocker 为 `live_bpl19r_rerun_not_executed`，
所以它只证明 11.3.c 的入口和 package linkage 已准备好，不证明 episode 成功。

2026-07-05 live update: 11.3.c 已获得第一条 package-linked BPL-19R 成功
evidence。EOS 使用 package-linked wrapper 运行 live multi-attempt rerun，前两次
attempt_000 和 attempt_001 均完成但 `task_success=false`、`score=0.0`；attempt_002
完成并记录 `task_success=true`、`standard_model_score=1.0`。顶层 evidence 为：

```text
docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/phase11_3c_bpl19r_package_linked_live/phase11_package_linked_bpl19r_rerun.yaml
```

该 evidence 记录 `rerun_status=executed`、`selected_success_attempt=attempt_002`、
`blockers=[]`，并声明 claim boundary：这是 Scenario Forge package-linked BPL-19R
rerun evidence，不是 official leaderboard evidence。11.3.c 因此从“live rerun pending”
推进为“package-linked successful rollout retained”。在 bridge 落地前，它仍不等于
Phase 11.3 passed：当时下一步是把 BPL-19R live output 转换或桥接成 Phase 11.2
completed-episode evidence 和 Phase 11.3 predicate evidence，然后跑 strict gates。

2026-07-05 bridge update: EOS worktree 已新增
`scenario_forge_bpl19r_phase11_bridge.py` 和
`run_phase11_scenario_forge_bpl19r_phase11_bridge.py`，把 package-linked
BPL-19R attempt_002 输出投影成 Phase 11.2 / 11.3 strict gate 可消费的 evidence。
Scenario Forge 已保留并通过两条 strict gate：

```text
phase11_executed_episode_bpl19r_success_evidence.yaml
phase11_executed_episode_bpl19r_success_gate.yaml        status=passed
phase11_success_predicate_bpl19r_success_evidence.yaml
phase11_success_predicate_bpl19r_success_gate.yaml       status=passed
```

这关闭 apple-to-bowl canary 的 Phase 11.3.d：成功结论来自 EOS/EBench
predicate evidence 和 BPL-19R retained result，不来自截图、人工确认或 visual review。
claim boundary 仍然是 internal Scenario Forge package-linked evidence，不是 official
leaderboard score release。

具体执行上，优先从 BPL-19R.R1 single-attempt runner 派生 11.3.c，因为它就是 R2 cohort
中 005/006/007/009 成功 attempt 使用的单次在线执行路径。历史样本中 attempt_007 是首选
调试参照：`task_success=true`、`score=1.0`、`sr=1.0`、13 cycles。风险是当前 CLI 不能指定
“重放历史 attempt_007 seed”，所以一次 rerun 不保证成功；11.3.c 需要允许多次 package-scoped
attempt，并保留第一条成功的 completed episode。如果 BPL-19R 输出格式不能直接被
`phase11-executed-episode` evidence builder 消费，EOS 侧还必须补一个小型 trace/evidence
translator，把 BPL-19R native run report、terminal episode_result、keyframes 和 package
linkage 转成 Phase 11.2/11.3 所需 evidence。

GenManip native demogen/cuRobo 路线作为备选 regeneration lane，而不是当前 11.3.b 的
首选证据来源。GenManip 可以从 native config 运行
`python demogen.py -cfg configs/tasks/ebench/mobile_manip/test_mini/apple_to_fruit_bowl.yml`
或加 `--eval` 生成 eval task seed；workflow 在 scene metric `score == 1` 时记录成功，
成功 artifacts 会写入 `saved/demonstrations/.../trajectory/` 或 `saved/tasks/.../`。但当前
没有找到可直接复用的 apple demogen/task LMDB，已有 `saved/eval_results/.../result_info.json`
只能证明历史 online eval 成功，不能作为 clean replay source。更重要的是，GenManip demogen
期望的是 native GenManip asset/config layout（`saved/assets/scene_usds`、`object_usds`、
task YAML、robot/camera/metric/object metadata），不能直接消费 Scenario Forge package/USD。
如果后续选择 demogen/cuRobo 作为 11.3.c 路线，必须先由 EOS/adapter 层提供
Scenario-Forge-to-GenManip exporter 或明确的 package-linked native config 生成记录。

如果 11.3.b 只找到“官方历史成功视频/日志”但不能证明它消费了 Scenario Forge package 或
同一 task contract，它只能作为 debugging/reference evidence，不能直接关闭 Phase 11.3。
Scenario Forge 不在本 repo 内实现 planner、oracle policy、simulator runner 或 predicate
evaluator，也不能伪造 `predicate_status=true`。

### 35.4 Post-Execution Visual Review Gate

对 episode 关键帧再做一次 clean-room visual review：

```text
initial frame:
  apple、bowl、桌面、robot/spawn 可见，材质没有明显 fallback。
final frame:
  如果 predicate_status=true，视觉上也应能看到合理的 apple-in-bowl 结果。
  如果 predicate_status=false，视觉 review 只记录可见失败形态，不推翻 predicate。
```

2026-07-04 Scenario Forge 侧已固化 11.4 的 evidence contract、JSON Schema 和 CLI
gate：

```bash
scenario-forge package phase11-post-execution-visual-review \
  --package <package-dir> \
  --visual-review <phase11-post-execution-visual-review.yaml> \
  --strict
```

该 gate 要求 `render-visual-reviewer` 的 clean-room PASS、initial/final keyframes 存在、
可见证据非空，并要求引用的 Phase 11.3 success predicate gate 已经 passed。在该 gate
contract 固化时，真实 apple-to-bowl canary 仍需 EOS 侧保留执行关键帧并完成 visual
review 后才能关闭 Phase 11.4。

2026-07-05 执行结果：Phase 11.4 已对 BPL-19R attempt_002 关闭。原先的
post-action overview frame 没有清楚显示 apple-in-bowl，因此没有被用作 PASS 证据；
review packet 改用同一 camera 的 `right_camera_first.jpg` / `right_camera_last.jpg`。
clean-room visual review evidence 记录 final frame 可见红苹果在白碗内，且没有空画面、
严重 clipping 或异常红/粉 fallback material。Scenario Forge strict gate 已通过：

```text
phase11_4_bpl19r_visual_review_frames/right_camera_first.jpg
phase11_4_bpl19r_visual_review_frames/right_camera_last.jpg
phase11_post_execution_visual_review_bpl19r_success.yaml
phase11_post_execution_visual_review_bpl19r_success_gate.yaml   status=passed
```

人工查看只能作为调试备注；实际 gate 只消费 `render-visual-reviewer` 风格的结构化
visual review evidence。

Phase 11.4 的具体无人化执行切片：

```text
11.4.a review packet assembly:
  owner: Scenario Forge evidence handoff + EOS artifact producer
  input: Phase 11.2 completed episode gate, Phase 11.3 predicate gate,
         initial/final keyframe paths, image hashes, short visual expectation。
  rule: packet 只能包含图片路径和视觉期望，不能包含实现细节、怀疑点或期望 verdict。

11.4.b clean-room visual review:
  owner: render-visual-reviewer
  input: 11.4.a review packet
  output: phase11-post-execution-visual-review/v0.1 evidence，包含
          reviewer=render-visual-reviewer、review_mode=clean_room_visual_skill、
          verdict、visible evidence、risk、retake recommendation。

11.4.c strict visual gate ingestion:
  owner: Scenario Forge
  input: 11.4.b evidence
  output: phase11_post_execution_visual_review_gate.yaml
  rule: 只有 verdict=PASS、initial/final keyframes 存在、visible evidence 非空、
        upstream Phase 11.3 predicate gate passed 时才能 passed。WARN/FAIL/missing
        review 都 blocked，并要求 retake 或上游 evidence 修复。
```

2026-07-05 soap-to-dish 11.4 retake/rerender 技术判断：

```text
root cause:
  package-linked BPL-19R 已经给出 predicate success，但当前保留的默认执行相机
  没有把 task contract 绑定的目标容器、紫色 soap、接触关系和 lifted / non-occluding
  gripper 同时拍清楚。11.4 的目标判断必须来自 package task contract、
  `scene/instances.yaml` / source_uid 和 retained scene evidence，不能靠人工把某个
  画面物体临时命名成 target；非目标容器只能作为上下文，不能作为 PASS 的唯一依据。

current EOS capability:
  retake/rerender 属于 EOS / GenManip runtime lane，不属于 Scenario Forge pure
  package layer。执行策略是给 package-linked BPL-19R rerun wrapper 增加
  `retake_camera_config`，通过结构化 YAML 生成 derived native task config，并把
  evidence camera override 写进 GenManip 允许的 `configs/tasks/...` 路径。BPL-19M/R
  live rollout 的 policy request 仍只消费 `video.overlook_camera_view`、
  `video.left_camera_view` 和 `video.right_camera_view`；优先用不进入 policy 输入的
  `top_camera` 作为 fixed world/external evidence view，避免改变 policy 行为。

current GenManip renderer boundary:
  GenManip `render.py` / `RenderWorkflow` 是 demogen trajectory renderer，依赖
  `DEMONSTRATION_DIR/<task>/trajectory/<dir>/meta_info.pkl` 和 planning data。
  它不是 BPL-19R eval episode 的离线 final-state rerenderer。当前 retained
  `meta_record.pkl` 只保留 base/gripper/joint/model_output 等轨迹信息，不包含
  object final poses，因此不能只靠 retained eval artifact 可靠重建最终物体状态。

implementation route:
  owner 是 EOS / GenManip runtime lane，不是 Scenario Forge pure package layer。
  package-linked 11.4 retake lane 必须在不改变 policy 输入的前提下，用非 policy
  evidence camera 做固定 wide 3/4 或 top-oblique 重拍。当前最稳候选是把
  `top_camera` 作为 world/external evidence camera，因为 policy 输入只用
  overlook/left/right。Scenario Forge 只保留 retake evidence 和 gate ingestion；
  不在本 repo 内引入 Isaac/GenManip SDK。

required retake evidence:
  保留 package dir、native_task_config、camera YAML path/hash、camera pose/intrinsics/
  resolution、runtime log、result_info、selected_success_attempt、video/keyframe
  paths/hash，以及 policy-input camera hashes。retake keyframes 必须再交给
  render-visual-reviewer clean-room review，并由 Scenario Forge strict 11.4 gate
  消费 PASS evidence。

non-goals:
  不在 Scenario Forge 里实现 simulator runner、planner、policy adapter、offline
  physics replay 或 ConvertAsset USD/MDL/mesh conversion；visual evidence 也不能覆盖
  11.3 predicate、11.5 policy 或 11.7 release gate。
```

2026-07-05 执行更新：

```text
soap-to-dish Phase 11.4 已通过 top-camera retake visual gate。

retained evidence:
  soap_to_dish_phase11_4_bpl19r_top_camera_retake_live_allowed_config/phase11_package_linked_bpl19r_rerun.yaml
  soap_to_dish_phase11_4_top_camera_retake_visual_review_frames/top_camera_first.jpg
  soap_to_dish_phase11_4_top_camera_retake_dense_frames/top_camera_after_t7_009.jpg
  soap_to_dish_phase11_post_execution_visual_review_top_camera_retake_pass.yaml
  soap_to_dish_phase11_post_execution_visual_review_top_camera_retake_pass_gate.yaml

result:
  selected_success_attempt=attempt_000, task_success=true, standard_model_score=1.0.
  A first clean-room review over the earlier final/late frame returned WARN because
  the gripper still occluded the contact region. A second clean-room review over the
  denser top-camera frame at about 11.0s returned PASS: the soap is visibly sitting
  on / overlapping the shallow dish and the gripper no longer makes the relationship
  unreadable. The strict Scenario Forge 11.4 gate is passed with blockers=[].

diagnostic evidence retained:
  soap_to_dish_phase11_4_bpl19r_side_camera_retake_live/
  soap_to_dish_phase11_4_bpl19r_side_camera_retake_fresh_live/
  The first side-camera attempt reused the previous GenManip run progress and ran
  native item 001, producing task_success=false; the fresh-run attempt started item
  000 but blocked at reset / online-lane readiness. Neither side-camera attempt is
  used to close 11.4. EOS wrapper tests were updated so derived retake task configs
  include the retake camera config stem, preventing later retakes from overwriting
  earlier evidence configs.
```

### 35.5 Single-Task Automated Release Candidate

苹果入碗形成第一个完整自动证据包：

```text
package + asset lock + task contract
overview render + automated visual review
EOS executed episode evidence
success predicate evaluation
post-execution visual review
license/release policy gate
known blockers
```

结论只能是：

```text
release_candidate_status: passed | blocked
```

如果资产仍是 `research-use`，则 release gate 自动给 `blocked`，即使 package、render、
episode 和 predicate 都通过。

这是用户真正关心的“给 EBench 的一个有 USD 的完整任务包”的第一个闭环版本：它包含真实
USD 资产 package、EOS 执行证据、predicate 证据、前后视觉 review 和 release policy 结论。
如果 license 仍 blocked，它仍是 internal RC，不是可公开发布 dataset。

2026-07-04 Scenario Forge 侧已固化 11.5 的 release policy contract、JSON Schema
和 CLI gate：

```bash
scenario-forge package phase11-single-task-rc \
  --package <package-dir> \
  --release-policy <phase11-release-policy.yaml> \
  --strict
```

该 gate 聚合 11.0-11.4 的 passed gate、package/asset lock/task contract 和
`phase11-release-policy/v0.1`。如果资产仍为 `research-use` 或缺少 redistribution
approval，结果必须是 `blocked`，不能发布为 public dataset 或 official score release。

2026-07-05 执行结果：apple-to-bowl 已形成第一个 single-task internal RC evidence
bundle。11.0 overview visual review、11.1 EOS task execution、11.2 BPL-19R executed
episode、11.3 success predicate 和 11.4 post-execution visual review 均有结构化 evidence；
11.5 聚合 gate 因 release policy 被自动阻塞：

```text
phase11_release_policy_bpl19r_internal_rc_blocked.yaml
phase11_single_task_rc_bpl19r_internal_policy_blocked_gate.yaml  status=blocked
blockers:
  - release policy status must be pass; got blocked
  - release policy redistribution_approval must be true
  - ebench_assets_research_use_only
  - redistribution_approval_missing
```

产品口径：这已经是“给 EBench 的一个有 USD 的完整任务包”的 internal RC 闭环；
它不是 public dataset release，也不是 official score/leaderboard release。

### 35.6 Small Multi-Task Canary

扩到 3-5 个 EBench 任务，验证自动门禁不是只适配 apple-to-bowl。

要求：

```text
1. 每个任务都有真实资产 package。
2. 每个任务都有 task contract。
3. 每个任务都有 overview render + automated visual review。
4. 至少一个 EOS execution lane 能启动 episode。
5. 每个任务都有 predicate evaluation evidence 或 blocker。
```

2026-07-04 Scenario Forge 侧已固化 11.6 的 suite-level evidence contract、JSON
Schema 和 CLI gate：

```bash
scenario-forge suite phase11-small-canary \
  --suite <suite-dir> \
  --canary-evidence <phase11-small-multi-task-canary.yaml> \
  --strict
```

该 gate 要求 3-5 个任务、每个任务引用 single-task RC gate、记录真实资产 package /
task contract / overview visual review / execution lane / predicate evidence 或结构化 blocker，
并要求至少一个任务的 execution lane 已 started 或 completed。真实 small multi-task canary
仍需 EOS 针对 3-5 个 Scenario Forge-generated EBench tasks 产出证据后才能关闭 Phase 11.6。

2026-07-05 执行结果：已跑一个 underfilled canary 来固化阻塞口径。当前只有
apple-to-bowl 一个真实 EBench task，所以 gate 正确 blocked：

```text
phase11_small_multi_task_canary_underfilled_blocked.yaml
phase11_small_multi_task_canary_underfilled_blocked_gate.yaml    status=blocked
blockers:
  - small multi-task canary package_count must be between 3 and 5; got 1
  - only_one_real_ebench_task_available; need 3-5 tasks for Phase 11.6
```

2026-07-05 second-task update：新增 `ebench_soap_to_dish_canary` 作为第二个真实
EBench USD-bearing task package。它覆盖 EBench 中常见的“manipulated object +
environment fixture target”形态：soap 是单独 materialized official asset，soap dish 是
scene USD 内的 fixture `/root/obj__01` / source uid `_01`，不会伪造一个 target asset。
已通过 package check、asset lock check 和 USD Stage.Open：

```text
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/soap_to_dish_package_generation_evidence.yaml
soap_to_dish_package_manifest.yaml
soap_to_dish_main.usda
soap_to_dish_asset_lock.yaml
soap_to_dish_task_contract.yaml
soap_to_dish_ebench_package.yaml
```

新的 2-task underfilled 11.6 gate 已保留：

```text
phase11_small_multi_task_canary_two_task_underfilled_blocked.yaml
phase11_small_multi_task_canary_two_task_underfilled_blocked_gate.yaml   status=blocked
blockers:
  - small multi-task canary package_count must be between 3 and 5; got 2
  - soap_to_dish_overview_visual_review_not_run
  - soap_to_dish_eos_execution_not_run
  - soap_to_dish_success_predicate_not_evaluated
  - soap_to_dish_single_task_rc_not_run
```

2026-07-05 third-task update：新增 `ebench_remote_to_holder_canary` 作为第三个
真实 EBench USD-bearing task package。它同样覆盖 “manipulated object +
environment fixture target” 形态：remote control 是单独 materialized official
asset，remote holder 是 scene USD 内的 fixture `/root/obj__00` / source uid `_00`，
不会伪造一个 target asset。已通过 package check、asset lock check 和 USD Stage.Open：

```text
docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/remote_to_holder_package_generation_evidence.yaml
remote_to_holder_package_manifest.yaml
remote_to_holder_main.usda
remote_to_holder_asset_lock.yaml
remote_to_holder_task_contract.yaml
remote_to_holder_ebench_package.yaml
```

新的 3-task 11.6 gate 已保留：

```text
phase11_small_multi_task_canary_three_task_downstream_blocked.yaml
phase11_small_multi_task_canary_three_task_downstream_blocked_gate.yaml   status=blocked
package_count=3
blockers:
  - soap_to_dish_overview_visual_review_not_run
  - soap_to_dish_eos_execution_not_run
  - soap_to_dish_success_predicate_not_evaluated
  - soap_to_dish_single_task_rc_not_run
  - remote_to_holder_overview_visual_review_not_run
  - remote_to_holder_eos_execution_not_run
  - remote_to_holder_success_predicate_not_evaluated
  - remote_to_holder_single_task_rc_not_run
```

因此 Phase 11.6 的“任务数量不足” blocker 已解除。下一步不是进入 Phase 12，
而是让 soap-to-dish 和 remote-to-holder 分别走 11.0-11.5 的自动
visual/EOS/predicate/RC evidence chain。只有两个新增任务都补齐自动门禁后，
11.6 才可能从 blocked 变成 passed。

2026-07-05 Phase 11.0 scale-out update：soap-to-dish 和 remote-to-holder 已经
各自产出 engine-native tabletop overview render，并交给 clean-room
`render-visual-reviewer`。两个 11.0 gate 都是 failed，而不是 not_run：

```text
soap_to_dish_tabletop_overview.png
soap_to_dish_tabletop_overview_render_metadata.json
soap_to_dish_tabletop_overview_runtime.log
soap_to_dish_tabletop_overview_visual_review.yaml
soap_to_dish_phase11_visual_review_gate_failed.yaml   status=failed
blockers:
  - visual review verdict must be PASS; got FAIL
  - visual review render metadata material_runtime_preflight.status must be pass; got failed
  - visual review render runtime log contains blocking material signal: rtx.mdltranslator
  - visual review render runtime log contains blocking material signal: wasn't resolved properly

remote_to_holder_tabletop_overview.png
remote_to_holder_tabletop_overview_render_metadata.json
remote_to_holder_tabletop_overview_runtime.log
remote_to_holder_tabletop_overview_visual_review.yaml
remote_to_holder_phase11_visual_review_gate_failed.yaml   status=failed
blockers:
  - visual review verdict must be PASS; got FAIL
  - visual review render runtime log contains blocking material signal: References an asset that can not be found
```

产品口径：这是正向推进，不是失败倒退。之前的 blocker 是“还没跑视觉验收”；
现在已经知道真实 blocker：两个任务的 overview 相机都要重拍，soap-to-dish 还暴露
official task3 scene 的缺失 texture / MDL translator 问题，remote-to-holder 暴露
remote asset 的外部 texture reference 没被 package materialize 的闭包问题。Scenario Forge
已把 11.0 gate 加严：visual PASS 不再足够，render metadata 和 runtime log 中的材质/贴图
闭包 blocker 也会让 gate failed。

2026-07-05 material-closure triage update：

```text
remote-to-holder:
  root cause: Scenario Forge 的 official asset intake 只复制了
        remote_control/ready/remote0 bundle，没有把 USD dependency 指向的
        sibling sidecar texture bundle 一起 materialize。缺失贴图实际存在于
        official asset root 下的 remote_control/63f5007c-.../SubUSDs/textures/。
  owner: Scenario Forge adapter layer.
  fix direction: 在 adapters/ebench/official_asset_intake.py 中用 USD dependency
        analysis 发现 source_usd.parent 外、但仍在同一 collection root 内的
        sibling sidecar roots，并按 collection-relative layout 复制进
        assets/official_ebench_remote_control/。
  local verification: regenerated package now records canonical USD as
        assets/official_ebench_remote_control/ready/remote0/remote0.usd, and
        the fixed IsaacSim41 render metadata reports
        material_runtime_preflight.status=pass with no missing texture blocker.
  retained gate status: fixed render, WARN visual review, and strict 11.0 gate
        are now retained. The 11.6/11.7 suite gates no longer list the old
        remote missing-texture blocker. The remaining remote 11.0 blocker is
        camera/framing/object identifiability: the independent review returned
        WARN because the remote is too small and the holder is weakly identified.

soap-to-dish:
  root cause: the retained official task3 scene USD/MDL references texture files
        that were not found in the current official EBench asset mount. This is
        not a Scenario Forge package-layout bug.
  owner: upstream asset/ConvertAsset lane, or a replacement official source.
  fix direction: do not synthesize textures or copy ConvertAsset conversion
        logic into Scenario Forge. Prepare a ConvertAsset handoff with failing
        package, dependency closure report, runtime log, render image, source
        provenance, and hashes; alternatively switch to an official repaired
        scene source and regenerate the package/lock/evidence.
  historical planning status: soap 11.0 was blocked by both camera/framing and
        upstream scene material closure before the no-MDL relink repair.
  2026-07-05 evidence update: Scenario Forge added a static MDL
        `texture_2d(...)` closure audit and retained
        `soap_to_dish_phase11_material_closure_handoff.yaml`. The audit fails
        both the package copy and official task3 source because
        `MI_655dcc9a9237ad0001ba8197.mdl` references
        `c00e97e58585d8ddb0f8b16a724d05a13eae31.jpg`, and
        `MI_655dcc9ad6b50e000157727c.mdl` references
        `bf77ddc86c270d02747e7d0517103514ab51d0f.jpg` and
        `c9c274d4ea1de7d059cec0a795b3b27e3941935.jpg`; none exists in the
        checked official/local roots. This confirmed that the original official
        scene needed an upstream repaired source or ConvertAsset-owned
        material-normalized artifact before Scenario Forge could rerender/review
        soap-to-dish. This blocker was later closed for the internal visual
        canary by the ConvertAsset no-MDL relink artifact and retained
        `soap_to_dish_phase11_visual_review_gate_nomdl_relink_cam4_pass.yaml`.

both tasks:
  the next overview camera retake must use task-specific visual expectations:
        soap + soap dish + bathtub/work surface + robot/spawn for soap-to-dish,
        remote + remote holder + coffee table/work surface + robot/spawn for
        remote-to-holder. The EOS render metadata must not keep apple/bowl
        target anchors for these scale-out tasks.
```

最新 3-task 11.6 gate 已更新为 visual-failed downstream blocked：

```text
phase11_small_multi_task_canary_three_task_visual_failed_downstream_blocked.yaml
phase11_small_multi_task_canary_three_task_visual_failed_downstream_blocked_gate.yaml   status=blocked
package_count=3
blockers:
  - soap_to_dish_phase11_0_visual_review_failed
  - soap_to_dish_overview_camera_retake_required
  - soap_to_dish_material_runtime_preflight_failed_missing_scene_textures
  - remote_to_holder_phase11_0_visual_review_failed
  - remote_to_holder_overview_camera_retake_required
  - soap_to_dish_eos_execution_not_run / remote_to_holder_eos_execution_not_run
  - soap_to_dish_success_predicate_not_evaluated / remote_to_holder_success_predicate_not_evaluated
  - soap_to_dish_single_task_rc_not_run / remote_to_holder_single_task_rc_not_run
```

2026-07-05 remote material-closure promotion result:

```text
remote_to_holder_tabletop_overview_material_fixed.png
remote_to_holder_tabletop_overview_material_fixed_render_metadata.json
remote_to_holder_tabletop_overview_material_fixed_runtime.log
remote_to_holder_tabletop_overview_material_fixed_visual_review.yaml
remote_to_holder_phase11_visual_review_gate_material_fixed_warn.yaml   status=failed
blockers:
  - visual review verdict must be PASS; got WARN

phase11_small_multi_task_canary_three_task_visual_failed_downstream_blocked_gate.yaml   status=blocked
remote row:
  material_runtime_closure: passed
  overview_visual_review_gate: remote_to_holder_phase11_visual_review_gate_material_fixed_warn.yaml
  blockers:
    - remote_to_holder_phase11_0_visual_review_failed
    - remote_to_holder_overview_camera_retake_required
    - remote_to_holder_eos_execution_not_run
    - remote_to_holder_success_predicate_not_evaluated
    - remote_to_holder_single_task_rc_not_run

phase11_automated_release_three_task_visual_failed_policy_blocked_gate.yaml   status=blocked
known_blocker_count: 13
```

结论：remote-to-holder 的材料闭包问题已经从 release blocker 中移除；它还没有通过
Phase 11.0，因为 clean-room reviewer 只给 WARN。下一步是按 reviewer 建议重拍更近、
更低的 overview camera，让 remote 和 holder 在画面中更大、更明确。soap-to-dish 的
official task3 scene 缺贴图后来通过 ConvertAsset no-MDL relink 路线关闭了 11.0
visual/material blocker；soap 随后也关闭了 11.1 EOS task execution integration，
当前 blocker 已转移到 11.2-11.5 downstream evidence。

### 35.7 Automated Release Gate

最终 release gate 完全自动判断：

```text
package_check: pass
asset_lock_check: pass
adapter_contract: pass
visual_review: pass
episode_execution: pass | blocked
predicate_evaluation: pass | failed | blocked
license_policy: pass | blocked
known_blockers: []
release_status: passed | blocked
```

只有全部 release-critical gate 通过，才能声明 release candidate passed。任何 gate blocked
都必须保留机器可读 blocker，不能由人工口头放行。

2026-07-04 Scenario Forge 侧已固化 11.7 的 suite-level automated release evidence
contract、JSON Schema 和 CLI gate：

```bash
scenario-forge suite phase11-release \
  --suite <suite-dir> \
  --release-evidence <phase11-automated-release-evidence.yaml> \
  --strict
```

该 gate 要求 Phase 11.6 small canary passed，package check、asset lock、adapter
contract、visual review、episode execution、predicate evaluation、license policy 全部为
`pass`，且 `known_blockers=[]`。这只是 release-candidate 自动门禁；public dataset
publication、official score release 和 leaderboard comparability 仍需要外部 approval /
policy evidence。

2026-07-05 执行结果：Phase 11.7 gate 已以机器可读方式 blocked。原因不是人工未确认，
而是 11.6 任务数量不足和 license policy 未过：

```text
phase11_automated_release_underfilled_policy_blocked_evidence.yaml
phase11_automated_release_underfilled_policy_blocked_gate.yaml   status=blocked
blockers:
  - small multi-task canary gate status must be passed; got blocked
  - release-critical gate license_policy must be pass; got blocked
  - known_blockers must be empty; got 3
  - phase11_6_requires_3_to_5_real_ebench_tasks; current structured canary has 1
  - ebench_assets_research_use_only
  - redistribution_approval_missing
```

2026-07-05 second-task update：11.7 已用新的 2-task 11.6 gate 重新聚合，仍然
blocked，但 blocker 更具体：

```text
phase11_automated_release_two_task_underfilled_policy_blocked_evidence.yaml
phase11_automated_release_two_task_underfilled_policy_blocked_gate.yaml   status=blocked
blockers:
  - small multi-task canary gate status must be passed; got blocked
  - release-critical gate visual_review must be pass; got blocked
  - release-critical gate episode_execution must be pass; got blocked
  - release-critical gate predicate_evaluation must be pass; got blocked
  - release-critical gate license_policy must be pass; got blocked
  - phase11_6_requires_3_to_5_real_ebench_tasks; current generated task packages are apple-to-bowl and soap-to-dish
  - soap_to_dish_overview_visual_review_not_run
  - soap_to_dish_eos_execution_not_run
  - soap_to_dish_success_predicate_not_evaluated
  - soap_to_dish_single_task_rc_not_run
  - ebench_assets_research_use_only
  - redistribution_approval_missing
```

2026-07-05 third-task update：11.7 已用新的 3-task 11.6 gate 重新聚合。该版本不再因为
package_count 不足阻塞，但仍然 blocked：

```text
phase11_automated_release_three_task_downstream_policy_blocked_evidence.yaml
phase11_automated_release_three_task_downstream_policy_blocked_gate.yaml   status=blocked
blockers:
  - small multi-task canary gate status must be passed; got blocked
  - release-critical gate visual_review must be pass; got blocked
  - release-critical gate episode_execution must be pass; got blocked
  - release-critical gate predicate_evaluation must be pass; got blocked
  - release-critical gate license_policy must be pass; got blocked
  - soap_to_dish_overview_visual_review_not_run
  - soap_to_dish_eos_execution_not_run
  - soap_to_dish_success_predicate_not_evaluated
  - soap_to_dish_single_task_rc_not_run
  - remote_to_holder_overview_visual_review_not_run
  - remote_to_holder_eos_execution_not_run
  - remote_to_holder_success_predicate_not_evaluated
  - remote_to_holder_single_task_rc_not_run
  - ebench_assets_research_use_only
  - redistribution_approval_missing
```

2026-07-05 Phase 11.0 scale-out update：11.7 已再次用 visual-failed 版本的 11.6
gate 聚合。当前 blocker 更具体：

```text
phase11_automated_release_three_task_visual_failed_policy_blocked_evidence.yaml
phase11_automated_release_three_task_visual_failed_policy_blocked_gate.yaml   status=blocked
blockers:
  - small multi-task canary gate status must be passed; got blocked
  - release-critical gate visual_review must be pass; got blocked
  - release-critical gate episode_execution must be pass; got blocked
  - release-critical gate predicate_evaluation must be pass; got blocked
  - release-critical gate license_policy must be pass; got blocked
  - soap_to_dish_phase11_0_visual_review_failed
  - soap_to_dish_overview_camera_retake_required
  - soap_to_dish_material_runtime_preflight_failed_missing_scene_textures
  - remote_to_holder_phase11_0_visual_review_failed
  - remote_to_holder_overview_camera_retake_required
  - remote_to_holder_eos_execution_not_run
  - remote_to_holder_success_predicate_not_evaluated
  - remote_to_holder_single_task_rc_not_run
  - ebench_assets_research_use_only
  - redistribution_approval_missing
```

2026-07-05 remote material-fixed release-gate update：同一 11.7 gate 已重跑。
`known_blockers must be empty` 的计数从 14 降到 13；remote 的
`material_runtime_log_missing_remote_texture` 已移除。11.7 仍然 blocked，因为 11.6
未通过、soap 仍有 visual/material blocker、remote 仍有 WARN/camera-retake blocker，
两个新增任务的 EOS/predicate/RC 证据未跑，且 license policy 仍 blocked。

2026-07-05 remote retake planning update：remote-to-holder 已经完成一次 task-specific
camera retake trial。该 trial 证明 remote 的材质闭包已通过：IsaacSim41 render
material preflight 为 pass，runtime log 不再出现 missing remote texture blocker。
但是 clean-room visual review 仍为 WARN，原因是 remote 在画面中偏小、姿态更像竖立或
edge-on，holder 偏暗，桌面略有裁切。这个结果说明下一步不能盲目继续调相机；必须先把
remote 的 official task pose、Scenario Forge source manifest pose、生成后的
scene/instances pose 和 render camera metadata 对齐检查。若 Scenario Forge manifest
或 generator 让 remote 偏离 official pose，应先修 pose 并重新生成 package；若 official
pose 本身导致画面不可识别，则记录为 task-specific pose/camera/framing blocker，再由
EOS renderer 选择更合适的 overview camera。无论哪条路径，人工看图都只能生成 retake
request，不能把 WARN 改成 PASS。

2026-07-05 remote contact/camera closure update：上述 WARN 已被新的 root-cause
gate 和 contact-fixed render supersede。根因不是材质，也不只是相机；Scenario Forge
示例 manifest 的 remote orientation 已改为 GenManip wxyz 约定，但 z center 仍是
`0.11`，导致 corrected-pose remote 的 world bbox bottom 约为 `0.096045`，
比 task5 table top `0.000162` 高约 9.6 cm。已用 TDD 固化并修正为
`xyz=[-0.25, -0.4, 0.0142]`，重新生成 package 后 remote bottom 到 table top
约 `0.000083` m。随后用更低、更近的 task-specific overview camera 重渲染，并由
clean-room `render-visual-reviewer` 给出 PASS：

```text
remote_to_holder_pose_camera_root_cause.yaml
remote_to_holder_tabletop_overview_contactfixed_cam3.png
remote_to_holder_tabletop_overview_contactfixed_cam3_render_metadata.json
remote_to_holder_tabletop_overview_contactfixed_cam3_runtime.log
remote_to_holder_tabletop_overview_contactfixed_cam3_visual_review.yaml   verdict=PASS
remote_to_holder_phase11_visual_review_gate_contactfixed_cam3_pass.yaml   status=passed

phase11_small_multi_task_canary_three_task_remote_visual_pass_downstream_blocked_gate.yaml   status=blocked
remote row:
  overview_visual_review: passed
  material_runtime_closure: passed
  blockers:
    - remote_to_holder_eos_execution_not_run
    - remote_to_holder_success_predicate_not_evaluated
    - remote_to_holder_single_task_rc_not_run

phase11_automated_release_three_task_remote_visual_pass_policy_blocked_gate.yaml   status=blocked
known_blocker_count: 11
```

结论：remote-to-holder 的 Phase 11.0 visual/material/pose-contact gate 已关闭。
它还不是 single-task RC，因为 11.2 completed episode、11.3 predicate、11.4
post-execution visual review 和 11.5 RC aggregation 尚未对该任务运行。
small-canary/release blocker 现在只保留 remote downstream gaps；不再保留
remote visual failed 或 camera-retake blocker。

2026-07-05 remote Phase 11.1 config update：EOS 的 Scenario Forge package
task-execution lane 已消费 contact-fixed remote package 并生成 runtime config evidence：

```text
remote_to_holder_phase11_eos_task_execution_config_blocked_evidence.yaml
remote_to_holder_phase11_task_execution_config_trace.json
remote_to_holder_phase11_task_execution_config_runtime.log
remote_to_holder_phase11_task_execution_gate_config_blocked.yaml   status=failed

phase11_small_multi_task_canary_three_task_remote_config_blocked_downstream_blocked_gate.yaml   status=blocked
remote row:
  overview_visual_review: passed
  execution_lane_status: blocked
  blockers:
    - remote_to_holder_phase11_1_execution_config_blocked_episode_start_not_run
    - remote_to_holder_success_predicate_not_evaluated
    - remote_to_holder_single_task_rc_not_run

phase11_automated_release_three_task_remote_config_blocked_policy_blocked_gate.yaml   status=blocked
known_blocker_count: 11
```

该历史结果把 remote blocker 从 “Phase 11.1 not run” 收窄为 “contract/config 已消费，
但真实 simulator episode start 和 initial keyframe 未跑”。它已经被后续 live-start、
completed-episode、zero-policy predicate-failed evidence，以及后续 package-linked
BPL-19R predicate-passed evidence supersede；当前 remote blocker 不再是 config
generation、episode start 或 Phase 11.3 predicate，而是 Phase 11.4 post-execution
visual review、Phase 11.5 RC aggregation 和 suite re-aggregation。Scenario Forge
仍只消费 evidence，不在本 repo 内实现 runner。

2026-07-05 remote Phase 11.1 runtime-preflight update：在真正重跑 remote-to-holder
11.1 前，EOS 必须先保留 GenManip/IsaacSim41 runtime preflight evidence。一次
remote live probe 已经证明 `start_new_job` 可以消费 native remote task config，但如果
EvalServer 没带 EOS 所需的 cuRobo/CUDA overlays，Isaac worker 会在 reset 前因
`ModuleNotFoundError: No module named 'curobo'` 死亡，后续 `/reset_result` 只会表现为
HTTP 500/无 pending reset result。这不是 Scenario Forge package、相机、材质或布局
blocker；下一次 11.1 需要先记录 simulator env、cuRobo import、CUDA/torch lib overlay、
server launch command/run id 和 log path。preflight 失败时，remote 11.1 应 blocked 为
`eos_runtime_environment_preflight_failed`，不能误归因到 package 生成。

2026-07-05 remote Phase 11.1 live-start update：EOS 随后用带 cuRobo/CUDA overlays
的 GenManip/IsaacSim41 EvalServer 重跑 `mobile_manip/remote_to_holder`，保留了 runtime
preflight、trace、runtime log 和 initial overlook keyframe，并通过 Scenario Forge strict
gate：

```text
remote_to_holder_phase11_runtime_preflight_envfix.yaml
remote_to_holder_phase11_eos_task_execution_live_evidence.yaml
remote_to_holder_phase11_task_execution_live_trace.json
remote_to_holder_phase11_task_execution_live_runtime.log
remote_to_holder_phase11_task_execution_initial_overlook.png
remote_to_holder_phase11_task_execution_gate_live.yaml   status=passed
```

这关闭 remote-to-holder Phase 11.1。它只证明 EOS 能消费 package/task config 并启动
真实 episode，完成 reset、一次 zero-policy step、cleanup close 和 initial keyframe
retention；仍不证明任务成功、模型能力、completed episode、predicate、release policy 或
leaderboard 可比性。

2026-07-05 remote Phase 11.2 / 11.3 update：remote-to-holder 随后在同一个
GenManip/IsaacSim41 run 中跑到 terminal episode，保留 completed trace、runtime log、
initial/final overlook keyframes 和 terminal episode_result，并通过 Scenario Forge
Phase 11.2 strict gate：

```text
remote_to_holder_phase11_executed_episode_completed_evidence.yaml
remote_to_holder_phase11_executed_episode_completed_trace.json
remote_to_holder_phase11_executed_episode_result_info.json
remote_to_holder_phase11_executed_episode_completed_runtime.log
remote_to_holder_phase11_executed_episode_initial_overlook.png
remote_to_holder_phase11_executed_episode_final_overlook.png
remote_to_holder_phase11_executed_episode_gate_completed.yaml   status=passed
```

Phase 11.2 关闭只证明“完整 episode 证据已保留”。该 terminal result 是
`score=0.0`、`sr=0.0`，因此随后的 Phase 11.3 simulator-state predicate gate
正确失败：

```text
remote_to_holder_phase11_success_predicate_failed_evidence.yaml
remote_to_holder_phase11_success_predicate_gate_failed.yaml   status=failed
blockers:
  - predicate_status must be true; got False
  - episode_result_sr_zero
```

这把当时的 remote-to-holder blocker 从“没有跑完整 episode”推进成更真实的
`remote_to_holder_success_predicate_failed_zero_policy`。该失败仍保留为历史 debugging
evidence：它证明 zero-policy 不能关闭 11.3，也证明人工看图不能把失败 predicate 改成
成功。它已经被下面的 package-linked BPL-19R live success evidence supersede；当前
remote-to-holder 不再卡在 11.3，而是进入 11.4 post-execution visual review。

2026-07-05 remote Phase 11.3.b/11.3.c source-selection update：Scenario Forge 已保留
`remote_to_holder_phase11_successful_rollout_source_selection.yaml`。调查没有找到任何
remote-to-holder 的历史 `task_success=true`、`sr=1` 或 `score=1.0` retained artifact；
TaskBook/GenManip 中找到的 remote terminal results 都是 0 分或失败。可复用的是 EOS
BPL-19R package-linked wrapper/bridge 模式。EOS 侧已经把 package-linked BPL-19R
mapping 扩到：

```text
mobile_manip/remote_to_holder ->
/cpfs/shared/simulation/zhuzihou/dev/GenManip/configs/tasks/ebench/mobile_manip/test_mini/remote_to_holder.yml
```

然后用同一 pi0.5/BPL-19R multi-attempt lane 跑 package-linked remote rerun。只有出现
terminal `task_success=true` / `sr=1` 后，才能通过已有 Phase 11 bridge 生成新的 11.2
executed-episode evidence 和 11.3 predicate evidence。Scenario Forge 不在本 repo 中实现
policy runner 或模型 adapter。

已保留的 dry-run plan：

```text
remote_to_holder_phase11_3c_bpl19r_package_linked_plan/phase11_package_linked_bpl19r_rerun.yaml
rerun_status=planned
package_id=ebench_remote_to_holder_canary
task_id=mobile_manip/remote_to_holder
native_task_config_exists=true
blockers:
  - live_bpl19r_rerun_not_executed
```

该 dry-run plan 随后被 live package-linked BPL-19R rerun supersede，不再是当前 blocker。

2026-07-05 remote Phase 11.3.c/11.3.d live success update：EOS 使用同一
package-linked BPL-19R wrapper 对 `ebench_remote_to_holder_canary` 运行 live rerun，
attempt_000 即完成并记录 `task_success=true`、`standard_model_score=1.0`。Scenario Forge
已保留并通过 Phase 11.2 / 11.3 strict gates：

```text
remote_to_holder_phase11_3c_bpl19r_package_linked_live/phase11_package_linked_bpl19r_rerun.yaml
  rerun_status=executed
  selected_success_attempt=attempt_000
  blockers=[]

remote_to_holder_phase11_executed_episode_bpl19r_success_gate.yaml   status=passed
remote_to_holder_phase11_success_predicate_bpl19r_success_gate.yaml  status=passed
```

因此 remote-to-holder 的当前 Phase 11 状态是：11.0 overview visual passed、11.1 live
episode start passed、11.2 completed episode passed、11.3 simulator-state predicate
passed。随后 remote-to-holder 已进入并关闭 11.4 / 11.5：

```text
remote_to_holder_phase11_4_bpl19r_visual_review_frames/left_camera_first.jpg
remote_to_holder_phase11_4_bpl19r_visual_review_frames/left_camera_last.jpg
remote_to_holder_phase11_post_execution_visual_review_bpl19r_success.yaml
remote_to_holder_phase11_post_execution_visual_review_bpl19r_success_gate.yaml   status=passed

remote_to_holder_phase11_single_task_rc_bpl19r_internal_policy_blocked_gate.yaml status=blocked
blockers:
  - release policy status must be pass; got blocked
  - release policy redistribution_approval must be true
  - ebench_assets_research_use_only
  - redistribution_approval_missing
```

11.4 的 PASS 来自 left-camera initial/final frame 的 clean-room visual evidence：
initial frame 显示 remote 在桌面上且 holder 可见，final frame 显示 remote 位于黑色
holder/tray 内。11.5 聚合时 11.0-11.4 技术 gate 全部 passed；blocked 只来自
release policy。不能再使用人工截图确认作为 gate input。

### 35.8 进入 Phase 12 前的 Phase 11.x 工程切片

下面这些步骤仍然属于 Phase 11，不应提前算作 Phase 12。Phase 12 是 registry /
multi-simulator / ecosystem 扩展；EOS task execution integration 仍是 Phase 11 的核心
blocker。

```text
11.1.a EOS package discovery:
  owner: EOS
  goal: 读取 Scenario Forge manifest、asset lock、EBench package descriptor、
        task_entrypoint.yaml 和 task/task_contract.yaml。
  evidence: phase11-eos-task-execution/v0.1 中 contract_consumed=true。
  current status: closed for apple-to-bowl canary on 2026-07-04.

11.1.b EOS execution config generation:
  owner: EOS
  goal: 把 task contract 映射成 EOS runtime execution config。
  evidence: execution_config_status=generated，并记录 config artifact 或 trace URI。
  current status: closed for apple-to-bowl canary on 2026-07-04.

11.1.c episode start and initial keyframe:
  owner: EOS / Isaac Sim runtime
  goal: reset/step/close lifecycle 至少跑通一次 started episode，保留 runtime log、
        trace URI 和 initial keyframe。
  evidence: phase11_task_execution_gate.yaml passed。
  current status: closed for apple-to-bowl canary on 2026-07-04 by
        phase11_task_execution_gate_live.yaml, status=passed, blockers=[].

11.1.c.0 EOS runtime environment preflight:
  owner: EOS / GenManip runtime
  goal: 在启动 EvalServer 和执行 reset 前，证明当前 simulator environment 能加载
        GenManip 所需 runtime：EOS IsaacSim41 conda env、cuRobo Python module、
        CUDA/torch shared libraries、EULA flags、PYTHONPATH/LD_LIBRARY_PATH overlays。
  evidence: runtime_preflight.status=passed, selected python/env root,
        selected CUROBO_SRC/CUDA lib paths, import-check output, server launch
        command/run id, and log path. If this fails, Phase 11.1 remains blocked
        before package execution and the blocker is EOS runtime environment,
        not Scenario Forge package content.
  current status: implicitly satisfied for apple-to-bowl by the live Phase 11.1
        evidence. Closed for remote-to-holder by
        remote_to_holder_phase11_runtime_preflight_envfix.yaml; the earlier
        missing-`curobo` run remains historical EOS runtime evidence, not an
        active package blocker.

11.1.c.1 EOS runtime connection hardening:
  owner: EOS
  goal: 启动或连接 GenManip/IsaacSim41 EvalServer，提交 apple-to-bowl job，并让
        smoke path 能等待真实 cold-start reset_result，而不是因为固定短超时过早 skipped。
  evidence: EOS runtime trace records server URL, job/run id, reset polling,
        timeout configuration, and whether reset reached passed/failed/blocked.
  current status: closed for apple-to-bowl canary; reset_result_timeout_s=240.0
        is retained in live trace evidence.

11.1.c.2 initial keyframe export:
  owner: EOS
  goal: 从 simulator observation、server recorder artifact 或 trace 中导出真实
        initial keyframe PNG，并把文件路径写入 phase11-eos-task-execution/v0.1。
  evidence: keyframes.initial points to an existing PNG retained with the
        package evidence, and Scenario Forge strict gate verifies the file exists.
  current status: closed for apple-to-bowl canary with
        phase11_task_execution_initial_overlook.png.

11.1.c.3 strict Phase 11.1 rerun:
  owner: Scenario Forge
  goal: 只消费 EOS 产出的 evidence，重新运行
        scenario-forge package phase11-task-execution --strict。
  evidence: phase11_task_execution_gate.yaml passed, or failed/blocked with
        machine-readable blockers. No manual override is allowed.
  current status: closed for apple-to-bowl canary with
        phase11_task_execution_gate_live.yaml passed.

11.2.a completed episode artifact:
  owner: EOS
  goal: 保留 completed episode 的 final state、final keyframe、trace 和 runtime log。
  evidence: phase11_executed_episode_gate.yaml passed。
  current status: closed for apple-to-bowl canary on 2026-07-04 by
        phase11_executed_episode_gate_completed.yaml, status=passed,
        blockers=[].

11.2.a.1 EOS full-horizon / chunked episode execution:
  owner: EOS
  goal: 在 GenManip/IsaacSim41 EvalServer 中提交 apple-to-bowl job 后，用
        full-horizon 或 `step_chunk` 执行到 terminal episode，而不是只跑 one-step
        smoke。当前 40-step run 仍无 episode_result，不能关闭 11.2。
  evidence: EOS trace records run_id, task config, max native steps, chunk size
        or policy-call budget, terminal episode_result, and recorder artifact
        directory. If terminal result is not reached, emit a blocked evidence
        with blocker such as terminal_episode_result_missing.
  current status: closed with run_id
        scenario_forge_phase11_apple_to_bowl_chunk_20260704T154825Z,
        max_policy_calls=1000, step_chunk_size=1000, executed_steps=1000.

11.2.a.2 executed episode evidence builder:
  owner: EOS
  goal: 从 terminal trace、runtime log、initial/final keyframes 和 final simulator
        state 投影出 `phase11-executed-episode-evidence/v0.1`。
  evidence: episode_status=completed, runtime_owner=embodied-eval-os,
        trace_uri exists, runtime_log exists, keyframes.initial/final exist,
        final_state is non-empty, blockers=[].
  current status: closed by phase11_executed_episode_completed_evidence.yaml.

11.2.a.3 strict Scenario Forge gate ingestion:
  owner: Scenario Forge
  goal: 只消费 11.2.a.2 evidence，运行
        `scenario-forge package phase11-executed-episode --strict`。
  evidence: phase11_executed_episode_gate.yaml passed, or blocked/failed with
        machine-readable blockers. No manual override is allowed.
  current status: closed by phase11_executed_episode_gate_completed.yaml.

11.3.a predicate adapter evidence:
  owner: EOS / EBench adapter
  goal: 基于 simulator state 计算 apple_in_bowl / object_in_container，而不是靠截图判断。
  evidence: phase11_success_predicate_gate.yaml passed。
  current status: evaluated and failed for the retained zero-policy completed
        episode. Retained evidence:
        phase11_success_predicate_failed_evidence.yaml and
        phase11_success_predicate_gate_failed.yaml. Blockers:
        predicate_status must be true; got False; episode_result_sr_zero.

11.3.b successful rollout source selection:
  owner: EOS / EBench adapter
  goal: 调查并选择能产生 apple-to-bowl 成功 episode 的真实 policy/oracle/official
        rollout 来源。优先 GenManip demonstration_configs / cuRobo / generalized
        oracle rule lane；其次官方 successful rollout rerun。选择结果必须说明是否
        package-linked，不能用人工看图或历史截图替代。
  evidence: source selection note, task config, policy/oracle identity, runtime
        environment, run id, package linkage, and known blockers.
  current status: first rerun candidate selected. Use EOS BPL-19R.R2
        same-checkpoint online lane as the first 11.3.c source because it has
        retained historical apple-to-bowl successes for attempts 005, 006, 007,
        and 009. Use attempt 007 as the best debugging reference because it
        succeeded in 13 cycles. Historical success remains reference-only until
        EOS reruns it through a Scenario Forge package-linked execution wrapper.
        GenManip demogen/cuRobo is retained as a backup regeneration lane, but
        not as the selected source until a package-linked GenManip adapter or
        exporter exists.

11.3.c package-linked successful completed episode rerun:
  owner: EOS / GenManip runtime
  goal: 用 11.3.b 选定的 successful policy/oracle lane 重跑 completed episode，
        保留 trace/log/initial/final keyframes/terminal episode_result，并重新生成
        Phase 11.2 evidence。
  evidence: new phase11_executed_episode_* evidence with episode_status=completed,
        score/sr consistent with success, and package linkage recorded.
  current status: closed as package-linked rollout source evidence by live
        BPL-19R attempt_002. Top evidence:
        phase11_3c_bpl19r_package_linked_live/phase11_package_linked_bpl19r_rerun.yaml
        records rerun_status=executed, selected_success_attempt=attempt_002,
        task_success=true, standard_model_score=1.0, blockers=[].
        The BPL-19R-to-Phase-11 bridge is now implemented and has produced
        phase11_executed_episode_bpl19r_success_evidence.yaml and
        phase11_success_predicate_bpl19r_success_evidence.yaml.

11.3.d strict predicate re-gate:
  owner: Scenario Forge
  goal: 消费 11.3.c 对应的 EOS/EBench predicate evidence，重新运行
        phase11-success-predicate --strict。
  evidence: phase11_success_predicate_gate.yaml passed, or failed/blocked with
        machine-readable blockers. No visual or human override is allowed.
  current status: closed for apple-to-bowl canary by
        phase11_success_predicate_bpl19r_success_gate.yaml, status=passed,
        blockers=[].

11.4.a post-execution review packet assembly:
  owner: Scenario Forge evidence handoff + EOS artifact producer
  goal: 准备 clean-room packet，只包含 initial/final keyframe 路径、hash、简短视觉期望
        和 upstream gate references，不包含实现细节、怀疑点或期望 verdict。
  evidence: phase11-post-execution-visual-review/v0.1 input packet is complete.
  current status: closed for BPL-19R attempt_002 with right_camera_first.jpg and
        right_camera_last.jpg retained under phase11_4_bpl19r_visual_review_frames/.

11.4.b clean-room visual review:
  owner: render-visual-reviewer
  goal: 对 initial/final keyframes 做 clean-room visual review，确认没有视觉层面的
        fallback material、空画面、严重遮挡、坏相机或几何异常。
  evidence: reviewer=render-visual-reviewer, review_mode=clean_room_visual_skill,
        verdict, visible evidence, and retake recommendation when needed.
  current status: closed by phase11_post_execution_visual_review_bpl19r_success.yaml,
        verdict=PASS.

11.4.c strict visual gate and retake loop:
  owner: Scenario Forge gate ingestion + EOS renderer / asset pipeline
  goal: Scenario Forge 严格消费 11.4.b evidence；如果 WARN/FAIL/缺 evidence，
        保留 blocked gate，并按 retake recommendation 修复相机、lighting、
        asset/material closure 或 execution keyframe retention 后重跑 11.4.a/11.4.b。
        人工不能改 verdict，只能触发重跑。
  evidence: phase11_post_execution_visual_review_gate.yaml passed, or blocked
        with old gate retained as history.
  current status: closed by
        phase11_post_execution_visual_review_bpl19r_success_gate.yaml,
        status=passed, blockers=[].

11.5.a single-task RC aggregation:
  owner: Scenario Forge
  goal: 聚合 package、asset lock、task contract、11.0-11.4 gates 和 release policy。
  evidence: phase11_single_task_release_candidate_gate.yaml passed 或 blocked-with-policy。
  current status: internal RC evidence bundle produced, but gate is blocked by
        policy in phase11_single_task_rc_bpl19r_internal_policy_blocked_gate.yaml
        because assets remain research-use and redistribution approval is missing.

11.6.a 3-5 task breadth canary:
  owner: Scenario Forge + EOS
  goal: 把同样无人化门禁扩到 3-5 个真实 EBench task，避免只对 apple-to-bowl 过拟合。
  evidence: phase11_small_multi_task_canary_gate.yaml passed 或带结构化 blocker。
  current status: progressed from package_count=1 to package_count=3 by adding
        ebench_soap_to_dish_canary and ebench_remote_to_holder_canary. Latest
        gate:
        phase11_small_multi_task_canary_three_task_remote_internal_rc_downstream_blocked_gate.yaml,
        package_count=3. The task-count blocker is removed. Soap-to-dish and
        remote-to-holder have attempted Phase 11.0 overview visual review.
        Remote-to-holder now has retained PASS Phase 11.0 evidence after fixing
        sidecar material closure, static tabletop contact, and task-specific
        overview framing. EOS has also closed remote Phase 11.1 live episode
        start with trace/log/initial keyframe evidence. The earlier zero-policy
        completed episode and failed predicate remain historical debugging
        evidence only. The current remote-to-holder path is the package-linked
        BPL-19R live rerun: `remote_to_holder_phase11_executed_episode_bpl19r_success_gate.yaml`
        and `remote_to_holder_phase11_success_predicate_bpl19r_success_gate.yaml`
        are both passed, with task_success=true and standard_model_score=1.0.
        Remote-to-holder also closed Phase 11.4 post-execution visual review
        and Phase 11.5 single-task RC aggregation. Its 11.5 gate is blocked only
        by license/redistribution policy, with all 11.0-11.4 technical gates
        passed. The suite gates have been rerun against this newer per-task
        evidence:
        phase11_small_multi_task_canary_three_task_remote_internal_rc_downstream_blocked_gate.yaml
        is blocked only by soap-to-dish blockers, not remote downstream gaps.
        Soap-to-dish has now closed Phase 11.0 using the ConvertAsset no-MDL
        relink package and retained engine-native render / visual-review
        evidence. Its active blockers are downstream 11.1-11.5 gates, not the
        overview visual/material gate.

11.6.a.4 remote pose / camera root-cause gate:
  owner: Scenario Forge package generator + EOS renderer.
  goal: 在继续 remote-to-holder retake 前，先区分“相机没拍好”和“package pose
        让 remote 变得不可识别”。检查 official GenManip task config、Scenario Forge
        source manifest、生成后的 scene/instances.yaml、scene/main.usda transform 和
        render camera metadata。
  evidence: root-cause note with official pose, generated pose, camera config,
        reviewed image path, clean-room WARN/FAIL reason, and chosen fix path.
  pass condition: either generated pose is confirmed official-aligned and a new
        camera retake receives render-visual-reviewer PASS, or generated pose is
        corrected under Scenario Forge tests before package regeneration and
        rerender/review. Manual inspection cannot override this gate.
  current status: closed for remote-to-holder Phase 11.0 by
        remote_to_holder_pose_camera_root_cause.yaml and
        remote_to_holder_phase11_visual_review_gate_contactfixed_cam3_pass.yaml.
        The manifest z contact fix is covered by
        test_remote_to_holder_example_places_remote_on_task5_tabletop.

11.7.a automated release gate:
  owner: Scenario Forge + policy evidence owner
  goal: 聚合 suite-level release-critical gates，只有 package/asset/adapter/visual/
        execution/predicate/license 全 pass 且 known_blockers=[] 才能 passed。
  evidence: phase11_automated_release_gate.yaml passed 或带结构化 blocker。
  current status: blocked by
        phase11_automated_release_three_task_remote_internal_rc_policy_blocked_gate.yaml.
        The retained 11.7 gate has been rerun after remote 11.4/11.5 closure.
        Remote is no longer listed as an execution/predicate/visual blocker; it
        appears only as an internal RC / policy-blocked package. The active
        blockers are soap visual/material/downstream execution gaps and global
        license/redistribution policy.
```

当前执行顺序：

```text
1. Phase 11.0-11.4 对 apple-to-bowl canary 已经全部由自动 evidence 关闭。
2. Phase 11.5 已生成 single-task internal RC evidence bundle，但 public release
   仍被 license/redistribution policy 自动阻塞。
3. 接下来继续做 11.6 的下游自动门禁：remote-to-holder 已有 real USD package、
   asset lock、task contract、passed Phase 11.0 overview visual gate、passed Phase
   11.1 EOS live-start evidence、package-linked BPL-19R 的 passed Phase 11.2
   executed episode gate、passed Phase 11.3 success predicate gate、passed Phase
   11.4 post-execution visual review gate，以及 Phase 11.5 internal RC /
   policy-blocked gate。Phase 11.6/11.7 已重跑，remote 的旧 downstream blockers
   已从 suite blocker list 中消失。soap-to-dish 已通过 ConvertAsset no-MDL relink
   和 clean-room visual review 关闭 11.0，并已通过 EOS live-start evidence 关闭 11.1；
   现在需要补齐 soap 11.2-11.5 后，11.6 才能重新聚合到 passed。
4. 同步推进 license/release policy：明确哪些 official EBench assets 只能 research-use，
   哪些可以 internal share，哪些需要替换或获取 redistribution approval。
5. 每补齐一个新增任务的 11.0-11.5 自动证据后，都重跑 11.6；11.6 passed 后再重跑
   11.7 automated release gate。只有 known_blockers=[] 且 license_policy=pass 时，
   才能叫 release candidate passed。
6. Phase 12 仍不提前；registry/viewer/multi-simulator 只能在 11.6/11.7 blocker
   机器可读且稳定后展开。
```

目标完成定义：

```text
single-task technical completion:
  一个具体 EBench task 达到 Phase 11.5，并且 11.0 overview visual、11.1 EOS
  task execution、11.2 completed episode、11.3 success predicate、11.4
  post-execution visual review 都是 passed；11.5 聚合出 retained RC gate。
  如果 release policy blocked，这仍然只能叫 internal RC / policy-blocked
  complete evidence bundle，不能叫 public release。

multi-task canary completion:
  3-5 个真实 EBench tasks 都有同样自动 evidence chain，11.6 small canary gate
  passed，且没有 unknown/manual blocker。任何 soap 这种 upstream material closure
  blocker 都必须先变成 repaired artifact 或结构化 handoff blocker。

release completion:
  11.7 automated release gate passed，known_blockers=[]，license/release policy
  passed。只有这个状态才允许对外说 public release candidate passed。

Phase-12 readiness:
  11.8 只检查 11.5/11.6/11.7 的 retained evidence 和 blocker 稳定性。人工看图、
  口头同意或 PM 确认都不是 readiness 输入。
```

面向产品经理的下一阶段口径：

```text
下一步不是进入 Phase 12，而是把 Phase 11 的无人化链路从 apple-to-bowl 扩到更多任务：

1. soap-to-dish 的 Phase 11.0 / 11.1 / 11.2 已关闭：EOS 已用
   `/tmp/ebench-soap-to-dish-canary-nomdl-relink` 作为 package-linked 输入，
   消费 Scenario Forge package、生成 runtime config、通过 IsaacSim41/GenManip
   runtime preflight，启动真实 episode，并保留 completed episode trace、runtime log、
   initial/final keyframes、final_state 和 strict 11.2 gate。
2. soap-to-dish 的 Phase 11.3 先在 zero-policy completed episode 上正确失败，
   但随后已通过 package-linked BPL-19R success rerun 关闭：fresh 11.2 / 11.3
   strict gates 都是 passed。旧 zero-policy 失败现在只是 retained history。
3. soap-to-dish Phase 11.4 已通过 top-camera retake visual review：predicate 成功
   和 visual readability 现在都已有 retained machine-readable evidence。旧的 default
   camera FAIL / camera-pair WARN 只作为历史调试证据保留。
4. soap-to-dish Phase 11.5 已聚合成 internal RC / policy-blocked：11.0-11.4
   技术 gate 全部 passed，剩余 blocker 是 research-use asset / redistribution approval。
5. 11.6 和 11.7 已重跑：multi-task canary 和 automated release gate 不再被 soap
   visual、execution 或 predicate 挡住；当前只剩 suite / release policy blockers。
6. 只有 11.5、11.6、11.7 的状态和 blocker 都是机器可读且稳定的，11.8 readiness
   才能允许 Phase 12 registry/viewer/multi-simulator 工作开始。
```

2026-07-05 规划更新：Phase 11 后续不再保留任何人工验收替代路径，并且
apple-to-bowl 已进入 policy-blocked internal RC 状态。

```text
11.2 / 11.3 已被 BPL-19R bridge 关闭：
  live multi-attempt rerun 在 attempt_002 记录 task_success=true、score=1.0，并保留
  package linkage；bridge 已把该结果转成 strict gate evidence，11.2 executed episode
  和 11.3 success predicate gate 均为 passed。

11.3.d 是成功谓词的硬门：
  只消费 EOS/EBench simulator-state predicate evidence。通过条件是
  predicate_status=true、score/sr 与成功一致、引用的 Phase 11.2 gate passed、
  blockers=[]。这次通过来自 structured evidence；截图、视频、人工确认、visual review
  都不能替代这个门。

11.4 是自动视觉复核，不是人工复核：
  11.3.d 通过后，initial/final keyframes 已交给 render-visual-reviewer 风格的
  clean-room review。可用证据是 right_camera_first/right_camera_last，不是看不清
  apple-in-bowl 的 overview post-action frame。WARN/FAIL/missing review 只会触发
  retake/re-render，不允许人工改成通过。

11.5 是第一个真正的“给 EBench 的完整 USD 任务包”里程碑：
  它聚合 real USD asset package、asset lock、task contract、EOS completed episode、
  success predicate、overview visual review、post-execution visual review 和 release policy。
  当前 gate 已生成 internal RC，但 license/redistribution 仍 blocked，所以结论是
  internal RC / blocked-for-public-release，而不是 public release。

11.6 和 11.7 才验证规模化：
  11.6 已从 package_count=1 推进到 package_count=3：apple-to-bowl 是 internal RC，
  soap-to-dish 和 remote-to-holder 是 package-static passed，任务数量 blocker 已解除。
  remote-to-holder 已经进一步关闭 11.0 overview visual、11.1 EOS live-start、
  package-linked BPL-19R 11.2 completed-episode gate、11.3 success predicate
  gate、11.4 post-execution visual review gate 和 11.5 single-task internal RC
  aggregation；zero-policy failed predicate 只作为历史 debugging evidence 保留。
  11.6/11.7 聚合已重跑，remote 不再作为 downstream blocker。soap 已通过
  ConvertAsset no-MDL relink、engine-native render 和 render-visual-reviewer PASS
  关闭 11.0，通过 EOS live-start evidence 关闭 11.1，并通过 completed episode
  evidence 关闭 11.2。随后 soap 11.3 在 zero-policy episode 上正确失败，
  但已经被 package-linked BPL-19R success rerun supersede：fresh 11.2 / 11.3
  strict gates passed。当前不是人工看图放行，也不是 predicate blocker，而是
  Phase 11.4 visual evidence blocker。11.7 已记录 suite-level release blocker：
  11.6 未过、soap-to-dish 11.4/11.5 未过，remote-to-holder 只剩 internal RC /
  policy-blocked，且 license_policy 未过。

Phase 12 不能提前：
  registry、viewer、多 simulator adapter、生态集成必须等 11.5 至少形成 single-task
  complete evidence bundle，并且 11.6/11.7 的多任务与 release-policy blocker 已经
  机器可读之后再展开。
```

2026-07-05 next Phase 11.x execution plan：

编号规则：

```text
11.6.x 只做多任务 scale-out 和新增任务补证：soap/remote 的 11.0-11.5
       自动 evidence、材质/相机 retake、EOS execution/predicate/RC 都在这里。
11.7.x 只做 suite release aggregation 和 policy re-gate：不新增人工验收，
       不把 policy blocker 混成视觉或执行 blocker。
11.8.x 只做 Phase-12 readiness：检查 retained gate、known blockers 和 policy
       状态是否足够稳定。11.8 不运行 episode，也不把 blocked gate 改成 passed。
Phase 12 只在 11.8 明确允许后启动。registry/viewer/multi-simulator 是生态扩展，
       不是补 Phase 11 执行闭环的替代品。
```

```text
11.6.a.1 remote material sidecar closure promotion:
  owner: Scenario Forge.
  action: keep the official asset intake fix, regenerate
        ebench_remote_to_holder_canary, retain package manifest/asset lock/main
        USD evidence, render with IsaacSim41, and run the strict 11.0 visual gate.
  pass condition: render_status=pass,
        material_runtime_preflight.status=pass, runtime log has no missing
        remote texture blocker, and render-visual-reviewer PASS after the camera
        retake. Until the visual review is PASS, remote 11.0 remains blocked.
  current status: closed for remote-to-holder Phase 11.0. Contact-fixed cam3
        has render_status=pass, material_runtime_preflight.status=pass, no
        blocking runtime log signal, clean-room visual PASS, and strict visual
        gate status=passed.

11.6.a.2 soap upstream material closure:
  owner: ConvertAsset/upstream asset lane, with Scenario Forge retaining only
        package evidence and handoff artifacts.
  action: either receive a repaired official task3 scene bundle or retain a
        ConvertAsset handoff record containing the failing package, dependency
        report, runtime log, render image, source provenance, and hashes.
  pass condition: regenerated soap package render has material preflight PASS,
        no missing texture/MDL translator blocker, and clean-room visual PASS.
  current status: closed for soap-to-dish Phase 11.0, Phase 11.1, and Phase
        11.2; still open for Phase 11.3 success, Phase 11.4, and Phase 11.5.
        The original blocker was confirmed upstream material
        closure; Scenario Forge then invoked the external ConvertAsset public
        CLI and retained a no-MDL artifact result. A temporary relink package
        passed static package check and USD mesh-face openability, then an
        IsaacSim41 engine-native overview render was rerun with task-specific
        soap/dish expectations. The new render metadata reports
        `material_runtime_preflight.status=pass`, the runtime log has no
        blocking material signals, clean-room `render-visual-reviewer` returned
        PASS, and Scenario Forge strict Phase 11.0 visual gate status is passed.
        The runtime log and static MDL texture audit both point to missing JPG
        files referenced by official task3 MDLs:
        c00e97e58585d8ddb0f8b16a724d05a13eae31.jpg,
        bf77ddc86c270d02747e7d0517103514ab51d0f.jpg, and
        c9c274d4ea1de7d059cec0a795b3b27e3941935.jpg. The package copy and the
        official task3 source both fail the same closure audit, so this is not
        the remote-style Scenario Forge sidecar-copy bug.
  retained evidence:
        soap_to_dish_phase11_material_closure_handoff.yaml and
        soap_to_dish_phase11_convertasset_handoff_v0_2.yaml. The v0.2 handoff
        records the corrected dry ConvertAsset command plan, source/render/log
        hashes, checked roots, expected `scene_noMDL.usd` return path, and the
        artifact bundle required before Scenario Forge can rerun soap Phase 11.0.
        The follow-up
        soap_to_dish_phase11_convertasset_nomdl_result_v0_3.yaml records the
        actual ConvertAsset run: exit_status=0, `scene_noMDL.usd` exists at
        /tmp/ebench-soap-to-dish-canary/assets/official_ebench_scene/scene_noMDL.usd,
        sha256=e1cf0d5b4d76cdc32cb57459be501e55e736f533effe17838191fa63ee107840,
        ConvertAsset audit `resultStrict=true` / `reason=strict-pass`, and
        mesh-faces=568692.
        soap_to_dish_phase11_nomdl_relink_static_gate_v0_4.yaml records the
        temporary relink package at /tmp/ebench-soap-to-dish-canary-nomdl-relink:
        `scene/main.usda` now references `scene_noMDL.usd`, the asset manifest
        and lock include the no-MDL artifact hash, `scenario-forge package check`
        returns Package OK, and ConvertAsset/Isaac Python `mesh-faces` on the
        relinked `scene/main.usda` returns 925370 faces.
        soap_to_dish_nomdl_relink_tabletop_overview_cam4.png,
        soap_to_dish_nomdl_relink_tabletop_overview_cam4_render_metadata.json,
        soap_to_dish_nomdl_relink_tabletop_overview_cam4_runtime.log,
        soap_to_dish_nomdl_relink_tabletop_overview_cam4_visual_review.yaml, and
        soap_to_dish_phase11_visual_review_gate_nomdl_relink_cam4_pass.yaml
        close soap Phase 11.0 as a visual/material gate. The subsequent
        soap_to_dish_phase11_task_execution_gate_live.yaml closes Phase 11.1.
        The refreshed follow-up
        soap_to_dish_phase11_single_task_rc_nomdl_relink_11_1_pass_policy_blocked_gate.yaml
        records the older post-11.1 RC state. That RC gate is now superseded by
        retained package-linked BPL-19R 11.2 completed-episode evidence,
        retained package-linked BPL-19R 11.3 passed predicate evidence, and the
        retained failed 11.4 visual review gate. The next RC rerun should block
        on soap 11.4 post-execution visual review and release policy, not on
        overview visual/material, EOS task-execution, missing completed episode,
        or predicate success.
  searched roots: exact filename search found no usable local copy under the
        checked EBench-Assets, GenManip, shared ConvertAsset, or user
        ConvertAsset roots. A repaired upstream source or ConvertAsset-owned
        normalized artifact is required.
  ConvertAsset handoff boundary: Scenario Forge may retain a dry command plan,
        source hashes, failing package path, dependency closure report, runtime
        log, render PNG, and expected returned artifact path, but it must not
        reimplement USD/MDL/texture conversion or synthesize replacement
        textures. ConvertAsset's public no-MDL CLI is the external boundary:
        `scripts/isaac_python.sh main.py no-mdl <scene.usd>` writes a sibling
        `*_noMDL.usd`; Scenario Forge command-plan tests should mirror that
        CLI shape instead of inventing conversion flags.
  returned artifact requirement: satisfied for the internal no-MDL relink visual
        canary. It does not grant public redistribution approval and does not
        prove task success, official material parity, or leaderboard evidence.
  current downstream action: soap-to-dish Phase 11.1 is now closed using
        /tmp/ebench-soap-to-dish-canary-nomdl-relink as the package-linked EOS
        input. EOS consumed the Scenario Forge package/task contract, generated
        runtime execution config, passed the IsaacSim41/GenManip environment
        preflight, started a real soap-to-dish episode, completed reset plus one
        zero-policy step, and retained trace/log/initial keyframe evidence.
        Retained gate:
        soap_to_dish_phase11_task_execution_gate_live.yaml, status=passed,
        blockers=[]. EOS then ran a completed zero-policy episode and Scenario
        Forge retained
        soap_to_dish_phase11_executed_episode_completed_evidence.yaml and
        soap_to_dish_phase11_executed_episode_gate_completed.yaml, status=passed,
        blockers=[]. That zero-policy result had score=0.0 / sr=0.0, so
        soap_to_dish_phase11_success_predicate_gate_failed.yaml remains retained
        failed history. EOS then ran a package-linked BPL-19R success attempt:
        soap_to_dish_phase11_3c_bpl19r_package_linked_live/phase11_package_linked_bpl19r_rerun.yaml
        selected attempt_000 with task_success=true and standard_model_score=1.0.
        The bridge produced
        soap_to_dish_phase11_executed_episode_bpl19r_success_gate.yaml and
        soap_to_dish_phase11_success_predicate_bpl19r_success_gate.yaml, both
        passed. The current concrete action is now visual, not predicate:
        retake/rerender Phase 11.4 keyframes so render-visual-reviewer can pass
        the post-execution visual gate.
  EOS render handoff contract: retained and superseded by passed render evidence
        as
        `soap_to_dish_phase11_eos_render_handoff_nomdl_relink_v0_5.yaml`.
        Current EOS repo search found R5/Newton official observation renderer
        experience, but did not identify a direct Scenario Forge
        package-linked IsaacSim41 overview render CLI that consumes
        `scene/main.usda`. The v0.5 handoff remains useful as the artifact
        contract for any future EOS-owned persistent render CLI, but the current
        soap 11.0 closure is already backed by retained PNG/metadata/log/review
        and a strict Scenario Forge gate.

11.6.a.3 task-specific overview camera retakes:
  owner: EOS renderer + render-visual-reviewer.
  action: remove apple/bowl-specific target anchors from scale-out render
        metadata. Use task contract objects and fixture targets to choose camera
        look-at/framing, then send only image path plus short expectation packet
        to render-visual-reviewer.
  pass condition: soap object + soap dish and remote + holder are visible and
        identifiable, the work surface and robot/spawn are not contradicted, and
        no fallback material or clipping blocker is reported.

11.6.a.4 remote pose / camera root-cause gate:
  owner: Scenario Forge package generator + EOS renderer.
  action: before additional remote camera tuning, compare official GenManip
        remote pose with Scenario Forge source manifest, generated
        scene/instances.yaml, scene/main.usda transform, and retained render
        camera metadata. Decide whether the fix is a Scenario Forge pose
        correction, a task-specific camera retake, or an upstream official task
        pose/rendering issue.
  pass condition: retained root-cause evidence plus a rerender reviewed by
        render-visual-reviewer. PASS is required to close remote Phase 11.0;
        WARN/FAIL remains blocked with retake recommendation.
  current status: closed. Scenario Forge corrected the static visual package
        z center from 0.11 to 0.0142 under test, retained bbox evidence showing
        the remote now sits on the task5 tabletop, and reran render-visual-reviewer
        to PASS.

11.6.b added-task EOS execution integration:
  owner: EOS / EBench adapter.
  action: repeat Phase 11.1 for mobile_manip/soap_to_dish and
        mobile_manip/remote_to_holder after their 11.0 gates pass. EOS must
        consume the Scenario Forge package/task contract, generate runtime
        config, pass the 11.1.c.0 runtime preflight, start a real episode, and
        retain trace/log/keyframe evidence.
  pass condition: phase11-task-execution gate passed for each task, or blocked
        with machine-readable EOS blockers. This is still Phase 11, not Phase 12.
  current status: closed for remote-to-holder by
        remote_to_holder_phase11_task_execution_gate_live.yaml, status=passed.
        Closed for soap-to-dish by
        soap_to_dish_phase11_task_execution_gate_live.yaml, status=passed.
        Soap 11.1 proves package consumption, runtime config generation,
        GenManip/IsaacSim41 preflight, live episode start, reset, one zero-policy
        step, cleanup close, trace/log retention, and initial keyframe retention.
        It does not prove completed episode, task success, model quality, release
        approval, or leaderboard evidence.

11.6.c added-task completed episode and predicate gates:
  owner: EOS / EBench predicate owner, with Scenario Forge ingesting evidence.
  action: retain completed episode evidence for each added task, then compute
        object_in_container-style predicate evidence from simulator state.
  pass condition: 11.2 and 11.3 strict gates pass per task. Visual review or
        manual inspection cannot override failed predicate evidence.
  current status: remote-to-holder Phase 11.2 and Phase 11.3 are passed on the
        package-linked BPL-19R live rerun evidence:
        remote_to_holder_phase11_executed_episode_bpl19r_success_gate.yaml and
        remote_to_holder_phase11_success_predicate_bpl19r_success_gate.yaml.
        Soap-to-dish also now has package-linked BPL-19R success evidence:
        soap_to_dish_phase11_3c_bpl19r_package_linked_live/phase11_package_linked_bpl19r_rerun.yaml
        records selected_success_attempt=attempt_000, task_success=true,
        standard_model_score=1.0, blockers=[].
        The BPL-19R bridge projected that run into fresh Phase 11.2 / 11.3
        evidence:
        soap_to_dish_phase11_executed_episode_bpl19r_success_evidence.yaml,
        soap_to_dish_phase11_executed_episode_bpl19r_success_gate.yaml,
        soap_to_dish_phase11_success_predicate_bpl19r_success_evidence.yaml, and
        soap_to_dish_phase11_success_predicate_bpl19r_success_gate.yaml. Both
        strict gates are passed. The earlier zero-policy soap 11.3 failure
        remains retained history, not the active blocker.
  implementation update: EOS BPL-19R wrapper mapping for soap-to-dish is
        unit-tested, dry-run verified, live-run verified, and bridged. A bridge
        bug in EOS path resolution was fixed with a regression test so rerun
        artifact refs can use repo-root-relative runtime_log paths. The current
        soap blocker is no longer predicate success; it has moved to Phase 11.4
        post-execution visual review.

11.6.d added-task post-execution visual review and RC aggregation:
  owner: render-visual-reviewer + Scenario Forge.
  action: run Phase 11.4 clean-room review on retained initial/final keyframes,
        then aggregate each task into a single-task RC gate with policy status.
  pass condition: 11.0-11.4 passed per task; 11.5 may still be internal RC /
        blocked-for-public-release if license policy remains blocked.
  current status: closed for remote-to-holder. Remote has passed 11.4 with
        remote_to_holder_phase11_post_execution_visual_review_bpl19r_success_gate.yaml
        and reached 11.5 internal RC in
        remote_to_holder_phase11_single_task_rc_bpl19r_internal_policy_blocked_gate.yaml.
        All remote 11.0-11.4 technical gates are passed; 11.5 is blocked only
        by release policy. Soap-to-dish now has 11.0, 11.1, 11.2, 11.3, and
        11.4 passed on the package-linked BPL-19R success lane plus top-camera
        retake visual review. The active soap 11.5 gate is
        soap_to_dish_phase11_single_task_rc_bpl19r_top_camera_retake_internal_policy_blocked_gate.yaml:
        all required technical gates are passed, and the remaining blockers are
        only release policy / redistribution approval. The older failed 11.4
        visual gates and WARN camera-pair reviews remain retained debugging
        evidence, not active blockers.

11.6.e small multi-task canary re-aggregation:
  owner: Scenario Forge.
  action: rerun suite phase11-small-canary after each added task reaches 11.5.
  pass condition: 3-5 real EBench tasks, all required gates passed or explicitly
        accepted as non-release blockers by the suite contract. If any release-
        critical gate remains failed/blocked, 11.6 remains blocked.
  current status: rerun after soap 11.4 top-camera retake PASS and soap 11.5
        internal RC / policy-blocked aggregation. Latest retained gate:
        phase11_small_multi_task_canary_three_task_internal_policy_blocked_gate.yaml,
        status=blocked. Apple, remote, and soap all have their 11.0-11.4
        technical evidence chains retained. Active blockers are now only
        single-task RC policy blockers for public release:
        apple_to_bowl_single_task_rc_policy_blocked_for_public_release,
        soap_to_dish_single_task_rc_policy_blocked_for_public_release, and
        remote_to_holder_single_task_rc_policy_blocked_for_public_release.

11.7.b automated release re-gate:
  owner: Scenario Forge + policy evidence owner.
  action: rerun suite phase11-release only after 11.6 passes and license /
        redistribution policy has either passed or remains explicit blocker.
  pass condition: package/asset/adapter/visual/execution/predicate/license all
        pass and known_blockers=[] for release_candidate_status=passed.
  current status: rerun after EBench author redistribution approval. Latest
        retained gate:
        phase11_automated_release_three_task_ebench_author_redistribution_pass_gate.yaml,
        status=passed. `visual_review`, `episode_execution`,
        `predicate_evaluation`, and `license_policy` are now pass; known_blockers=[].

11.8.a Phase-12 readiness checkpoint:
  owner: Scenario Forge roadmap / release owner.
  action: write one machine-readable readiness note that references the latest
        11.5 single-task RC gate, 11.6 small-canary gate, 11.7 release gate,
        policy status, and retained blocker list.
  pass condition: Phase 11.5 exists as a complete single-task evidence bundle;
        Phase 11.6 has either passed for 3-5 tasks or is blocked only by
        explicit, stable, machine-readable upstream/policy blockers; Phase 11.7
        has no unknown/manual blockers. Human approval is not an input.
  outcome: if readiness passes, Phase 12 may start registry/viewer/
        multi-simulator work. If readiness is blocked, Phase 12 remains deferred
        and the next action stays inside Phase 11.
  current status: readiness note has been rewritten after EBench author
        redistribution approval as
        phase11_8_phase12_readiness_ebench_author_redistribution_pass.yaml and
        formalized through `scenario-forge suite phase11-readiness --strict`.
        Latest retained gate:
        phase11_8_phase12_readiness_ebench_author_redistribution_pass_gate.yaml,
        status=passed, phase12_allowed=true. The audit found no manual
        blockers, no unknown blockers, and no remaining visual / execution /
        predicate / release-policy blockers. Phase 12 registry readiness may
        start from this retained three-task canary.
        Current active gate index:
        phase11_current_gate_index.yaml, overall_status=phase12_allowed,
        technical_closure_status=passed, public_release_status=release_candidate_passed.
```

2026-07-05 无人工验收最终落地规则：

```text
不再存在人工 gate：
  PM、研究员或工程师可以看图、看日志、提 issue、要求 retake 或标记 blocker triage，
  但不能把任何 Phase 11 gate 从 failed/blocked 改成 passed。

视觉 gate 的唯一通过来源：
  render-visual-reviewer clean-room evidence。适用范围包括 11.0 overview render
  和 11.4 initial/final keyframes。输入只能是图片路径、简短视觉期望、artifact
  hash/path 和必要的 upstream reference；不能把代码实现、怀疑点或期望 verdict
  喂给 reviewer。输出必须是结构化 PASS/WARN/FAIL、visible evidence 和 retake
  recommendation。WARN/FAIL/missing review 都只能触发 retake/rerender，不能人工放行。

非视觉 gate 的唯一通过来源：
  package/schema/asset/contract 归 Scenario Forge static gates；
  episode lifecycle、trace、runtime log、keyframe retention 归 EOS evidence；
  task success 归 EOS/EBench simulator-state predicate；
  license/release 归 policy evidence。视觉 review 不能替代 predicate、execution
  或 release policy。

下一步 Phase 11 执行顺序：
  1. remote-to-holder 已完成 package-linked BPL-19R successful rerun，并桥接成
     passed 11.2/11.3 evidence；11.4 post-execution visual review 也已 passed。
  2. remote 已完成 11.5 single-task RC aggregation；因为 license 仍 research-use，
     结论是 internal RC / policy-blocked。
  3. soap-to-dish 已用 ConvertAsset no-MDL relink package 关闭 11.0 visual/material
     gate，并已关闭 11.1 EOS execution integration、11.2 package-linked BPL-19R
     completed episode gate、11.3 package-linked BPL-19R success predicate gate
     和 11.4 top-camera retake post-execution visual review gate。
  4. soap 已完成 11.5 single-task RC aggregation；因为 license 仍 research-use，
     结论是 internal RC / policy-blocked。
  5. remote-to-holder 和 soap 都已补齐 11.0-11.5，且 11.6/11.7 已重跑移除旧的
     remote/soap technical blockers。
  6. 11.6/11.7 当前不是技术 blocker，而是 policy blocker：license/redistribution
     未过时只能是 internal 或 policy-blocked。
  7. 11.8 readiness 只检查机器可读 gate 和 blocker。任何 unknown/manual blocker
     都让 Phase 12 继续 deferred。
```

2026-07-05 无人工 Phase 规划落地：

```text
核心原则：
  “不需要人工”不等于“所有 gate 都由视觉 review 代替”。视觉 review skill 只替代
  原来人看图、人看截图、人判断画面是否可读的步骤；执行、成功、license 和 release
  仍然必须由对应 owner 的结构化 evidence 自动判断。

11.1 soap EOS task execution integration:
  owner: EOS / EBench adapter.
  input: /tmp/ebench-soap-to-dish-canary-nomdl-relink。
  output: phase11-eos-task-execution/v0.1 evidence + strict task-execution gate。
  pass claim: EOS can consume the Scenario Forge package and start a real episode.
  current status: closed by soap_to_dish_phase11_task_execution_gate_live.yaml,
        status=passed, blockers=[].
  no-human rule: 人不能说“我看它能跑”；必须有 config、preflight、trace、log、
        initial keyframe 和 gate status。

11.2 soap completed episode evidence:
  owner: EOS runtime.
  output: completed episode trace、runtime log、initial/final keyframes、final state
        和 strict executed-episode gate。
  pass claim: a complete episode artifact exists.
  current status: closed by
        soap_to_dish_phase11_executed_episode_completed_evidence.yaml and
        soap_to_dish_phase11_executed_episode_gate_completed.yaml, status=passed,
        blockers=[]. This does not prove task success because the terminal
        episode result is score=0.0 / sr=0.0.
  no-human rule: 人看视频不能替代 terminal episode_result 或 retained trace。

11.3 soap simulator-state predicate:
  owner: EOS / EBench predicate evaluator.
  output: success-predicate evidence + strict predicate gate。
  pass claim: task success is true according to simulator-state predicate.
  current status: passed by package-linked BPL-19R success evidence. Retained
        gate: soap_to_dish_phase11_success_predicate_bpl19r_success_gate.yaml,
        status=passed, blockers=[]. The older zero-policy failed gate remains
        retained history only. Task success is proven for this package-linked
        BPL-19R evidence lane; 11.4 visual review is now separately closed by the
        top-camera retake PASS gate. Neither predicate nor visual review closes
        release policy or public/leaderboard claims.
  no-human rule: render-visual-reviewer 和人工截图都不能把 failed predicate 改成 passed。

11.4 soap post-execution visual review:
  owner: render-visual-reviewer + Scenario Forge gate ingestion.
  output: clean-room initial/final keyframe review + strict post-execution visual gate。
  pass claim: the retained visual evidence is readable and not blocked by camera,
        material, geometry, or empty-frame problems.
  current status: passed by
        soap_to_dish_phase11_post_execution_visual_review_top_camera_retake_pass_gate.yaml.
        The earlier
        soap_to_dish_phase11_post_execution_visual_review_bpl19r_success_visual_failed_gate.yaml
        and camera-pair WARN review remain retained history: default overlook and
        early extracted camera pairs were not clean enough, so EOS produced a
        package-linked top-camera retake and render-visual-reviewer reviewed the
        denser top-camera frame to PASS.
        Follow-up target-identity diagnostic
        soap_to_dish_phase11_4_target_identity_and_retake_diagnostic.yaml is retained
        as history, but the authoritative target identity for future retakes must be
        derived from the package task contract, `scene/instances.yaml` source_uid,
        and USD scene evidence. Visual review judges whether the bound target
        container and soap relationship is readable; it must not promote a
        visually convenient non-target container into the task target.
  next action: no further visual retake is required for this lane. Future retakes,
        if needed for cleaner non-gate illustration, must keep target identity tied
        to task contract / source_uid / USD evidence and must not change policy
        input cameras.
  no-human rule: WARN/FAIL/missing review 只能触发 retake/rerender，不能人工放行。

11.5 soap single-task internal RC:
  owner: Scenario Forge.
  output: single-task release-candidate gate that aggregates 11.0-11.4 and policy。
  pass claim: if 11.0-11.4 pass but release policy blocks, this is an internal RC /
        policy-blocked complete evidence bundle, not a public release。
  no-human rule: PM 或工程师确认不能覆盖 missing gate、failed gate 或 policy blocker。

11.6 small multi-task canary:
  owner: Scenario Forge + EOS.
  output: 3-5 task small-canary gate。
  pass claim: the same no-human evidence chain works beyond one task。
  no-human rule: 每个任务都必须带自己的 11.0-11.5 evidence；不能用“苹果过了，
        其他任务人工看着也行”替代。

11.7 automated release gate:
  owner: Scenario Forge + policy owner.
  output: suite-level release gate。
  pass claim: package、asset、adapter、visual、execution、predicate、license 全部通过，
        known_blockers=[]。
  no-human rule: research-use asset 或 redistribution approval missing 必须保持
        blocked-for-public-release，不能人工签字改成 public。

11.8 no-human Phase-12 readiness:
  owner: Scenario Forge roadmap / release owner.
  output: readiness note that references retained 11.5/11.6/11.7 gates and blocker list。
  pass claim: Phase 12 can start only when the readiness note explicitly sets
        phase12_allowed=true. No manual/unknown blockers is necessary but not
        sufficient if release/license policy is still blocked。
  blocked claim: if the only remaining blockers are explicit policy/upstream
        blockers, 11.8 can close as a machine-readable readiness audit, but
        public registry/release Phase 12 remains deferred. Internal-only
        evidence browsing must be labeled as internal / policy-blocked and must
        not be called public release。
  no-human rule: 11.8 不运行 episode、不修 package、不做人工验收；它只检查是否真的
        达到了进入 Phase 12 的证据条件。

Phase 12:
  starts only after 11.8 passes. Registry、viewer、multi-simulator adapters and
  ecosystem integration are product expansion work, not substitutes for the
  Phase 11 EOS execution / predicate / visual-review closure。
```

2026-07-05 无人工验收执行版规划：

```text
目标：
  Phase 11 后续所有“看图判断”和“人工确认没问题”都从 gate 输入中删除。
  人仍然可以看 evidence、提出 issue、要求 retake、确认产品口径，但不能把任何
  failed/blocked/pending gate 改成 passed。

视觉 review skill 的职责边界：
  只负责视觉证据是否可读、是否明显错误、是否存在相机/遮挡/灯光/材质/几何问题。
  适用 artifact 是 11.0 overview render 和 11.4 execution initial/final keyframes。
  输入必须是 clean-room packet：图片路径、短视觉期望、必要 artifact hash/path、
  upstream reference。不能给 reviewer 代码实现、怀疑原因、期望结论或 gate 结果。
  输出必须是 reviewer=render-visual-reviewer、review_mode=clean_room_visual_skill、
  verdict=PASS/WARN/FAIL、visible_evidence、blockers/retake_recommendation。

视觉 review skill 不能替代的东西：
  不能证明 EOS 真消费了 Scenario Forge package；这归 11.1 task-execution gate。
  不能证明 episode 已完整结束；这归 11.2 executed-episode gate。
  不能证明任务成功；这归 11.3 simulator-state success predicate gate。
  不能证明 license 可以发布；这归 11.5/11.7 release policy gate。
  不能修复 USD/MDL/texture 闭包；缺材质或红/粉 fallback 必须走 asset/ConvertAsset
  handoff 或重新 materialize，再重新 render/review。

soap-to-dish 下一步无人化执行序列：
  11.2：已关闭。EOS 跑完整 episode，保留 terminal trace、runtime log、initial/final
        keyframes 和 final_state；Scenario Forge strict gate passed。该结果只证明
        completed episode artifact 存在。
  11.3：已关闭。EOS BPL-19R wrapper 的 `mobile_manip/soap_to_dish` mapping 已
        unit-tested、dry-run verified、live-run verified。Live rerun selected
        attempt_000，task_success=true，standard_model_score=1.0，blockers=[]。
        Bridge 已生成 fresh 11.2 / 11.3 evidence，strict gates passed。
  11.4：已关闭。default overlook pair 为 FAIL、早期 camera-pair review 为 WARN，
        但 top-camera retake 的 dense frame `top_camera_after_t7_009.jpg` 已通过
        independent render-visual-reviewer clean-room PASS。Strict 11.4 gate
        `soap_to_dish_phase11_post_execution_visual_review_top_camera_retake_pass_gate.yaml`
        status=passed, blockers=[]。目标容器仍由 task contract、
        `scene/instances.yaml` source_uid 和 USD scene evidence 共同决定；历史
        target-identity diagnostic 只能作为调试记录，不能替代 machine-readable
        package binding。
  11.5：Scenario Forge 聚合 soap 的 11.0-11.4 gates 和 release policy，产出
        single-task RC。EBench 作者 zhuzihou 已给出当前三任务 canary 的
        redistribution approval，最新 soap 11.5 gate
        `soap_to_dish_phase11_single_task_rc_bpl19r_ebench_author_redistribution_pass_gate.yaml`
        status=passed。
  11.6：已重跑。apple、remote、soap 都有自己的 11.0-11.5 证据链；
        latest gate `phase11_small_multi_task_canary_three_task_ebench_author_redistribution_pass_gate.yaml`
        status=passed，blockers=[]。
  11.7：已重跑。`phase11_automated_release_three_task_ebench_author_redistribution_pass_gate.yaml`
        中 visual_review、episode_execution、predicate_evaluation 和 license_policy
        均为 pass，known_blockers=[]。
  11.8：只做 Phase-12 readiness 检查，确认没有 manual/unknown blocker；不运行
        episode，也不修改技术 gate 结论。最新 readiness note
        `phase11_8_phase12_readiness_ebench_author_redistribution_pass.yaml`
        和正式 gate
        `phase11_8_phase12_readiness_ebench_author_redistribution_pass_gate.yaml`
        均为 status=passed、phase12_status=allowed、phase12_allowed=true。

产品经理口径：
  之后不能再说“人工看了图没问题所以过了”。只能说：
  - 视觉证据由 render-visual-reviewer PASS；
  - 执行证据由 EOS trace/log/keyframe/final_state PASS；
  - 成功证据由 EOS/EBench predicate PASS；
  - 发布证据由 release policy PASS。
  四类证据缺任何一类，就只能说 blocked / pending / internal RC。
```

2026-07-05 无人工 Phase 11 权威执行规则：

```text
为什么还需要 11.3.c：
  人工看过渲染图、render-visual-reviewer 给 PASS、或者历史 GenManip 目录里有成功
  result_info，都不能证明当前 Scenario Forge package 的任务成功。任务成功必须来自
  package-linked completed episode 的 simulator-state predicate。也就是说，11.3.c
  不是“再看一张图”，而是让 EOS/GenManip 用 Scenario Forge package-linked 配置跑出
  一个成功 terminal episode，再 bridge 成 11.2/11.3 strict gate evidence。

当前 soap-to-dish 状态：
  11.0 overview visual/material gate 已 passed。
  11.1 EOS live-start/task-execution gate 已 passed。
  11.2 package-linked BPL-19R completed episode gate 已 passed。
  11.3 package-linked BPL-19R success predicate gate 已 passed。
  11.4 top-camera retake post-execution visual review gate 已 passed。
  11.5 single-task RC 已形成 internal RC / policy-blocked evidence bundle。
  11.6/11.7 已重跑，当前 active blockers 是 policy/release blockers，不是
  soap visual、execution 或 predicate blockers。

无人工替代关系：
  render-visual-reviewer 只替代“人看图判断画面是否可读”的步骤：
  - 11.0 overview render review；
  - 11.4 post-execution initial/final keyframe review。

  render-visual-reviewer 不替代这些 gate：
  - 11.1 EOS 是否消费 package 并启动 episode；
  - 11.2 episode 是否 completed 且证据保留完整；
  - 11.3 task success predicate 是否 true；
  - 11.5/11.7 license、redistribution 和 release policy。

后续 Phase 11.x 顺序：
  1. 保留 soap 11.4 top-camera retake PASS 证据和 side-camera failed/blocked 诊断证据。
  2. 保留 EBench author redistribution approval evidence：
     `phase11_ebench_author_redistribution_approval_zhuzihou.yaml`。
  3. 11.5/11.6/11.7/11.8 当前结论已全部重跑为 passed；active index
     `phase11_current_gate_index.yaml` 记录 overall_status=phase12_allowed。
  4. 11.8 不新增人工验收，不运行 episode，不修改技术 gate 结论；它只消费
     retained gates 和 release-policy evidence。
  5. 下一步可以进入 Phase 12.0 Registry Readiness Freeze，用这个三任务 canary
     作为初始 release-candidate evidence bundle。

产品汇报边界：
  现在可以说“Phase 11 已经取消人工验收 gate，所有结论都走 owner evidence”。
  可以说“soap-to-dish package-linked BPL-19R 任务成功 predicate 已通过”。
  可以说“soap-to-dish 已形成完整 release-candidate evidence bundle：11.0-11.5
  passed”。
  可以说“11.8 readiness audit 已通过：没有人工/未知 blocker，没有视觉/执行/
  predicate/release-policy blocker，phase12_allowed=true”。
  可以说“这个三任务 canary 可以作为 Phase 12.0 registry readiness 的初始
  release candidate”。仍不能把这句话扩展成 leaderboard comparability 或全量
  benchmark 发布。
```

---

## 36. Phase 12：Ecosystem Integration / Registry / Multi-simulator Adapters

### 36.1 目标

让 Scenario Forge 成为跨 evaluator / simulator 的 package standard，并把 Phase 11
已经跑通的三任务 EBench canary 变成可索引、可浏览、可交接、可复现的 registry
基座。

Phase 12 从 retained Phase 11 evidence 开始。它 productize registry、viewer、
handoff examples 和 adapter descriptors；它不替代 EOS execution、predicate、
visual-review 或 release-policy gates。

当前 Phase 11.8 已允许进入 Phase 12：

```text
phase11_current_gate_index.yaml
  overall_status=phase12_allowed
  technical_closure_status=passed
  public_release_status=release_candidate_passed

phase11_8_phase12_readiness_ebench_author_redistribution_pass_gate.yaml
  status=passed
  phase12_allowed=true
```

Phase 12 的第一目标不是 hosted marketplace，而是 **local immutable package /
asset registry snapshot**。Hosted/internal browsing 可以稍后做；先保证 package、
asset lock、provenance、validation、EOS/visual/predicate evidence 和 release
policy status 能被稳定索引和复现。

2026-07-05 implementation status：

```text
Phase 12.0-12.6 已由 scenario-forge suite phase12 生成 retained evidence。

Command:
  PYTHONPATH=src python -m scenario_forge.cli suite phase12 \
    --suite docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/phase11_three_task_suite \
    --gate-index docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/phase11_current_gate_index.yaml \
    --strict

Authoritative current index:
  docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/phase11_three_task_suite/evidence/phase12_current_gate_index.yaml
    overall_status=phase13_allowed
    phase13_allowed=true
    12.0-12.6 status=passed

Registry snapshot:
  docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/phase11_three_task_suite/registry/registry_snapshot.yaml
  snapshot_digest=sha256:7dbf22b2ea435cb6c2eba19ee58d5c9aaebf728bea9a303a359439d2e0132007
```

这次实现刻意处理了一个真实证据问题：suite manifest 里的 runtime package
path 可以是 `/tmp`，但 public/reproducible registry 不能引用 `/tmp`。Phase 12
builder 会优先使用 retained evidence 中的稳定 artifact refs，并根据当前通过 gate
文件名中的 `nomdl_relink`、`contactfixed` 等 variant hint 选择最终通过版本。
收尾固化时进一步收紧：public registry、snapshot、viewer 和 handoff 输出不暴露
本机绝对 `source_uri`，包括 `/tmp/...`、`/cpfs/...` 和 `file://...`；这些来源会被
替换为指向 retained asset manifest 的 `retained-artifact://...` 引用。

### 36.2 产出

```text
1. Registry readiness freeze。
2. Local package / asset registry contract。
3. Immutable registry snapshot / resolver snapshot。
4. Read-only evidence / package viewer。
5. EBench / embodied-eval-os handoff examples。
6. Multi-simulator export descriptors。
7. Hosted/internal registry alpha。
8. Public release policy closure gate。
```

### 36.3 原则

Multi-simulator 是导出能力，不是核心格式污染。

核心永远是：

```text
manifest + task + scene instances + USD + assets + locks + validation + provenance
```

Phase 12 仍遵守 hard boundaries：

```text
- 不在 Scenario Forge 里添加 episode runner、model adapter、leaderboard 或 benchmark reporting。
- core/package/schema/assets/generation 层不 import simulator SDK。
- 不复刻 ConvertAsset USD/MDL/mesh/texture 转换逻辑。
- registry/viewer 只能展示 retained evidence，不能手动把 gate 改成 passed。
```

### 36.4 Phase 12 编号规划

Phase 12 已由 11.8 readiness 明确允许启动。下面阶段仍然按 gate 顺序推进；如果某个
gate blocked，只能回到对应 owner evidence 重新生成，不能人工覆盖状态。

```text
12.0 Registry Readiness Freeze:
  owner: Scenario Forge release owner.
  goal: 冻结 Phase 11.5 / 11.6 / 11.7 / 11.8 retained evidence，明确第一批
        registry package 列表、release status 和 claim boundary。
  input: phase11_current_gate_index.yaml, phase11_8_phase12_readiness_*_pass_gate.yaml.
  output: registry-readiness-freeze evidence with package refs, gate refs,
        manifest paths, asset_lock paths, USD entrypoints, validation refs,
        release-policy refs, content hashes.
  gate: registry-readiness-freeze-gate/v0.1 requires phase12_allowed=true,
        technical_closure_status=passed, public_release_status=release_candidate_passed,
        manual_blockers=[], unknown_blockers=[].

12.1 Local Package / Asset Registry Contract:
  owner: Scenario Forge asset/package layer.
  goal: 建立本地 registry metadata 和 query contract，不先承诺 hosted service。
        Registry entry 至少包含 package_id、version、task_family、asset_ids、
        asset_lock、license_policy、validation/evidence refs、release_status。
  output: package-registry-entry/v0.1, asset-registry-entry/v0.1,
        registry-query-contract/v0.1.
  gate: registry-contract-gate/v0.1 requires package_id/version uniqueness,
        asset_id is semantic id not local path, every public entry has release
        policy pass, and every asset has checksum/license/provenance metadata.

12.2 Registry Snapshot / Resolver Snapshot:
  owner: Scenario Forge asset/package layer.
  goal: 产出不可变 snapshot：package index、asset-lock snapshot、provenance index、
        resolver metadata、snapshot digest。证明 locked/fat package 可稳定恢复。
  output: registry_snapshot.yaml, resolver_snapshot.yaml, snapshot_digest.txt.
  gate: registry-snapshot-gate/v0.1 requires reproducible digest, no mutable
        local path in public entries, all asset locks resolve, all package manifests
        and USD entrypoints exist.

12.3 Read-only Evidence / Package Viewer:
  owner: Scenario Forge docs/UI adapter layer.
  goal: 展示 package manifest、scene USD entrypoint、asset lock、validation
        evidence、visual review evidence、EOS evidence links 和 policy status。
  output: viewer manifest / static site / docs page wired to retained evidence.
  gate: evidence-viewer-gate/v0.1 requires viewer status to be derived only from
        gate files; no UI/API path may change failed, blocked, pending, or
        policy-blocked gates to passed. Issue、retake、triage 记录必须与 gate
        status 分离。

12.4 EBench / EOS Handoff Examples:
  owner: adapter docs + EOS owner.
  goal: 提供最小可复现 handoff examples，说明 EBench/EOS 如何消费 Scenario Forge
        package、task contract、registry snapshot 和 evidence references。
  output: apple-to-bowl / soap-to-dish / remote-to-holder handoff examples pinned
        to frozen snapshot; adapter report and handoff manifest retained.
  gate: integration-example-gate/v0.1 requires commands are reproducible, examples
        point to frozen registry snapshot, and runtime claims cite EOS/EBench owner
        evidence.
  non-goal: 不把 EOS runner、model adapter 或 evaluator 搬进 Scenario Forge。

12.5 Multi-Simulator Export Descriptor Examples:
  owner: Scenario Forge adapters.
  goal: 输出 Isaac/Habitat/ManiSkill/OmniGibson 等 adapter descriptors 或
        export examples，证明 package standard 可跨 runtime。
  output: simulator export descriptors, adapter mapping examples, downstream
        runtime-smoke evidence refs where available.
  gate: multi-simulator-adapter-export-gate/v0.1 requires core layer has no
        simulator SDK imports; runtime smoke evidence is produced by downstream
        adapter/runtime, not Scenario Forge core.

12.6 Hosted/Internal Registry Alpha + Public Release Policy Closure:
  owner: policy / release owner.
  goal: 在 12.1-12.4 稳定后，提供 hosted/internal browsing alpha，并对 public
        registry / release policy status 给出可审计结论。
  output: hosted/internal registry alpha, public-release-policy-closure evidence.
  gate: public-release-policy-closure-gate/v0.1 requires license_policy=pass,
        redistribution_approval=true, known_blockers=[] for every package included
        in public release candidate；否则只能叫 internal registry / policy-blocked
        snapshot。
```

当前落地文件：

```text
12.0 evidence/phase12_0_registry_readiness_freeze.yaml
12.1 registry/package_registry.yaml
     registry/asset_registry.yaml
     registry/registry_query_contract.yaml
     evidence/phase12_1_registry_contract_gate.yaml
12.2 registry/registry_snapshot.yaml
     registry/resolver_snapshot.yaml
     registry/snapshot_digest.txt
     evidence/phase12_2_registry_snapshot_gate.yaml
12.3 viewer/readonly_index.yaml
     viewer/index.md
     evidence/phase12_3_readonly_viewer_gate.yaml
12.4 handoff/ebench_eos_handoff_examples.yaml
     evidence/phase12_4_ebench_eos_handoff_gate.yaml
12.5 adapters/simulators/export_descriptors.yaml
     evidence/phase12_5_multi_simulator_export_gate.yaml
12.6 registry/hosted_internal_registry_alpha.yaml
     evidence/phase12_6_public_release_policy_closure_gate.yaml
```

### 36.5 Phase 12 产品口径

可以承诺：

```text
- Phase 12 把 Phase 11 已验证的 package/evidence 做成 registry snapshot、
  read-only viewer、EBench/EOS handoff examples。
- Registry entry 可追溯到 manifest、asset_lock、provenance、validation、
  EOS/visual/predicate evidence 和 release policy。
- Scenario Forge 可以声明 package generation、validation、registry indexing
  和 EBench/EOS handoff readiness。
```

不能承诺：

```text
- Scenario Forge 自己运行 episode、评测模型或产出 leaderboard。
- Viewer 人工点击、截图看起来对、或者 visual review PASS 等价于 task success。
- Hosted registry 自动等价于 public release；public claim 仍要 release policy pass。
- Multi-simulator descriptor 等价于每个 simulator runtime 都跑通。
```

---

## 37. Phase 13：Image-Grounded Existing-Asset Task Package Factory

### 37.1 目标

Phase 13 放置第一版 “图片 + 一句话任务目标” 能力。

目标不是“任意图片自动重建真实 USD 资产”，而是：

```text
输入：一张桌面图片 + 一句话任务目标。
约束：资产必须来自 Phase 12 registry / resolver 中已有的 USD assets。
输出：一个完整 v0.2 EBench-compatible task package candidate。
关闭条件：candidate 通过 package validation、asset lock、USD compile、overview render、
         visual review、EOS/EBench execution、success predicate、post-execution visual
         review 和 release policy gates 后，才可称为正式任务包。
```

Phase 13 是 **Image-Grounded Existing-Asset MVP**。图片提供语义和空间提示；
一句话提供任务意图；Scenario Forge 负责把外部 perception/planning 结果导入为
owned contracts，并编译成可验证 package。

### 37.2 边界

应该在 Scenario Forge core / package layers 内：

```text
- image-task-request / image-to-scene-result / asset-selection-plan contracts。
- package 编译链：generation_plan、task/predicate/metric、scene/instances、
  scene/main.usda、asset_manifest、asset_lock、provenance/evidence。
- asset registry / resolver schema、checksum、license、physics profile、EBench
  eligibility 校验。
- 静态验证：asset lock 覆盖、USD reference、predicate binding、reachability、
  safety、adapter export readiness。
- evidence 记录：source image/text、producer version、confidence、assumptions、
  warnings、blockers、claim boundary。
```

必须是外部 adapter / upstream producer：

```text
- image understanding：detection、segmentation、mask、depth、camera pose、scale estimation。
- foundation model calls：image+text grounding、goal parsing、LLM planning。
- visual retrieval / embedding generation。
- 3D reconstruction、mesh generation、Gaussian splat、digital twin creation。
- ConvertAsset USD/MDL/mesh/texture conversion、mesh repair、material closure。
- simulator settling、rollout、policy/model execution、benchmark reports。
- LabBuilder / SimFoundry 本体 pipeline 或 fork。
```

Phase 13 release path 必须 fail closed：如果 upstream image result 缺资产、低置信、
无法绑定目标、没有 registry asset、缺 license、缺 material closure 或 predicate 不可验证，
则生成 blocker 或 real2sim / asset-intake handoff，不生成 public-ready package。

### 37.3 输入输出 contract 草案

`image-task-request/v0.1`：

```yaml
schema_version: image-task-request/v0.1
request_id: tabletop_photo_goal_001
source:
  image_uri: file://inputs/tabletop_001.jpg
  image_sha256: ...
  rights_status: user_provided_for_task_generation
goal:
  one_sentence_goal: Put the apple into the bowl.
  domain: tabletop_manipulation
  robot_profile: franka_panda_tabletop_v1
  target_export: ebench
constraints:
  package_mode: fat
  asset_source: phase12_registry_snapshot
  allow_new_asset_reconstruction: false
```

`image-to-scene-result/v0.1`：

```yaml
schema_version: image-to-scene-result/v0.1
result_id: tabletop_photo_goal_001_result
producer:
  name: external-image-grounding-adapter
  version: v0.1
source:
  image_uri: file://inputs/tabletop_001.jpg
  image_sha256: ...
goal:
  raw_text: Put the apple into the bowl.
  normalized_task_family: object_in_container
scene:
  coordinate_system: tabletop_right_handed_z_up
  units: meters
detections:
- detection_id: det_apple
  label: apple
  bbox_xywh: [120, 200, 80, 75]
  confidence: 0.91
  semantic_tags: [fruit, pickable]
  affordance_guesses: [pickable]
asset_requirements:
- role: object
  detection_id: det_apple
  asset_type: apple
  required_affordances: [pickable, rigid]
asset_candidates:
- role: object
  detection_id: det_apple
  selected_asset_id: ebench/apple/red_apple/v1
  score: 0.84
  matching_reason: category_and_size_match
instances:
- id: apple_001
  role: object
  asset_id: ebench/apple/red_apple/v1
  pose:
    xyz: [0.12, 0.04, 0.78]
    wxyz: [1, 0, 0, 0]
task_bindings:
  object: apple_001
  container: bowl_001
evidence:
  confidence_summary: usable_with_review
  blockers: []
```

### 37.4 Asset auto-selection 前置条件

Phase 13 依赖 Phase 12 registry metadata。每个可被自动选择的 asset 至少需要：

```text
- asset_id, version, content digest, metadata digest。
- asset_type, semantic_tags, category aliases, affordances, role suitability。
- canonical USD, collision USD, texture/material dependency closure。
- physics readiness: rigid/articulated, mass, friction, collision type, graspability, scale。
- license / use restriction / EBench export eligibility / public or internal policy。
- normalized status, ConvertAsset provenance, resolver version。
- thumbnail / engine render views / dimensions / material-color tags。
- visual matching embedding id/version if an upstream retrieval service uses embeddings。
- substitution/cousin groups for semantically equivalent replacements。
```

没有这些 metadata 时，asset selection 只能作为 blocked candidate，不得伪装成
release-ready package。

### 37.5 Phase 13 编号规划

```text
13.0 Image-Grounded Existing-Asset MVP Scope Freeze:
  owner: Scenario Forge product + adapter owners.
  goal: 限定第一版只做 tabletop manipulation；输入是 image + one_sentence_goal；
        资产只从 Phase 12 registry/snapshot 选；不做新资产重建。
  gate: image-goal-mvp-scope-gate/v0.1 requires domain, robot profile, target
        export, registry snapshot, no-new-reconstruction policy, and claim boundary.

13.1 Image + Goal Request Contract:
  owner: Scenario Forge schemas/adapters.
  goal: 定义 image-task-request/v0.1 和 image-to-scene-result/v0.1。
  gate: image-goal-intake-provenance-gate/v0.1 requires image hash/source/rights,
        text goal, producer identity, model/pipeline version, and manual/unknown
        blockers empty.

13.2 Visual Hints / Task Intent Extraction:
  owner: external perception adapter + Scenario Forge importer.
  goal: 外部 image+text grounding 产出 detections、roles、spatial hints、
        task_family、uncertainty 和 blockers。
  gate: image-understanding-candidate-gate/v0.1 requires candidates are explicit,
        top-k ambiguity recorded, low-confidence detections blocked, and no runtime
        success claim is made.

13.3 Registry Asset Selection Plan:
  owner: Scenario Forge asset registry/resolver.
  goal: 将 visual hints 转成 registry query，选择已有 USD assets。
  gate: asset-registry-match-gate/v0.1 requires selected_asset_id, asset_digest,
        license, source_uid, matching score/reason, rejection reasons for top
        alternatives, and no unresolved required role.

13.4 Goal-to-Task Contract and Layout Plan:
  owner: Scenario Forge generation/task/layout layers.
  goal: 将 one_sentence_goal 和 selected assets 编译成 task_contract、
        scene instance role binding、success predicate、layout constraints。
  gate: goal-to-task-contract-gate/v0.1 requires object/source/target/container
        bindings, simulator-state predicate, safety rules, and reachability/layout
        checks. 图片判断不能作为 predicate。

13.5 Scene USD / Asset Lock / Materialization:
  owner: Scenario Forge USD compiler + asset lock layer.
  goal: 生成 scene/instances.yaml、scene/main.usda、asset_manifest、asset_lock、
        package validation 和 material runtime preflight。
  gate: scene-layout-usd-materialization-gate/v0.1 requires USD entrypoint,
        asset lock, layout/scale/collision/support checks, no missing material
        dependency, and no placeholder asset on release path.

13.6 Factory Overview Visual Gate:
  owner: renderer owner + render-visual-reviewer.
  goal: 对生成 package 做 engine-native overview render 和 clean-room visual review。
  gate: factory-overview-visual-gate/v0.1 requires image hash/metadata,
        material preflight pass, render-visual-reviewer PASS. It only proves
        visual readability, not asset identity or task success.

13.7 Package Adapter Preflight:
  owner: Scenario Forge adapters.
  goal: package check、EBench export、policy preflight、registry snapshot insertion。
  gate: package-adapter-preflight-gate/v0.1 requires package/schema/asset/policy
        validation and no simulator SDK import in core.

13.8 Execution / Predicate Canary:
  owner: EOS/EBench adapter owner + Scenario Forge gate ingestion.
  goal: 对生成 package 复用 Phase 11 execution、completed episode、success predicate、
        post-execution visual review、single-task RC 聚合链。
  gate: execution-predicate-canary-gate/v0.1 requires EOS execution evidence,
        completed episode, predicate true, post-execution visual PASS, release
        policy pass.

13.9 Batch Factory Quality Gate:
  owner: Scenario Forge evaluation + registry owner.
  goal: 从单任务 MVP 扩到 batch factory，检查去重、split leakage、difficulty、
        coverage、failure rate、blocker taxonomy。
  gate: batch-factory-quality-gate/v0.1 requires machine-readable quality report
        and retained blockers for every failed/blocked request.
```

### 37.6 防人工放行规则

Phase 13 的关键风险是 confidence laundering：把 perception confidence、视觉 review
PASS 或人工看图满意，错误地当成 asset identity、task binding 或 task success。

规则：

```text
1. render-visual-reviewer 只证明画面可读，不证明选对资产、不证明目标绑定正确、
   不证明 predicate 成功。
2. 目标身份必须来自 task_contract + scene/instances.yaml source_uid + asset_lock。
3. 任务成功必须来自 EOS/EBench simulator-state predicate。
4. 人工修正只能生成新的 versioned input/evidence，然后重跑 gate。
5. viewer 只能展示 retained evidence，不能提供 status override。
6. 如果 registry 缺资产，输出 real2sim-request 或 asset-intake blocker；
   不允许用 placeholder asset 进入 release path。
```

### 37.7 产品口径

第一版可以承诺：

```text
- 在受限 tabletop domain 和已有 USD asset registry 内，用户给一张桌面图和一句话
  任务目标，系统生成一个完整 v0.2 task package candidate。
- Candidate 包含 manifest、task contract、scene/instances、scene/main.usda、
  asset lock、provenance、validation、EBench export 和 evidence refs。
- 只有通过 Phase 13 gates 并复用 Phase 11 execution/predicate/release gates 后，
  才称为正式 EBench-compatible task package。
```

第一版不能承诺：

```text
- 任意图片自动重建新 USD 资产。
- 任意开放场景都能自动变成可执行任务。
- 图片理解 confidence 等价于 task success。
- Scenario Forge 自己跑 episode、评测模型或发布 leaderboard。
- 缺 registry asset 时自动生成 public-ready package。
```

---

## 38. 推荐的 repo 结构演进

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

## 39. 产品 OKR / KPI

### 39.1 North Star Metric

```text
Number of validated EBench-compatible scenario packages generated per suite with reproducible assets and explicit success predicates.
```

中文：

```text
每个 suite 中自动生成并通过验证的、资产可复现且成功条件明确的 EBench-compatible 任务包数量。
```

### 39.2 阶段性 KPI

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

### 39.3 产品质量红线

```text
1. 没有 asset lock 的任务包不能进入 EBench export。
2. 没有 success predicate 的任务不能进入 suite。
3. 没有 license 的资产不能进入 release。
4. USD reference 不可解析的 package 不能通过 validation。
5. 任务语义只写在自然语言里是不合格的。
6. not_run 不能伪装成 passed。
```

---

## 40. 风险与直接决策

这里不写“未来再研究”的保守话术，直接给默认决策。

### 40.1 风险：资产包太大

默认决策：

```text
仍然以 fat package / locked package 为标准。
用 content-addressed dedupe 和 suite-level asset store 解决体积问题，不牺牲复现性。
```

### 40.2 风险：USD 生态复杂

默认决策：

```text
Scenario Forge 只生成 USD reference stage 和基础 metadata。
复杂材质、mesh 修复、MDL 转换交给 ConvertAsset 或外部工具。
核心 package 不 import heavy simulator SDK。
```

### 40.3 风险：EBench 真实格式变化

默认决策：

```text
核心 package 不跟 EBench 格式强绑定。
EBench adapter 独立演进。
Scenario Forge 的 portable contract 保持稳定。
```

### 40.4 风险：自动生成任务质量不稳定

默认决策：

```text
引入 validation ladder 和 suite quality evidence。
低质量任务可以生成，但不能进入 release suite。
```

### 40.5 风险：LabBuilder / SimFoundry / RoboGenesis 没有可复用代码

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

### 40.6 风险：早期 schema 频繁变化

默认决策：

```text
v1.0 前不背兼容包袱。
每次 schema 变化提供 migration。
v0.2 直接面向产品目标设计。
```

---

## 41. 近期执行清单

### 41.1 立即更新文档

```text
1. 添加 docs/strategy/scenario-forge-ebench-auto-factory-roadmap.md。
2. 添加 docs/design/package-v0.2.md。
3. 添加 docs/design/asset-lock.md。
4. 添加 docs/design/usd-scene-compiler.md。
5. 添加 docs/design/ebench-adapter.md。
6. README 增加“EBench task package factory”路线说明。
```

### 41.2 立即更新 package scaffold

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

### 41.3 立即新增测试

```text
tests/test_asset_lock.py
tests/test_fat_package.py
tests/test_usd_scene_compiler.py
tests/test_predicate_bindings.py
tests/test_ebench_adapter.py
tests/test_package_v02_scaffold.py
```

### 41.4 立即新增 CLI

```text
scenario-forge assets check
scenario-forge assets lock
scenario-forge scene compile
scenario-forge export ebench
scenario-forge generate package
scenario-forge generate suite
```

### 41.5 立即构建最小演示

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

## 42. 最小可行产品：MVP 定义

### 42.1 MVP 不是普通 scaffold

MVP 必须证明：

```text
Scenario Forge 能自动生成一个带真实资产锁、USD 场景、任务语义、机器人配置、成功条件、验证报告和 EBench export 的 package。
```

### 42.2 MVP 必须包含

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

### 42.3 MVP 不需要包含

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

## 43. Product Bet：我们真正的壁垒是什么

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

## 44. 与 LabBuilder / SimFoundry / RoboGenesis 的最终关系

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

## 45. 关键命名建议

### 45.1 产品级命名

```text
Scenario Forge
  Product identity：EBench task package factory
  Technical identity：portable scenario package compiler
```

### 45.2 内部模块命名

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

### 45.3 避免命名

不要把项目改名为 LabForge / LabBuilder / RoboGenesis / SimFoundry 的变体。

这些是能力来源，不是我们的产品身份。

---

## 46. 参考资料

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

## 47. 最终建议

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
