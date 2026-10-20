# task12 均匀变色真液体：验证与恢复

> 当前验收已由用户调整：固定19组×两次的新旧对照，新版成功数最多少7/38，不设绝对成功率底线；物理、显色、保液与独立安装验收仍独立保留。旧的38/38、单例新增失败必阻塞要求不再作为活动门槛。见[相对验收记录](../records/2026-10-19-task12-relative-acceptance.md)。下文此前状态保留为历史，不代表进程当前仍运行。

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

**最新进度：旧版三个代表已校准通过。** 先读`original_success_gate.json`，再看当前实际运行的
`calibrated_new_timing_pair_queue.json`（evidence下），它使用已校准的执行方式对比冻结新液体包与时间候选。
完整复核见[校准后新版验证记录](../records/2026-10-15-task12-calibrated-new-liquid-validation.md)。
下列旧版排障队列保留作历史依据，不应重新启动旧的统一absolute/单步回放。

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


2026-10-15后续：同机时间B/C及位姿诊断均0.85，回架未通过；快速移动与样液0.2m/s速度上限不匹配。当前旧版位姿对照和3m/s单参数候选队列见[速度与回架诊断记录](../records/2026-10-15-task12-sample-speed-and-return-diagnosis.md)。该候选尚未合格，禁止以其替换已声明的正式资格。

2026-10-15 用户明确调整加热规则：后续候选取消“碰壁停表”，保留入水、有效液体、烧杯/加热器姿态与承托判定；离水暂停、原生物理时间累计和重置保持。碰壁计数仅作遥测。此前碰壁应阻断加热的夹具属于旧规则，不作为新规则的验收期望；原始记录保留。此变更是任务规则调整，不是漏液或回架修复。见[规则变更记录](../records/2026-10-15-task12-wall-heating-policy.md)。

2026-10-15执行基线更新：按用户确认，样液体积以清晰液柱和完整变色为准；独立验收采用全过程≥95%保留、无穿壁/持续失液，metric不新增扣分。先通过静置与原动作速度压力测试，再跑完整机器人；旧零损失报告保留。详细边界和队列见[保液优先记录](../records/2026-10-15-task12-retention95-replan.md)。

桌面2mm与运动压力测试进展见[执行记录](../records/2026-10-15-task12-table2mm-and-motion.md)：两次静置已数值通过；3722帧旧位姿压力测试已启动，四个桌面单变量/组合资产仅静态审计通过。桌面2mm尚非交付设置。

运动压力测试首轮保留率超过95%，但管口分类存在未确定事件。重测使用独立检查器v2，旧FAIL不覆盖；原因和回归测试见[管口分类修正](../records/2026-10-15-task12-mouth-exit-checker-v2.md)。不得把计数用的1mm容差当作实际管口高度，也不得忽略粒子重入后的再次侧壁退出。

接入新液体初态时，必须同时检查USD points/canonical和task data的`initial_particle_states`，不能只检查`initial_prim_attributes`。原版loader会恢复粒子点并清零速度；按每份初始容器布局映射后，验证其余metadata与原动作不变。当前独立候选仅静态通过，见[候选与初态审计更正](../records/2026-10-15-task12-retention95-receiver-candidate.md)。

kinematic位姿压力夹具要分别核对live物理位姿与显示网格；不能假定tensor targets自动更新USD显示变换。当前仅在外部诊断session用无物理API的显示副本跟随live位姿，原碰撞体不动，见[压力视频显示同步](../records/2026-10-15-task12-pressure-video-display-sync.md)。该记录也包含管口外回落的独立几何复核；旧FAIL报告不覆盖。

完整原生h13_b为0.85分且实际回架翻倒；当前转入只读USD观察器的前300步抓持诊断，生产7000步和metric保持。短测不能当完整成功/坏例，详见[完整失败与短诊断记录](../records/2026-10-16-task12-native-return-failure-and-observer.md)。19条来源有重名case，验收按来源哈希计数，不按case名去重。

短诊断已定位到拿起阶段的夹持相对位姿差异；恢复旧试管碰撞组合仅改善初始摆放，尚未恢复抓持。下一组只恢复evaluation位置迭代范围1/255，保留全局CCD与液体设置；结果按上述记录追加，勿将短测0.15当完整任务结果。

2026-10-16后续：旧试管碰撞+位置迭代1/255组合的短测抓持偏差降至3.59mm，但完整诊断出现持续失液，变色完成时仅保留74.66%；松爪后实时槽底间隙约29mm，尚未落座。不能将短测改善提升为交付资格。当前完整运行继续保留终态，下一轮只读观察器将采实际粒子offset、运行时重力/单位/材质及样液点速度快照；运行标签与实际observer版本以身份文件区分，见[诊断记录](../records/2026-10-16-task12-native-return-failure-and-observer.md)。

近期单变量与完整回放的状态快照见[12组原生诊断记录](../records/2026-10-16-task12-native-diagnostic-ledger.json)。必须区分计划短测、完整7000步、保液门槛提前结束；短测过程分0.15不代表完成任务失败，短测保液95%也不构成完整交付资格。候选是否仍运行以个人repair目录CURRENT_STATUS及实际进程/运行记录为准，提交的ledger仅是生成时快照。

4mL候选的阶段边界与未完成事项见[阶段记录](../records/2026-10-16-task12-volume4-candidate.md)。短测98.37%只覆盖1200步；正式任务、重复性、19条来源与独立安装仍未合格，不能提前交付。

最新阶段：恢复旧管架及烧杯自动接触间距后，短测抓持改善，但完整范围仍在直立提离烧杯阶段触发保液不足95%的停止条件；不是已完成回架。下一组仅试样液表面张力，见上述诊断记录。切勿将短测97.83%或旧版本显色片段视作当前候选完整通过；仍需流动检查、完整任务和重复验收。

4mL诊断版本还有交付前必修项：旧sample_height_m仍被触水判定读取，不能只更新sample_volume_ml标签及粒子初态。应同步名义液柱几何与体积，并独立验证触水/计时/重置；当前表面张力运行保持原字节以保留单变量对照。发现与边界检查见2026-10-16原生诊断记录。

表面张力0.0074单次短测只比0张力多保留2颗粒子，抓持偏差反增，暂不采用。后续完整范围诊断采用0张力原候选并单独修正4mL名义高度；observerv8只增加只读height/volume，不改变metric。依据与数值见原生诊断记录。

高度修正版完整范围回放也未合格：显色逻辑完成，回架终态偏高约31mm且倾角约15度，保液在observer5007降到95%以下并提前结束，无完整原生分数。当前只读v9短诊断用于比较连续位置差分与USD速度，不继续盲目提高速度上限；配置/进程以CURRENT_STATUS和实际句柄为准。详见2026-10-16原生诊断记录及sample_height_full_abort_review.json。

v9已完成并精确对齐：动作前局部粒子位移率约0.013m/s，首动作即明显上升，后续保持段约0.223m/s；已记录的USD物理属性400/500一致。当前转入300步v10只读启动边界检查，不改物理或评分；首动作相关性不构成根因证明。报告sample_motion_start_boundary.json，详见原生诊断记录。

v10边界前后实际getter未发现碰撞/质量/粒子offset切换，首动作突变再次复现。下一项是300步场景位置迭代下限1→128的单变量对照，保持120Hz、粒子数和原动作；这是检验敏感性，不是已定位内部求解器根因或采用新默认值。相关报告与范围见2026-10-16原生诊断记录。

位置迭代下限128对照未采用：只使较大的粒子相对运动提前到动作前出现。已转入原min1配置下MaxPosition255→16的300步单变量对照，仍保持120Hz；观察液体改善时同时验机器人抓持，不降低最终回架、全程保液及重复验收标准。

MaxPosition16短测有明确变化：首动作相对运动突变未出现，正式300步保液100%，但抓持相对旧成功的偏差增至18.07mm。当前仅作为完整7000步cap候选，须检查显色/提管/回架；不将短测100%或solver参数敏感性当作交付资格或通用默认。三组证据见position_iteration_three_way_comparison.json及原生诊断记录。

最新完整MaxPosition16回放已得1分并自然结束、全程保液99.67%，但逐粒审计发现两次侧壁退出，因此仍不交付、资格计数不增加。下一单变量保持低迭代，只将样液碰撞纠正速度上限1→2m/s检验侧壁问题；保留原动作和7000cap。视觉显色可见，但热板OFF标签待修。详见2026-10-16原生诊断记录，勿只引用1分掩盖物理失败。

当前简明交接见[首次满分但仍有侧壁缺口](../records/2026-10-16-task12-first-native-success-with-side-exit-gaps.md)，包含实际视频、交付边界和下一单变量；不要将该诊断成功包直接发送为合格交付。

纠正速度2的完整范围诊断未采用：烧杯偏移导致未加热，后续横倒且保液不足；已停止，不是完整评分结果。下一300步对照保留原场景上限255，只将两套PBD自身迭代16→128，仍不增加粒子数。另有ON文字纯视觉overlay已静态通过、未渲染/未应用；不要把它当作已交付状态。具体证据见原生诊断记录。

两套液体迭代128短测未改善持续运动，暂不采用。当前转入场景位置迭代上限32的单变量300步对照（液体仍16、纠正速度仍1）；结果以实际运行记录为准，不把单次短段保持率当作交付。

上限32短测正式300步保液100%、抓持差1.94mm，已进入同物理完整范围验证准备；这仍是单次短段结果，不替代完整无穿壁、显色与回架验收。ON文字overlay仍独立保留，尚未进入运行包。

后续上限32完整诊断已经自然满分，正式episode样液/浴水保留均100%、无退出；初始化与视觉仍单独待审。已构建20场景/41初始化/51配置的RC1并通过静态闭包，ON文字已集成、私有观察器已删除。进入三来源各两次和独立安装验证，尚不可交付。GPU正在执行称量队列，水浴等待器只在整队结束后启动，不得将等待状态写成运行状态。身份、矩阵、资源状态及构建踩坑见[RC1记录](../records/2026-10-16-task12-maxpos32-receiver-rc1.md)；以身份文件定位候选，不按目录时间猜测。

后续干净RC1已完整跑完：0.85分，试管斜靠管架，尚不可交付。当前暂停代表/全量资格队列，执行120Hz的“原诊断/RC1×有无观察器”配对，每组累计两次，新增六次。只读观察器仍可能通过数据视图/订阅影响运行，需实测，不凭无setter推断。具体分组、独立副本验证、真实状态和审计范围见[配对复现记录](../records/2026-10-16-task12-observer-package-pairs.md)。运行链路通过与任务成功分开；没有runtime时钟文件的审计false标记不能自动归因为频率错误。

配对后续：八条结果仍未建立干净候选成功；RC1带观察器也出现一成一败。v10含每步显式`update_transformations(False,True,True)`，应更正“纯只读”称呼；下一轮隔离该同步与抓持偏差。本机初始化失败后不再继续补环境，迁到`10.150.164.67:22`，新机客户端已对齐0.2.0；旧机称量保持独立运行。先做旧包基线，再执行四组各两次300步短诊断；不得使用本机私有依赖或将跨主机结果混作重复资格。身份、环境恢复和状态入口见[新机诊断记录](../records/2026-10-16-task12-newhost16467-diagnostics.md)。

2026-10-17：新机基线1分且机器人状态误差0，八次短测已结束；同组波动和组间范围重叠，未定位同步为充分修复。四次完整120Hz干净/仅同步对照已静态准备。新机现被称量双机队列占用，等待其整批渲染结束再接续，不抢任务间隙。此前候选的一成一败已用live位姿重算回架几何，失败有真实高位停滞/倾倒，不能只归因于评分读取。详见[完整同步对照与资源记录](../records/2026-10-17-task12-full-sync-comparison.md)，实际启动以资源队列记录为准。

2026-10-18：等待器已退出且称量迁移后原状态源失效，四次水浴均未曾启动。用户改为新机优先水浴，现以直接队列启动四次对照并持有称量新机渲染锁，称量另备排除new的恢复入口；称量本轮未自动重启。不得再依据旧WAITING或历史active字段报告进度。详见[新机预留恢复记录](../records/2026-10-18-task12-reserved-host-recovery.md)，以新队列心跳、实际进程和run记录为准。

上述四次已结束并完成关键帧复核：干净版0.85/1，只有同步0.3/1；前者失败为显色后回架倾倒，后者失败为蓝色未完成变化但回架。干净版成功不依赖同步，但稳定性与逐粒保液仍未合格。查看[完整同步对照复核](../records/2026-10-18-task12-fullsync-visual-review.md)，不要把待复核状态或下一步建议误报为后台持续工作。

日志补充更正：仅同步a的周期快照已有`bath_off_center`和6.366667秒停表证据，先前“缺少加热原因”的描述遗漏了已有日志。用户选择按实际杯底承托判断加热，并比较干净120/180Hz。两版20入口/41初始化已静态通过，12项边界/时间测试通过，旧包180Hz正在校准；不得把它写成升频已解决回架。详见[承托与频率比较记录](../records/2026-10-18-task12-support-and-rate-comparison.md)，包含派生动作、metric计时和门禁范围。

后续：旧包180Hz校准最终0.85分，回架失败，视觉门禁明确拒绝；原频率比较队列已停止，180Hz新液体未运行。独立120Hz承托修复a/b队列已接续，利用此前有效120Hz基线推进加热规则修复，不视为180Hz校准通过。运行及自动准备的画面、周期状态均按上述记录中的新队列检查。

本阶段收尾：120Hz a/b均0.85分、显色完成但未落座，关键帧已由实现者复核；15mm偏移的受控旧/新判据对照通过，证明杯底仍被承托时旧规则停表、新规则继续加热。短测0.15不计为完整任务结果。当前无后台仿真，不能交付。详细证据、历史上端转动分析及约1GB失败重复资产的备份清理见承托/频率记录；下一步需围绕夹持角度和接触数据定位回架，不将默认抗扭参数或更多升频直接当答案。


2026-10-18夹持接触诊断收尾：当前候选已观察到离架后、触杯前相对夹爪转2.712度／管底偏移6.120mm。当前玻璃碰撞网格及列出的质量属性与旧包一致，已检查的管身接触点在纠正一物理步报告时差后贴合表面；尚无足够依据修改碰撞几何。三次300步过程及视频审计结束，只有diag_v2_b具备完整有效接触trace；短测不替代回架资格。共享ENOSPC曾造成错误的旧RUNNING状态及trace缺失，已更正并将输出归档验证，当前无后台仿真。下一项为核对有效材料/迭代后规划32→64上限单变量，而非直接加摩擦（当前机器人配置已2.5/max）；未执行新参数。详见[夹持诊断记录](../records/2026-10-18-task12-grasp-contact-diagnosis.md)。

2026-10-19新阶段：用户采用无新增诊断读回的交付方向，完整比较场景上限32/64各三次，固定顺序32-A、64-A、64-B、32-B、32-C、64-C，候选已静态冻结。新机10.150.165.46:22已连通，硬件身份改变，先执行旧包校准及视觉门禁；当前六轮尚未运行。权威队列在该机`/tmp/task12_iteration32_64_20261018/queue.json`，共享镜像`evidence/iteration32_64_queue.json`；所有输出先本地落盘，避免共享ENOSPC吞失记录。具体身份、门槛、局限及规则见[32/64完整对照](../records/2026-10-19-task12-iteration32-64-comparison.md)。

2026-10-19收尾：32／64各三次完整无新增读回回放均为一成两败，未采用64；两次32私有接触诊断一败一成，关键帧已实际复核。第3500帧手腕位置差0.00131mm、管底在夹爪中差28.414mm，偏差先于管架冲量；具体接触参数根因仍未证明。读取位置各少一个终态观察，base-Y存在接口符号差异，已明确限定，不合成缺帧、不作为保液认证。后处理已改为纯NumPy并恢复A现有记录，未重跑A仿真。仅YAML的25→2mm摩擦接触点合并距离候选已准备但未运行；生产USD无新增诊断读取，metric和动作不变。当前无后台仿真、尚不可交付，详细结果/局限/候选见[本轮记录](../records/2026-10-19-task12-iteration32-64-comparison.md)和个人目录CURRENT_STATUS。

2026-10-19目标继续推进：2mm接触点合并距离候选现已开始三次无新增读回完整回放，其他物理/动作/metric不变。旧“候选未运行”是上一阶段收尾状态；当前以`evidence/contact_correlation2_queue.json`及10.150.165.46上的实际进程为准。尚未采用、未交付，详见[本轮验证](../records/2026-10-19-task12-friction-correlation2-validation.md)。


## 日志审计恢复

第一轮 `contact_correlation2_a_20261018T194329_035108Z` 原生完成7000步，得分0.85、成功率0。监督器重复的原始 `[ERROR]` 字符串检查误把框架包装的 tqdm 进度条判为异常。移除这条重复检查，继续使用经过7项测试的严格日志分类器，并保留配置生效、动作、时钟和视频审计。没有修改GenManip或重新仿真A轮。恢复监督PID126500，权威状态改为 `/tmp/task12_correlation2_20261018/queue_resume_logfix.json`；原停止记录保留。A轮复核后继续B/C，当前仍不具备交付资格。

当前阶段进度：A轮0.85分且横倒，B轮1分且目视插入架孔，C轮继续；不得选择B轮覆盖A轮来声称稳定。后续一次性等待进程130284将于当前监督器正常完成后运行两个私有300步摩擦锚点诊断；权威等待记录在 `/tmp/task12_anchor_inspection_20261018/chain.json`。该短测不验证完整回架或保液，也不进入交付包。

自动续接已启用：当前权威队列 `/tmp/task12_relative_auto_20261019/queue.json`，共享 `relative_acceptance_20261019/queue_status.json`。按已批准的 `ready_jobs.json`自动执行，先索引15/0共8次；其余16组待核查后追加。普通任务失败继续，基础设施异常明确停止。恢复命令为在本轮授权4090上使用client Python运行个人repair/tools下 `run_relative_auto_queue.py`；完成项跳过，未解决的中断尝试必须先检查收尾结果，不能删除记录强制重跑。画面复核与仿真接续分离，不自动批准交付。

2026-10-19接入完成：ready_jobs已追加剩余64次，现共72条自动任务，加来源13已执行/待复核的4个槽位，总计76。remaining_protocol_pending为空。队列已自动从等待转为h08_old_0运行。原“16组待核查”仅为历史状态。mixed5早期偏差已定位到约800帧的入杯/加热姿态，参见relative_acceptance_20261019/mixed5_onset_review；先完成冻结版本对照，不边跑边改USD。21项辅助工具测试通过。

2026-10-19四卡管架容错探索：10.150.164.127上已独立对齐client0.2.0并验证四卡参考链路。GPU1/2/3分别执行初态居中摆直、18小孔每侧放宽0.5mm、组合候选的同卡成对完整回放，各12次；GPU0做静态查询与私有位姿测量。原10.150.165.46单卡正式对照不停止。身份、隔离、两项启动错误修复、静态18孔负对照、短测限制及队列路径见[四卡管架记录](../records/2026-10-19-task12-rack-tolerance-four4090.md)。300步0.15是短测截断，不计完整成功率；当前未晋级交付。

2026-10-19后续执行：上述36条已全部结束。GPU2/3改为各8条来源13/15的参考／居中交叉验证，权威状态为四卡机`/tmp/task12_four4090_20261019/centered_cross_gpu{2,3}/queue.json`；GPU0执行三版mixed5的1200步私有位姿诊断，权威状态`/tmp/task12_four4090_20261019/mixed5_pose_v2/queue.json`。不复用旧PID判断运行，不修改原单卡正式队列。诊断v1误读静态管架触发引擎错误，已留存并用独立v2修正；它不是任务零分。外部分析进程完成后保留对齐报告，不能自动批准交付。回架选帧必须匹配各来源的实际动作阶段，不能固定3450帧而漏掉3242步就结束的来源15。详见[跨卡复核与位姿诊断](../records/2026-10-19-task12-centered-cross-and-pose-onset.md)。

2026-10-20离线分析：正式72条队列和跨卡16条、诊断3条均已正常结束，当前无新仿真。先前对齐工具错误假设测量行一一连续，原失败报告保留；新离线方法使用精确关节状态、底座和等价物体位姿组，三版1–1200观察均可对应，初始化0观察保留歧义。不能累计重复compute的dt作为物理时间。原生分数、共同语义审核、媒体提取状态分开报告。CPU证据提取状态在个人repair的`evidence/offline_analysis_20261020/packet_queue_{formal,exploration}.json`，完成提取不意味着审核通过。数值、画面与限制见[离线分析记录](../records/2026-10-20-task12-offline-data-analysis.md)。

2026-10-20后续授权执行：用户选择最终显色时限提前0.75秒，开始时间不变、中间阶段按比例压缩、95%门槛不变；另以私有ABBA诊断隔离浴液参与。四卡机GPU0执行4条1200步诊断，GPU2/3执行5条显色候选完整回放。新权威队列位于四卡机`/tmp/task12_four4090_20261019/{bath_isolation,completion075_gpu2,completion075_gpu3}/queue.json`。与上段离线分析阶段分开，现有新仿真，但未启动全量重评或交付。构建/静态/测试、候选身份、后处理及限制见[显色时间与浴液隔离记录](../records/2026-10-20-task12-completion075-and-bath-isolation.md)。
