# Task10 真液体滴定修复与交付

状态：双运行时完整物理验收、最终视觉复核和 MP4 全片解码通过；共享场景已发布。完整任务包及 ZIP 由匹配证据的归档器生成。

用户批准以 chenjiantong 当前 `task_10_titration_experiment/scene.usd` 为唯一场景基准，
在新的任务包中将接收锥形瓶与滴定管液体改为 GPU PBD，保持透明材质和原显色曲线。
磁力搅拌器只修复静态显示 OFF→ON；没有新增物理搅拌。
目标共享目录为 `scene_usd/zzh_fixed/task_10_titration_experiment/`，默认 Isaac 4.1，
另有 4.5 入口。共享目录仅放 USD 和 SubUSDs；证据与无机器人视频留在任务包。

## 已批准的物理边界

采用受控、守恒的源液体→滴嘴转移：实际扣除管内粒子体积，在滴嘴下生成等量真实粒子，
随后由重力和碰撞计算运动。不是解析亚毫米阀道的毛细流模拟。
下阀预充液使用独立精细粒子，保留被动流体；不挪到上方液柱以凑体积。
隐形数值封口与向外加厚碰撞壳属于生产者声明的近似，内腔和可见玻璃几何仍以源为准。
没有机器人接触空间或真实化学动力学资格。

计量依据为唯一试剂粒子实际向下穿越瓶口后接触瓶内真实液体，初始瓶内液体、空中液滴和泼洒不推进显色。
粒子加入接收液体系时保留世界坐标及速度。重置恢复各粒子集、剂量账目、颜色与成功状态；
夹具负责恢复容器位姿和关闭阀门。成功条件沿用原连续显色阈值及关阀保持 3 仿真秒。

## 职责与文件

ConvertAsset 的 `scripts/task10_pbd_producer.py` 负责粒子、碰撞与材质闭包。
Scenario Forge 消费冻结快照，添加任务状态与打包，不承担通用资产转换或碰撞修复。

- `scripts/task10_pbd_policy.py`：流量、显色、守恒剂量账目。
- `scripts/task10_pbd_runtime.py`：真实关节／粒子读取、受控转移与遥测。
- `scripts/task10_pbd_geometry.py`：独立内腔与自由液面数值检查。
- `scripts/build_task10_pbd_candidate.py`：生产者候选与嵌入控制器。
- `scripts/build_task10_pbd_package.py`：v0.2 任务包。
- `scripts/export_task10_colleague_layout.py`：保持资源字节及 USD 语义的共享目录导出。
- `scripts/validate_task10_pbd.py`：无机器人场景验证夹具，不是 episode runner。

工作证据位于 `outputs/task10_real_liquid_20261009/`。
旧 `api_smoke_01`／`api_smoke_02` 的接口运行不能支撑保液资格；它们的液位明显偏低，
首剂入瓶率不足，失败轨迹保留。生产者的新连续 SDF 快照仍需校准液位与微小穿壁。

## 规范同步

遵循 ASSET-001 的生产者边界、USD-001/002/004 的运行时、闭包与物化要求、MAT-001..006 的液体与材质要求、
STATE-001..006 的实际输入、重置和成功语义，以及 VAL-001..007 的分层证据与交付要求。
现阶段没有通用规则变更：发射器、容器离散化、PBD 参数和验收容差均限定于本任务，
尚未获得足以推广的运行证据。操作说明与本记录随验证结果更新；不改写历史任务包。

## 本轮接口证据与修正

4.1 逐剂轨迹暴露了原 OnPhysicsStep 脚本的时序错误：开阀时读到尚未回写的 USD 点，
每次 resize 又把旧位置写回；关阀后堆叠液滴才散开。旧接口计数 smoke 不足以证明连续运动。
`api45_post_readback` 使用显式物理完成／USD 同步后的对照调用，释放 2.727 mL，入瓶
2.727 mL，泼洒为 0。`api45_graph_sync` 将显式 readback 放入内置 compute 入口，同样全量入瓶；
开阀过程中收到的体积逐帧增加，飞行中约 0.054 mL。没有回写逃逸位置或冻结粒子。
同一快照的容器／液面门禁仍失败，因此整体报告仍为 failed；不得将它作为正式物理资格。
后续加入 continuous_delivery_while_open 检查，防止只在关阀后观察计数而漏掉该问题。

仓库检查本轮 `make check`：1237 passed、1 skipped；Ruff、两套 smoke 和 diff 检查通过。
随后增加的 SDK 调度／渲染代码仍需对应运行证据，不借用之前的检查结果宣称验收完成。

4.1 的非空→空 Falling 等值面另触发 sparse-grid CUDA 错误。
只在空集时关闭 `physxParticleIsosurface:isosurfaceEnabled`、保留 ParticleSystem 插入场景后，
`api41_empty_iso_only` 的连续收液、2.727 mL 全量入瓶、各集总质量及 PhysX error stream 检查通过。
切换 `particleSystemEnabled` 的尝试触发 addParticleBuffer-not-inserted，已撤销并保留失败日志。

`replay_preview_05c` 使用 SDK 暂停状态的等值面重建；渲染前后粒子坐标逐值相同。
实现者目视确认透明液面和显示屏红色 ON；该预览使用未合格物理快照，不能充当最终视频。
源滴定管与锥形瓶的实际 OmniGlass 参数已逐项检查：glass_color=(.97,.99,1)、IOR=1.333、
cutout_opacity=1、enable_opacity=False、thin_walled=False、frosting_roughness=.02，两者一致。
不同粒子体系的表面输出连接到各自 Shader，接收液染色不会修改管内液体。

旧 `full45_controller_preflight` 的逐步 set_pose/清零速度晃瓶产生 5268 粒穿底，已中止，
不将该 teleport 夹具结果解释为合格的运动验证。改为容器 kinematic targets，保留全部液体动态；
该属性只在验证 session 层生效，干净资产仍保留源刚体设置。新流程需重新获得运动资格。
后续一轮启动时 Vulkan 崩溃，未产生可用运动证据。非渲染验证改为关闭 viewport，
并通过 World.render 的 playSimulations=False 路径定期刷新 Kit 队列，检查不会额外推进任务。

## 长时与动态验证的补充

后续完整控制预检在 4.5 跑通：终点收到 15.217875 mL 并锁定成功，重置清零，
过量收到 19.089 mL 且不成功；试剂泼洒为 0，PhysX error stream 为空。
该版本仍有容器接触门禁失败，保留为控制诊断，不晋升交付。
逐步把测试路径改为先竖直平移离开滴嘴，再晃动、回正、移回，避免瓶口穿过固定滴嘴。
Points 与刚体姿态在 fetch_results 后显式同步；内腔检查升级为每个物理步，
Fine 同时检查数值封口内表面和实际出口。短时恢复到瓶内不能掩盖中间穿壁。

30 秒测试说明 10 秒的液位仍未平衡。提高一个 actor 的迭代数也可能改变其他液体的有效求解迭代：
[官方 PhysxCfg 说明](https://isaac-sim.github.io/IsaacLab/v2.0.2/source/api/lab/isaaclab.sim.html#isaaclab.sim.PhysxCfg.max_position_iteration_count)
解释了最高 actor 迭代数与场景上下限的关系。本任务据此固定场景位置迭代上下限，
再统一校准液位；不是将 64 次迭代提升为所有任务的默认。
生产者预平衡必须保留全部实测点与速度，并映射回源容器的初始坐标；随后重新冷启动验证。
消费者重置恢复初始点和初始速度，不强制冻结液体。

归档器要求完整双运行时、逐步内腔、守恒、终点、重置、过量和错位漏接负例全部通过，
并核对每个物理记录帧与渲染输入的哈希。运行场景 ZIP 保持完整依赖闭包；
较大的原始粒子帧另留在本任务输出目录，并在包内保存索引与逐文件哈希。
本任务的原始证据保留方式不改变核心包/schema/API 或其他历史包的策略。

第二轮 `make check`：1239 passed、1 skipped；Ruff、两套 smoke 与 diff 检查通过。

最终冷启动第一轮的逐步数据还发现：直接在瓶口合并粒子体系会让少量液滴短暂反弹到口上；
两版 2595 个采样均为 Receiver 的 above-mouth，Source/Fine 没有越界。
消费者将合并点改为真实穿口后的实际液体粒子邻域接触，保留当前位置和速度；
空中位于瓶颈内的液滴也不提前计量/显色。生产者预平衡资产不变，完整双版验收重跑。


## 最终物理资格（candidate_03）

生产者冻结快照为 `ConvertAsset/outputs/task10_pbd_20261009/snapshots/prebalanced_06`，
manifest SHA256 `68ab6c349ab5021b7c7f01cc05acbb7a317697d17550e07e17582a4e784ddb68`。
细管渐缩段使用保持原内轮廓的局部凸壁，原位解析出口封口，接收瓶增大粒子—刚体接触缓冲；
统一 64 次位置迭代后重调平衡液位。全部实际沉降点和速度保留，按刚体变换映射回原始容器位置。

消费者先要求真实穿口，再依据原液主体的自由液面邻域判断接触；排除孤立新滴递归延伸的液柱。
此修改不移动液滴或放宽内腔门槛。`bulk45_long_flow` 的 7 秒最大流量回归通过，收到 19.089 mL。

最终双版本报告位于 `outputs/task10_real_liquid_20261009/qualified/run41_03`、`run45_03`。
同一输入指纹、同一验证器，各 10,456 个物理步；Source、Receiver、DeadPrecharge 每步越界数均为 0，
PhysX error stream 均为空。正常终点、重置、过量、漏接、持续滴流、名义体积和各粒子集质量守恒全部通过。
最终候选为 `final_candidate_03`；旧 candidate_01/02 的不合格证据继续保留，未用于晋升交付。


## 渲染重建与共享目录

原样式交付目录为 `/mnt/data/chenjiantong/scene_usd/zzh_fixed/task_10_titration_experiment`，
对应用户路径 `/shared/smartbot_new/chenjiantong/scene_usd/zzh_fixed/task_10_titration_experiment`。
结构为 `scene.usd`（4.1）、`scene_isaac45.usda` 和 `SubUSDs/{materials,textures}`。
导出保持组合语义一致、无包外依赖；共享 4.1 入口已实际运行 smoke。

视频使用合格运行的粒子/刚体实测记录，回放渲染阶段以零力、零速度重建 SDK 等值面，
不改变原运行数据。显式开启 USD 回写，逐帧要求粒子坐标完全一致并检查表面包围范围。
空/非空切换刷新 SDK 对象和粒子系统关联；空中小液滴关闭网格过滤和网格平滑，
因为原过滤参数可能将稀疏小液滴表面完全抹除。容器内液体和所有运行时输入保持原字节。
上述渲染参数只用于可核对的实测状态回放，不替代动态物理资格。
原录制 30 Hz，成片按每两帧抽取一次输出 15 fps、1 倍速；未插帧或加速物理过程。

规范正文无需变更：求解器迭代、表面过滤和受控转移均只获得本任务范围证据，
不提升为通用液体默认。同步操作说明、案例索引与本记录；不改变核心包/schema/API。

最终仓库检查：`make check` 通过，1242 passed、1 skipped（555.01 秒）；Ruff、两套 smoke 和 diff 检查通过。


## 最终媒体与交付索引

成片为 `visual/final_movie_v2/task10_real_liquid_demo.mp4`：H.264、1920×1080、15 fps、
586 帧、39.066667 秒。全部帧绑定合格运行原始 NPZ 哈希，粒子逐值一致与等值面范围门禁全通过。
MP4 全片解码无错误；从编码成片抽取晃瓶、出液、13.74/14.38/15.03 mL 显色、
15.26 mL 终点锁定、重置和19.09 mL 过量帧，由实现者目视复核通过（非独立审查）。
透明度、原器材布置和 ON 均可辨认；同机位原场景对照保留在 `visual/source_baseline`。

完整包目录为 `handoff_v3/scientific_workbench_titration_task10_real_liquid_r1`，同级同名 ZIP；
`handoff_v3/delivery_receipt.json` 保存最终归档、视频、候选及原始记录 SHA256。
包内包含双运行时逐步报告、实际粒子记录哈希索引、视觉复核、成片、操作说明、生产者出处和运行脚本。
共享目录保持仅 USD/SubUSDs，异地复制闭包通过；细节见 `qualified/shared_relocation_final.json`。
全部相对输出路径均以 `outputs/task10_real_liquid_20261009/` 为根。
