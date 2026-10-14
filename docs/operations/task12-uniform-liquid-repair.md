# task12 均匀变色真液体：验证与恢复

## 2026-10-14 当前入口

新远端`root@10.150.163.77:22`已恢复授权，公网919为备用；不改称量主机别名或内部8087。
六次坏例及19组旧满分筛查均已正常结束。19组为17×.15、2×.3，正式交付仍被回归门槛阻塞。
当前执行三组旧/新计时对照，队列位于`clock_diagnostics_20261014T023450Z/queue.json`。
旧mixed5部分实测已有同一物理步两次累计、有效倍率2的证据，完整结论/新版对照尚待完成。
用户允许统一校准反应时长并必要时低于30秒；其余原文加热条件保持。不得擅自以低分逐案例调时长。
详见[计时与抓取回归记录](../records/2026-10-14-task12-clock-and-grasp-regression.md)。

## 新增正式交付门槛：旧满分回归

用户要求全量验证21份旧满分记录对应的19组动作。旧画面真成功、初态/时序对齐而新版失败的未解回归阻塞交付。
即使下面坏例队列全部完成，也不能直接发布；必须满足`evidence/historical_success_release_gate.json`。
新增队列`historical_success/queue.json`等待现有水浴队列结束后顺序筛查18组，mixed5两次当前结果复用。
不停止称量、不改接收方文件，不把低分直接解释为旧metric误判。详情见[旧满分回归记录](../records/2026-10-13-task12-historical-success-regression.md)。

## 2026-10-13 当前执行状态（优先于下方历史流水）

旧128MiB mixed5曾约3060步GPU求解失败，本轮同字节复查完整7000步/.15且无引擎错；
旧失败保留，不能因一次完成认定修复。按用户新指示优先复用标准SDF烧杯及已有粗粒子配方，
去掉257块额外浴液边界，浴液96649→2320粒、样液13905不变。
当前2320候选已通过三冷态/一升降；闭合渲染包络350.11mL，目标349.095mL，水面高约7.4mm已记录。
用户已明确接受约7mm的水面差异，保持当前PBD。恢复触水规则原1.2mm补偿后，最终四项归档
独立安装到`receiver_archive_install_20261013T031857Z`；真实控制器回归和静态闭包通过。
旧粗粒子v1完整mixed5已通过运行检查，但不替代最终v2。完整normal/tilt/offcenter/wall已通过，43.7秒变色/重置视频已人工抽查与全解码；
测试夹具在录制前刷新原玻璃材质，不能据此替代原版运动显示验证。
首条最终版mixed5已完整7000步/.15，无引擎error；四视频全解码，四路各20帧审查未见移动玻璃悬空，
保留飞溅/横倒/遮挡WARN。原版运行未加材质刷新。`coarse_final_v2_resume_queue.json`当前执行第二次mixed5
及另四例；首条结果`recheck_coarse2320_v2_a_mixed_5.json`，审查`coarse_v2_first_visual_review.json`。
旧`coarse_final_v2_queue.json`是夹具失败的历史记录，不要重启或覆盖。尚未发布。
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
称量600条在另一台机器上运行，勿停止或重复启动其producer。水浴当前使用10.150.163.77:22的单4090（公网备用919）；旧10.150.162.223为历史入口。
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

## 2026-10-14 回归诊断恢复顺序

**最新决定覆盖下列旧自动串行顺序：先通过建通原版成功复现，才继续新版物理调参。**
当前聚焦回架的入口为`pristine_rack_observer_h00_b_run.json`、`rack_prefix_diagnostic_queue.json`
与`rack_segment_diagnostic_queue.json`（均在evidence下）。先核对观察器完整中立性，再执行
有证据的底座分段模式对照；这些推断不是原请求实录。详见[旧版回架记录](../records/2026-10-14-task12-old-rack-reproduction.md)。
prefix_mode_h00_a已首次1分，后续读`old_success_verification_queue.json`和`complete_mode_mapping_queue.json`。
初始270帧状态精确对齐但后续仍有差异，不能用一次1分直接解锁原版校准；需独立重复、live插架位姿与剩余语义核验。
这两个旧队列随后因验收脚本直接比较不同成功长度而停止；现已重新核验两次成功及live位姿通过。
最新入口是`old_success_verification_reaudit.json`、`old_prefix_success_visual_acceptance.json`和
`complete_mode_mapping_resume_queue.json`，不要把旧队列的STOPPED当作新的任务失败。
完整模式mixed5现已两次5902步成功，已执行5903观察帧与原机器人记录完全一致并完成同帧目视核对。
当前执行入口转为`remaining_original_representatives_queue.json`，原版gate仍等待另外两条代表；
证据见`mixed5_complete_mapping_acceptance.json`及`pi05_original_transport_evidence.json`。
先读`evidence/original_success_gate.json`和`evidence/pristine_original_h00_a_run.json`。
后续时间/接触队列已停止，禁止直接重启绕过前置；旧phase1发布器已停用。
最终标准为同一修复版19组各两次成功，不能沿用“缺成功示范待重采”的旧水浴交付口径。
来源、当前差异和辅助门禁见[原版校准记录](../records/2026-10-14-task12-original-baseline-calibration.md)。

当前状态以R/CURRENT_STATUS.json与下列队列为准，前文早期队列只作历史排障依据：

1. `clock_diagnostics_20261014T023450Z/queue.json`：三个旧/新计时配对。
2. 同目录`original_config_control_queue.json`：当前可获取旧配置控制；不冒充历史精确快照。
3. `evidence/original_rigid_offsets_bounded_queue.json`：刚体偏移诊断的限定冷态/升降测试。
4. `evidence/timing_v2_trial_queue.json`：证据门禁后作者统一0.5时间版本，三条原动作隔离回放。
5. `evidence/contact_logic_fixture_queue.json`：另一个只改接触判断的诊断overlay，正常/碰壁/倾斜/偏心夹具。

上述队列串行使用单GPU，任一前置失败不得绕过门禁继续启动后续。接触候选没有合入时间候选或正式交付；
不能把不同候选的局部通过拼成一个版本的完整资格。暂定0.1mm接触容差仍需距离边界和休眠验证。
旧计数与被动事件部分不一致，未对齐步不得据此消除碰壁限制。最终仍需相同版本原动作完整成功及回归。
详细测量、未解决问题和证据索引见[当日记录](../records/2026-10-14-task12-clock-and-grasp-regression.md)。
