# task12 均匀变色真液体：验证与恢复

## 2026-10-13 当前执行状态（优先于下方历史流水）

旧128MiB mixed5曾约3060步GPU求解失败，本轮同字节复查完整7000步/.15且无引擎错；
旧失败保留，不能因一次完成认定修复。按用户新指示优先复用标准SDF烧杯及已有粗粒子配方，
去掉257块额外浴液边界，浴液96649→2320粒、样液13905不变。
当前2320候选已通过三冷态/一升降；闭合渲染包络350.11mL，目标349.095mL，水面高约7.4mm已记录。
用户已明确接受约7mm的水面差异，保持当前PBD。恢复触水规则原1.2mm补偿后，最终四项归档
独立安装到`receiver_archive_install_20261013T031857Z`；真实控制器回归和静态闭包通过。
旧粗粒子v1完整mixed5已通过运行检查，但不替代最终v2。当前先处理无机器人夹具的玻璃画面不同步：
物理插入、液体保留和反应数值通过，玻璃仍显示在上方，视频不合格。诊断仅在辅助脚本，接收方文件未改。
状态见`CURRENT_STATUS.json`与`render_sync_diagnostic_process.json`；`coarse_final_v2_queue.json`
是首夹具失败的停止记录，不要直接重启旧的预放入水中夹具。后续短画面对齐通过，再完成安装版
反应/重置/守卫、两次mixed5及另四例；尚未发布。
称量600条LeRobot继续生产；暂缓的仅是水浴训练集。
四项文件存在不代表完整运行合格，接收方仍只能依赖YAML、USD、task data及metric。
详细收尾和故障记录见[本轮记录](../records/2026-10-13-task12-runtime-closeout.md)。

工作根R：`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/task12_liquid_color_20261012`。
决定及资格边界见[日期记录](../records/2026-10-12-task12-uniform-liquid-repair.md)。本页不为Scenario Forge添加runner或SDK核心层。

## 恢复入口

当前最新队列是`stack128_native_cases.json`/`run_stack128_qualification.py`。旧`remaining_native_cases.json`在unseen_background3约2430步因64MiB碰撞栈不足停下，接触已被丢弃，不得放行或重跑旧配置。
新51个YAML/102块只增加GpuCollisionStackSize=134217728，已重新归档并独立安装；原版loader实际设置新值的日志必须进入每例验收。五例全部在新版本重验，报告`native_stack128_<case>.json`；首条人工审查marker为`first_stack128_visual_review.json`。旧视频/守卫仅以相同USD范围复用，不能充当新容量运行证据。
新容量首条background3已完整通过当前回放运行验收、0.15分失败，人工审查放行，正在继续mixed5。通用视频audit可选runtime JSON缺失时clock字段为False；task12实际频率由内嵌native回调摘要和逐异常dt触发日志独立验收，不把缺失文件当测得错误频率，也不跳过实际时钟检查。

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

首例已完成7000步、0.15分，完整日志无引擎错误、四视频全解码及受保护源码检查通过；真实失败是加热不足且末帧试管斜躺在架上，不能当成功示范。`first_rack_native_visual_review.json`只放行坏例运行范围，总体视觉WARN。
后续由`run_qualified_continuation.py`串行执行已安装版本的normal/tilt/offcenter/wall夹具与badcase4/5/6/7；状态在`qualified_continuation.json`。任何失败停止，无自动READY或发布。最终仍需人工检查新视频与其余坏例画面。

该协调器实际停在旧wall夹具未维持接触：接触数0，不能当wall guard失败或通过。原normal视频及tilt/offcenter通过。修订wall夹具只在测试内夹住dynamic烧杯并实测16–17接触点、保持一秒不加热；交付文件哈希复核一致，未包含夹具。完整资格汇总读`guard_qualifications.json`。
最新剩余四例队列已切换`run_remaining_native_cases.py`，状态读`remaining_native_cases.json`；旧协调器的STOPPED状态为历史失败证据，不能覆盖当前运行状态。新native验收日志/四视频仍逐项检查，所有人工审查完成后才运行受门禁保护的`finalize_phase1_release.py`，只生成本人目录的phase1发布头。
最终无机器人原视频见`final_normal_video_audit.json`，已亲看蓝色→整体橙砖红→重置蓝色且全解码。120帧刷新不增加native步；一个待处理native事件的8.33ms读回已注明，不把render-only当新物理时间。原装饰OFF字样保留，不用它判断实际任务加热状态。

真实反应视频的重置画面曾误报PASS，人工检查已撤销。最新演示工具增加暂停物理后的120帧渲染刷新和样液区域颜色占比检查；必须在最终接收方版本重新录制，确认刷新期间物理步不增加。数值重置通过不等于摄像头第一帧恢复。

## 安装兼容与交付

metric共享repair_checks与已交滴定、称量相同。未安装共享文件的接收环境使用task12_metrics_standalone.patch；已有且哈希一致时使用task12_metrics_existing_shared.patch，只修改task12 metric。哈希不一致时先处理版本差异，不盲覆盖。
两种补丁及只读检查在R/evidence，正式交付时复制到独立发布目录。
最终包须含20场景入口、离线相对路径、补丁、安装说明、哈希及实际证据；无GenManip核心、SDK、机器人或生产脚本安装需求。
缺成功机器人示范/LeRobot如实标为待重采；引擎错误不可作为正常坏例放行。
