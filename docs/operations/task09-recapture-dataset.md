# task09 新数采数据制作与恢复

2026-10-19 OSS补充交付已完成：标准目标下 `task_09_solid_weighing_300/`、`task_09_solid_weighing_500/` 共4008个对象全量MD5校验及SSH代表回读通过；本地READY保持原范围，OSS回执见[发布记录](../records/2026-10-19-task09-oss-publication.md)。

通用方法见[单任务制作与交付指南](genmanip-task-delivery.md)，新任务可复制[交付与验收清单](templates/genmanip-task-delivery-checklist.md)。本页保留具体任务的阶段记录；判断当前产物时，以最新交付入口及其验收范围为准。

2026-10-19：标准 v3 已安装交付并生成 READY。正式数据及回执位于 `/mnt/data/chenjiantong/scientific_experiments_data/releases/task09_standard_v3`；正式仓库分支为 `delivery/task09-standard-v3-final`（82cabca5）。两档reader、40独立初始化、四条回放链路及视频检查通过；四例分数为0.1/0.1/1/1，不代表全部任务成功。一次SDK启动超时重试记录保留。见[接收安装与验收记录](../records/2026-10-19-task09-receiver-installation.md)。下文旧日期内容为历史阶段快照。

2026-10-18 最新：500 条渲染已完成，300 档导出及验收 PASS。旧导出主机失联后，500 档从已提交的 354 条复制到独立候选目录，在四卡主机 `10.150.164.127` 的持久 tmux 会话续导。当前状态读取 `/cpfs/user/zhuzihou/dev/task09-current.json` 中的 `active_queue`（`export_recovery/STATE.json`），旧 multi/COORDINATOR 不再代表当前执行。续导后自动进行完整 500 档验收，接收目录安装仍待完成。见[导出恢复记录](../records/2026-10-18-task09-export-recovery.md)。

## 历史阶段记录（不作为当前运行指令）

2026-10-17 10:43 UTC后最新入口：原`/mnt/data/zhuzihou`制作目录出现跨主机ENOSPC，后续写入迁至`/cpfs/user/zhuzihou/dev/task09-storage-recovery-20261017/task09_recapture_600_20261012/standard_v3`。读取`/cpfs/user/zhuzihou/dev/task09-current.json`获取当前路径，或运行新根下`tools/multi_health.py`。原446条已验收数据保留原位，只读引用；旧CURRENT_STATUS无法写入，不再作为最新入口。

2026-10-17最新称量生产：四卡实例通过完整资格检查后，已与原两台合并为六卡队列，交接时保留291条已验收记录。当前使用`standard_v3/tools/multi_status.py`或`standard_v3/multi/COORDINATOR.json`；下文双机入口为此前阶段快照。完整导出及最终接收安装仍待完成，见[六卡运行记录](../records/2026-10-17-task09-six-gpu-render.md)。

2026-10-17当前称量生产：标准流程v3已切换为两台单卡并行，实时状态读取制作根下`standard_v3/dual/COORDINATOR.json`或运行`standard_v3/tools/status.py`。旧队列迁移时242条已验收结果全部保留；v3完整数据导出和接收目录安装仍待完成。见[双机渲染记录](../records/2026-10-17-task09-dual-host-render.md)。

2026-10-16标准流程重制已启动：用户选择补写完整制作LMDB转换器，再使用标准render.py及genmanip2lerobot.py生成新v3；允许有测试的标准脚本最小修复。三条输入共6894帧已通过标准parser逐轨迹往返检查，实际渲染/导出与批量状态见[标准流程v3记录](../records/2026-10-16-task09-standard-pipeline-v3.md)。下文“安装与PR暂停”是此前审计结果，尚未解除发布门槛，但不再阻止独立制作输入的修复和试制。

2026-10-16接收仓库安装门槛：用户要求按飞书流程先做兼容核验。远端CPU调用标准parser发现现有动作回放LMDB缺少逐帧物体/连杆/属性轨迹，不能直接作为记录状态渲染输入；安装及PR暂停。原始轨迹仍在，先补齐独立制作LMDB再做标准渲染/导出对照。详见[接收交付核验与修复方案](../records/2026-10-16-task09-receiver-delivery-audit.md)。这不撤销下述reader/单例回放资格，也不表示现有数据已被证明损坏。

2026-10-16修订已完成：600条的reader通过不代表符合300/500训练加10源留出的协议。600交付仅作制作归档，SUPERSEDED.json标记替代关系；新版入口为`handoff_train300_500_eval40_v2`，READY明确限定独立单case运行。
300/500两档远端reader、40例独立初始化、四组代表回放及归档校验已完成；回放分数为0.1/0.1/1.0/1.0，不宣称全部任务成功。连续切场清理问题未修复，按交付README逐case独立启动。
当前协议与证据见[训练划分修订记录](../records/2026-10-16-task09-training-split-v2.md)，以下2026-10-15的READY属于旧范围，不作为新版就绪依据。

2026-10-15收尾：600条渲染及导出已完成；旧队列最终失败来自向历史SSH地址运行reader超时，不应重启渲染。
当前评测入口为`root@10.150.163.175:22`。生产目录与独立交付目录的全部600条标准reader已通过，数据ZIP已核验CRC/SHA，READY已生成；见[本轮交付记录](../records/2026-10-15-task09-reader-delivery.md)。
当前以`evidence/delivery600_*`和`handoff_readout_range_v1/READY.json`为依据，不用下文历史生产描述判断现状。

制作根目录：`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/task09_recapture_600_20261012`。
本页只记录外部制作流程；项目不新增 episode runner、模型适配或 benchmark 核心层。
决定与证据边界见 [日期记录](../records/2026-10-12-task09-recapture-dataset.md)。

## 旧600条制作阶段的输入与产物（历史）

- `manifest.json`：三个输入文件的来源、哈希、交付范围。
- `source/`、`extracted/`：不可变归档及安全解压结果。
- `episode_plan.json`：600 个计划 episode 对应的源示范、seen 背景和指令。
- `numeric/`：与可见连杆位姿一致的训练状态；动作原样保留。
- `evidence/numeric_validation.json`：60 条逐条数值闭合结果。
- `pilot/queue.json`：完整三条试制队列状态；各运行目录保留视频、关键帧、日志和报告。
- `evidence/pilot_acceptance.json`：完整三条和十背景的已完成验收门槛，不等于600条已完成。
- `production/queue.json`：持续生产状态、当前 episode、PID、完成计数与每条视频哈希。
- `CURRENT_STATUS.json`：任务概要；生产计数以队列为准。

## 旧600条制作阶段的验证顺序（历史）

1. 执行制作侧 `tools/test_source.py` 与 `tools/source.py`，通过后才使用生成的数值。
2. `tools/render_states.py` 在 Isaac 4.5 中恢复状态，只渲染；保持 timeline 停止。禁止把 Replicator 默认 `step` 当作无物理渲染。
3. 先做完整三条和十个背景关键帧检查，观察取瓶、去皮、倒料、回秤、读数及相机视角。
4. `tools/export_dataset.py` 生成标准 v2.1 目录，核对 Parquet、视频帧数及完整解码。
5. 在远程既有 LeRobot 环境执行 `tools/check_reader.py`；用现有隔离 datasets 3.6 路径，不修改原环境。
6. 上述门槛通过后才批量生产；最后检查 600 条、1248020 帧和 2400 视频，不得静默排除失败项或重复补数。

## 旧600条制作阶段的恢复与交付边界（历史）

先读进程记录与队列状态，核对实际 PID、GPU 和输出，避免重复启动同一 GPU 任务。
成功产物必须同时有完整视频、报告和校验；单有目录、进度文件或部分 MP4 不算完成。
失败目录保留，新尝试使用新版本目录。只停止本次拥有的进程。

批量入口为制作侧 `tools/batch600.py`，实际工作根中运行 `python tools/batch600.py --resume` 可以恢复。
恢复前必须确认原 supervisor 和其记录的渲染进程已结束；不要在已有活跃队列上再运行。
队列会核对已完成视频哈希、保留失败尝试，完成600条后导出数据集并在远端标准 LeRobot 环境校验。
状态 `DATASET_VALIDATED_FINAL_HANDOFF_REVIEW_PENDING` 只表示批量数据验证完成，还需最终清单、哈希及交付范围复核。

原生评测与数据生产是两条独立进程链。`tools/watch_native23.py` 只等待第二条原生测试结束并保存动作一致性、日志、视频解码结果，不更改动作或成功条件。
查看其 `evidence/native23_validation.json` 时仍需确认 scope；原生失败不能当作源成功记录失败，源状态回放成功也不能当作原生任务成功。

最终五项交付中的辅助说明可列出制作记录；接收方读取 LeRobot 或运行任务不能依赖工作目录下的脚本。
原生物理结果单独记录，固定 120 Hz、4000 步；源采样时间未知时，逐记录动作执行只是该输入序列的测试，不是原时长复现。
任务包若仍未通过物理验证，必须保留待完成标记，不能随数据集读取通过而升级为任务成功。

## 2026-10-12最终称量规则版本

用户确认的`task09_readout_4_to_5_g_once_v1`取消最终连续稳定要求：有效空瓶去皮后，瓶受秤盘承托、五颗均在瓶内、显示净重在4.0–5.0g（含边界），同一步满足即可。
设备原USD的stable状态不作任务通过条件，原生计重波动仍属已知现象；不要把规则版本变更写成修复了物理稳定性。

交付候选位于制作根目录`handoff_readout_range_v1`。`offline/`仅包含task YAML、scene USD、task data三类相对覆盖路径；`metric/`为指定目录代码提交补丁；LeRobot完成后独立交付。
`readout_receiver_runtime`使用接收方原始机器人资产，排除测试用robot_usds覆盖层。实验性的`native_geometry_support_runtime`不交付。
规则迁移、补丁检查及安装身份分别在`evidence/readout_contract_migration.json`、`readout_metric_patch_check.json`和`readout_receiver_identity.json`。
先核对`evidence/readout_contract_pair.json`中的成功/漏颗对照，再核对`evidence/readout_clean_receiver_run.json`和对应原生audit；不能用候选成功替代独立安装成功。
详情见[规则版本记录](../records/2026-10-12-task09-readout-range-acceptance.md)。

最终接收方原生成功证据为`evidence/readout_receiver_validation.json`：1.0分、3191步、接受时4.01g，原始机器人资产；视频末端读数字形有清晰度限制，不能用它代替字段快照。物化后的1143个文件校验见`readout_materialized_install.json`，当前输入为60条新数采及41条历史案例，共101份metadata、111份YAML。

`evidence/readout_clean_negative_validation.json`记录最终安装中的失败对照：0.1分、4000步、仅初始放瓶计分，与原型环境0.3分的`readout_range_source105_validation.json`区分。它不是隔离最终称量条件的反例；读数边界另由规则测试覆盖。原生重执行失败不改变源成功示范及600条渲染计划。任务内容总结见`readout_task_acceptance.json`。

前四类运行内容的独立压缩包为`delivery_archives/task09_readout_range_v1_runtime_payload.zip`，CRC和SHA报告在`evidence/readout_runtime_archive.json`。它不含LeRobot数据，不能替代完整五项交付。

收尾时同时核对`handoff_readout_range_v1/MANIFEST.json`的任务内容验收和数据集状态。`tools/finalize_readout_dataset_handoff.py`只在两者通过后物化最终数据、核对600/1248020/2400和标准reader结果，再生成`READY.json`。进程记录在`evidence/final_handoff_supervisor_process.json`；已有后台进程时不要重复启动。

2026-10-15的最终收尾另增加“最终目录在远端读取”和数据归档检查，故不直接运行上述旧watcher提前生成READY。
远端沿用`/root/miniconda3/envs/lerobot/bin/python`，进程级`PYTHONPATH`指向制作根的兄弟目录`lerobot_reader_deps`；实际datasets必须读回为3.6.0。
`tools/check_portable_reader600.py`只依赖指定数据目录和安装库，不依赖制作numeric；报告保存在交付evidence中。
接收方普通读取使用交付说明中的标准LeRobotDataset示例，不需要任何制作/验收脚本。

## 2026-10-17 双机渲染调度（历史）

新入口 `root@10.150.164.67:22` 实查只有一张GPU，用户选择与原 `10.150.163.175` 组成两台单卡生产。两机共享原数据与代码，不重装环境；新机reader沿用随交付准备的datasets3.6.0隔离依赖。

制作根下`standard_v3/tools/status.py`优先读取`dual/COORDINATOR.json`，列出各主机当前任务、日志与完成计数。不要并行启动旧batch.py和新协调器，也不要手工把同一个分组派给两台机器。跨机占用使用原子创建的`dual/COORDINATOR.owner`，原队列检查该占用并拒绝竞争启动；CPFS上的flock实测只在本机互斥。恢复时`dual_coordinator.py --resume`会先核对远端进程身份，存活或SSH不可达时拒绝重复派发。失败尝试保留，每次重试用新目录。

500条完成后协调器自动交回原batch.py导出、验收300/500两档。`DATASETS_VALIDATED_INSTALLATION_PENDING`仍不代表接收方安装完成。新机资格、迁移及运行记录见[双机渲染记录](../records/2026-10-17-task09-dual-host-render.md)。

若失败已发生在导出阶段，按原batch.py的导出日志和产物完整性恢复；不要重新启动渲染协调器来覆盖部分导出目录。双机协调器只在所有渲染结果通过后交接一次导出，接收方最终安装仍需独立验证。

## 2026-10-17 六卡队列恢复（历史）

`multi_coordinator.py --resume`沿用既有全局原子占用目录；恢复前核对所属主机上的旧worker/SDK进程，仍存活则拒绝重复派发。原`dual/COORDINATOR.json`已标记迁移，新状态以`multi/COORDINATOR.json`为准，不启动旧双机协调器。

任务只按已验收收据计数。成功或失败进程退出后，均给共享盘终态文件最多180秒可见时间。只有SDK未完成启动且日志300秒无更新的失败允许一次同组新目录重试，并先确认旧进程完全退出；数值/渲染/日志错误不重试冒充成功。失败lane停止接单，健康lane继续处理其他组；若有未通过的组，最终导出仍被阻止。

GLInterop修复只在私有Vulkan启动器中禁用OpenGL GPU枚举，不过滤日志或改全局图形环境。原始失败尝试和GPU1启动停滞重试均保留在六卡记录中。六卡结束后仍统一调用原标准导出器，不并发重复导出相同数据集目录。

2026-10-17 08:42 UTC发现中断后，当前队列由`tmux -L web-terminal`中的`task09-six-gpu`会话托管。首选`standard_v3/tools/multi_health.py`查看状态，它验证协调器实际进程身份和心跳；仅有COORDINATOR.json中的RENDERING不能证明仍在运行。恢复收据与原因边界见六卡记录的08:42 UTC小节。

09:48 UTC后，tmux任务由`tools/supervise_multi.sh`监督；`multi/supervisor-events.log`保留协调器退出码，最多三个启动尝试，普通数据错误不自动恢复。显式停止任务时应先停止继续派发及监督重启，再按记录的身份停止该任务进程；只杀协调器可能触发恢复。未确认退出原因前，ETA必须标明连续运行假设，不能把旧JSON状态当作存活证明。
