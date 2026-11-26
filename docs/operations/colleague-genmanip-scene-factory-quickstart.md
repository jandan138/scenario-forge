# GenManip 场景工厂 + 机器人闭环验证 · 同事快速复用指南（同集群 CPFS 版）

> 目标：让团队同事在 **5 分钟内** 直接复用「星巴克 Mastrena II 拿铁（多刚体咖啡豆 + 动态电子秤 + 单杯磨豆机 + 120 Hz 零漏液双相 PBD 液体 + Lift2 R5a 闭环轨迹）」同款工作流，从零生成任意新的 **GenManip 可加载场景包 (`collected_package`)** 并自动跑通机器人闭环验证与轨迹/视频合成。

---

## 1. 整套流程涉及的 4 个仓库与职责

| # | 仓库 | 地址 / 分支 | 职责 | 同事是否需要自己改代码 |
| :-: | :--- | :--- | :--- | :--- |
| 1 | **`scenario-forge`**（总入口） | `https://github.com/jandan138/scenario-forge.git` (`main`) | 场景工厂 Agent Skill、多自由度资产与门店生成、视觉盲审、导出 GenManip `collected_package` | **主要工作目录**（在此打开 Coding Agent） |
| 2 | **`trajectory-forge`** | `https://github.com/jandan138/trajectory-forge.git` (`main`) | Lift2 R5a / 机械臂特权闭环验证、PBD 液体/多刚体/外设仿真后端、合成 `episode_trajectory.npz` 与 `progression.mp4` | 仅需为新任务编写 1 个特权控制器 `.py` |
| 3 | **`ConvertAsset`** | `https://github.com/jandan138/ConvertAsset.git` (`main`) | Blender/程序化资产转 SimReady OpenUSD、材质/MDL 闭合与准入质检 | 无需改代码（命令行/API 自动调用） |
| 4 | **`GenManip-Sim`** | `https://gitee.pjlab.org.cn/L2/MultimodalVLA/GenManip-Sim.git` (`feature/pioneer`) | 底层 Isaac Sim 4.1 + GenManip 仿真与机器人运行时 | 无需改代码（直接使用远端 `feature/pioneer`） |

> **说明**：如果只是新建场景给 GenManip 加载、遥操或生成演示轨迹，**不需要**配置 `embodied-eval-os`。

---

## 2. 同集群 CPFS 5 分钟环境复用

在同集群 DSW / GPU 节点上，**无需重装 Isaac Sim 4.1 或 Blender**，直接复用共享 Conda 环境并 clone 代码仓即可：

```bash
mkdir -p ~/dev && cd ~/dev

# 1. 拉取核心仓库
git clone https://github.com/jandan138/scenario-forge.git
git clone https://github.com/jandan138/trajectory-forge.git
git clone https://github.com/jandan138/ConvertAsset.git
git clone https://gitee.pjlab.org.cn/L2/MultimodalVLA/GenManip-Sim.git -b feature/pioneer

# 2. 确认两个预装 Python 环境可用（同集群直接复用）
# (A) 编排 / USD 读写 / trajectory-forge CLI 环境：
export SF_PY="/cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-py310/bin/python"
# (B) 无头 Isaac Sim 4.1 + GenManip 仿真环境：
export SIM_PY="/cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/embodied-eval-os-sim-isaacsim41-genmanip-py310/bin/python"

# 3. 将自己的 clone 以 editable 模式挂到 PYTHONPATH（不污染共享环境）
export PYTHONPATH="$HOME/dev/scenario-forge/src:$HOME/dev/trajectory-forge/src:$HOME/dev/ConvertAsset:$PYTHONPATH"
```

---

## 3. 端到端 4 步工作流（以新建任意 GenManip 场景为例）

1. **Step 1 · 资产与门店生成（`scenario-forge`）**
   - 在 `scenario-forge` 目录启动你的 Coding Agent（支持 **Antigravity / Claude Code / Codex / Cursor**）。
   - Agent 自动加载两个内置 Skill：
     - [`skills/agentic-scene-factory/SKILL.md`](../../skills/agentic-scene-factory/SKILL.md)（主题门店/房间生成 + 空间对齐 + 独立视觉盲审）
     - [`skills/hunyuan-isaac-articulation-assets/SKILL.md`](../../skills/hunyuan-isaac-articulation-assets/SKILL.md)（参数化多自由度主力设备 + 矢量 UI 面板 + `GEN-008` 门控）
2. **Step 2 · SimReady 准入与 GenManip 场景包导出（`ConvertAsset` + `scenario-forge`）**
   - 所有动态道具与主力设备通过 `ConvertAsset` 材质闭合与准入，静态物理验证（17+ 动态道具零漂移 `0.000 mm`）。
   - 导出标准 GenManip `collected_package/`（包含 `scene.usda`、`tasks/config.yaml`、`meta_info.pkl`、`episode_metadata.json`）。
3. **Step 3 ·（可选）高阶物理注入（液体 / 多刚体颗粒 / 交互外设）**
   - **零漏液双相 PBD 液体（WET-OP / Starbucks v4 黄金配方）**：
     - `tasks/config.yaml` 开启 `TimeStepsPerSecond: 120` + `EnableStabilization: True`；
     - 容器侧壁采用 **32 瓣凸体围板**（壁厚 `10 mm` + `contactOffset` 缓冲），满足 `v_robot (0.12 m/s) << maxVelocity (0.50 m/s) << t_wall/dt (1.20 m/s)`；
     - 原生 `PhysxParticleIsosurfaceAPI` 所有属性必须使用 `custom=False`，`gridSmoothingRadius = 2.0`（网格单位）。
   - **稳定多刚体小颗粒（如 24 颗咖啡豆 / 药片 / 食材）**：
     - 每颗刚体使用 `UsdGeom.Xform`（`RigidBodyAPI` + `MassAPI`）+ 精雕 `Visual` 网格 + 解析 `UsdGeom.Capsule` 碰撞体（`purpose="guide"`，**切勿**用 `visibility="invisible"`，且必须用 `prim.AddAppliedSchema(...)` 追加 schema）；
     - 配合防抖休眠参数，1 秒静态漂移可压到 `< 0.05 mm`。
   - **可抓容器防滑**：并行夹爪抓取圆锥碗容易打滑，给碗下部增加 `30–35 mm` 直筒圆柱抓取腰身（如 `Ø 68 mm`）。
4. **Step 4 · 机器人闭环验证与轨迹/视频合成（`trajectory-forge`）**
   - 为新任务编写 1 个特权控制器，运行 `trajectory-forge solve`（`search` → `full_horizon_gate` → `trajectory_synthesis`）。
   - 自动产出：
     - `episode_trajectory.npz`（干净单条演示轨迹，可进一步转 LeRobot）
     - `progression.mp4`（含第三人称总览 + 右上角关键操作区 PiP 画中画）
     - 视觉核验关键帧与自包含汇报 HTML。

---

## 4. 一键复制给 Coding Agent 的启动 Prompt

在 `scenario-forge` 目录下打开 Antigravity / Claude Code / Codex / Cursor，直接粘贴以下 Prompt（只需替换 `【...】` 里的场景描述）：

```text
请先阅读本仓库的 AGENTS.md、skills/agentic-scene-factory/SKILL.md、skills/hunyuan-isaac-articulation-assets/SKILL.md 以及 docs/operations/colleague-genmanip-scene-factory-quickstart.md。

我要新建一个给 GenManip 使用的仿真场景并完成 Lift2 R5a 闭环验证：
- 场景主题：【例如：日式拉面店后厨 / 奶茶吧台 / 家庭早餐厨房】
- 核心交互设备与道具：【例如：带按键的多自由度制冰机、可抓取量杯、电子秤、杯子、出餐托盘】
- 任务流程（分阶段）：【例如：Stage 0 称量固体配料 -> Stage 1 倒入设备处理 -> Stage 2 放杯接取液体 -> Stage 3 倾倒混合 -> Stage 4 送至出餐区】
- 物理要求：【若涉及液体：使用 120 Hz + EnableStabilization=True + 32 瓣凸壁 + 原生 PhysxParticleIsosurfaceAPI (custom=False)；若涉及多刚体小颗粒：使用 Visual 网格 + purpose="guide" 解析胶囊碰撞体 + AddAppliedSchema】

请按以下标准端到端执行：
1. 生成房间、多自由度主力设备与全部道具，经 ConvertAsset 准入并做独立视觉盲审；
2. 导出标准 GenManip collected_package（同步 scene.usda、tasks/config.yaml、meta_info.pkl、episode_metadata.json）；
3. 使用 trajectory-forge 编写特权控制器，在无头 Isaac Sim 4.1 跑通 full_horizon_gate = 1.00（snapshots_used=0, firewall_verified=True），合成 episode_trajectory.npz 与 progression.mp4；
4. 逐帧视觉检查关键帧，确认零穿模、零漏液/零漂移后，输出完整验收数据与路径。
```

---

## 5. 参考样板（星巴克 Mastrena II v6 实测标杆）

- 场景配置：`configs/domain_packs/starbucks_barista_pbd/`、`configs/out_of_domain_tasks/starbucks_barista_pbd_latte.yaml`
- 集群内完整参考产物目录：
  `/cpfs/user/zhuzihou/dev/scenario-forge/external_artifacts/starbucks_barista_pbd_20261125/v6_single_dose_grinder/`
