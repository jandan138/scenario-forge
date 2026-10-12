# task12 均匀变色真液体：验证与恢复

工作根R：`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/task12_liquid_color_20261012`。
决定及资格边界见[日期记录](../records/2026-10-12-task12-uniform-liquid-repair.md)。本页不为Scenario Forge添加runner或SDK核心层。

## 恢复入口

先读R/CURRENT_STATUS.json、evidence/first_native.json及对应baseline_runs/receipt.json，再检查远程GPU与8087占用。
称量600条在另一台机器上运行，勿停止或重复启动其producer。水浴只使用10.150.162.223的单4090。
独立运行工具在R/tools；接收方只依赖允许的YAML、USD、task data与scientific metric。

## 验证与停止

- 当前首例mixed5按完整7000步验证；其原始动作来自bad_case_matrix中第8项，不混用teleop或其他策略轨迹。
- tools/run_first_native.py记录自己的helper、server/client与run ID，首个物理/加热运行时错误即停止；只清理本次进程，禁止全局pkill或ray stop。
- 原生结果、启动及worker日志、周期120Hz时钟、状态、四视频都要核对。已有静态结构及八项规则检查不能替代完整运行。
- 首例通过后才运行其余四个task12坏例；银镜的失败和局部资格不自动归给水浴。
- 规定无机器人演示需要明确夹持约束，只能支持相应液体/规则范围；完整反应演示不改变正式评测7000步上限。

首个mixed5原生尝试已在6495条有效观察后出现CUDA错误。`first_native_failure_audit.json`为实际失败证据；流式客户端视频可以用于故障前画面，不能替代不存在的完整服务器结果。
重置材质修正和浴液投影修正已写入20个场景入口；原静态报告的旧wrapper哈希须在最终验收前刷新。
当前真实反应视频见`normal_visible_process.json`；`shadow_diagnosis_process.json`等是强制颜色/暂停物理的诊断，不能当作反应视频。

默认凸分解候选因内腔偏差未通过，shrinkWrap候选初始化触发GPU错误，两者均不得安装或继续原队列。
当前生产者候选只关闭18片冗余架底支撑，保留完整原架三角网格。`tools/run_rack_qualification.py`串行执行两次冷态及两次升降，由`run_sdk_owned.py`在首错/超时清理本次进程组。冷态额外检查原网格实际接触和末秒落座稳定，液体仍逐原生步检查粒数和1mm内腔门槛。
只有`rack_qualification.json`为`PASS_BOUNDED_ASSET_GATES_NATIVE_REPLAY_REQUIRED`时，才能运行`prepare_rack_receiver.py`创建`receiver_rack_support_runtime`，之后用`run_rack_native.py`完整回放mixed5。原失败目录不覆盖。
四项夹具及正式插孔位姿检查已通过。无仪表冷态同样通过、保留既有faceIndex警告；最初零警告预期的协调器停止记录不删除，分类审查见`rack_warning_control.json`。最新完整回放状态读`native_rack_support_run.json`，不要把历史`rack_native_coordinator.json`的停止状态当作当前GPU已停止。

`build_candidate_install.py`制作候选而不发布：仅三棵离线树和两个metric补丁，YAML目录中的原索引JSON不交付，排除lock.mdb和mesh_data缓存。701个离线成员逐项哈希核验后，向原始base创建新worktree并从归档安装。安装哈希通过仍不等于运行通过，来源和目标在`rack_candidate_install_identity.json`。
生产者Git hook依赖已有cpu_tools工具在命令PATH；本次缺失PATH已修复并实际通过Black，没有跳过hook，也不给接收方新增该工具依赖。

真实反应视频的重置画面曾误报PASS，人工检查已撤销。最新演示工具增加暂停物理后的120帧渲染刷新和样液区域颜色占比检查；必须在最终接收方版本重新录制，确认刷新期间物理步不增加。数值重置通过不等于摄像头第一帧恢复。

## 安装兼容与交付

metric共享repair_checks与已交滴定、称量相同。未安装共享文件的接收环境使用task12_metrics_standalone.patch；已有且哈希一致时使用task12_metrics_existing_shared.patch，只修改task12 metric。哈希不一致时先处理版本差异，不盲覆盖。
两种补丁及只读检查在R/evidence，正式交付时复制到独立发布目录。
最终包须含20场景入口、离线相对路径、补丁、安装说明、哈希及实际证据；无GenManip核心、SDK、机器人或生产脚本安装需求。
缺成功机器人示范/LeRobot如实标为待重采；引擎错误不可作为正常坏例放行。
