# validation 继承最终 test 修复

状态：候选已生成，静态检查通过；原生运行验收中，未安装接收目录，未提交或 push。

用户确认保留 validation 的布局、指令和视角变化，以最终交付 test 为准继承资产、运行参数、评分和必要初始化修复。基线为接收仓库 `40ebb02006f5565f93762278b569e570668bb2b8`；task11 保持最终撤回后的16/1，不恢复192/16。

独立工作目录：`/mnt/data/zhuzihou/GenManip-Sim-deliveries/validation-alignment-20261104`。
工具、测试日志和文件清单：`/cpfs/user/zhuzihou/dev/validation-alignment-20261104`。

## 改动及证据

- 136个带definition_source的validation入口建立test来源映射；另外6个专用验收入口不强套普通变体映射。
- 修改20份evaluation YAML：task09八份对齐摩擦、额外偏移覆盖和对象部件配置；task12八份、银镜四份对齐物理参数及时间步写法。逐份解析后确认只有白名单字段变化。
- 生成28份metadata候选：task09/task10各八份、水浴八份、银镜四份，继承来源goal及必要属性恢复。保留其余字段；不复制历史episode_revision或机器人驱动目标；为每个候选生成独立的episode_revision，使控制器在恢复新粒子初态后重新构建。粒子点通过USD粒子坐标到世界、来源容器局部坐标、目标容器世界坐标再返回粒子坐标，检查局部形状误差不超过1e-6。
- 配置检查改前52项差异，改后通过；新增136来源配对回归测试；接收仓库38项unit通过，git diff --check通过。
- 所有新增属性路径静态存在性和metadata非目标字段保留检查通过。这些检查不替代冷启动、重置或完整回放。

原验收主机10.150.168.71为Isaac4.1，当前编辑主机为4.5。运行必须使用原验收环境；首个task09原生reset使用独立工作目录、独立输出和缓存，接收方当前配置与saved未覆盖。原生验收结果以工作目录evidence和后续更新为准。

## 规范

适用VAL-001/002/003/004/008、STATE-001/002/003。规范无需变更：本次修复特定交付split漏同步，不引入通用物理参数、包schema或核心接口。历史活动交付仍有效，候选不能冒充READY。

首轮task09原生reset完成，但随后代码复核发现滴定控制器以episode_revision缓存初态，因此R1滴定回放主动中止，不作验收证据。R2补充新候选epoch，28份metadata重新生成，回放队列重新启动；此前task09 reset不作为R2最终资格。

## 当前验证进度

Scenario Forge `make check`通过：1255 passed、1 skipped，lint与Phase10.x检查通过。GenManip 38项unit通过，新测试覆盖136个来源映射，Black和diff检查通过。

R2首个滴定入口已完成原生reset并开始执行LMDB动作。native_count=600时记录pbd_valid=true、pbd_error为空、controller_pose_valid=true；此为中间状态，不是完整回放或交付通过。28例串行队列的实时状态：`/cpfs/user/zhuzihou/dev/validation-alignment-20261104/replay_status.json`。尚待完整回放、媒体/原生状态审计和最终安装；候选不具备READY资格。

`ACTIVE_DELIVERY.json`仅为旧smoke增加历史快照和task09故障已被40ebb020替代的说明，修改前副本保存在本次证据目录；没有把活动入口切到候选。操作指南顶部已区分当前接收代码40ebb020与联合归档基线97ae5e98。

## 合入准备

候选Git提交`478874d1`位于`delivery/validation-test-alignment-20261104`，包含20份配置与2份测试文件，提交Black钩子通过。尚未合入建通分支或push；远端HTTPS缺少认证，尚不能确认最新远端。

R2首例滴定完成2000步、0.4分。四路视频各2001帧均完整解码；原LMDB938条动作逐值核对通过，后续保持末目标，底座尾增量为零。起/中/末关键帧未见明显缺资产或黄格；深色反射玻璃限制液体现象观察，未据此宣称任务成功或解释全部低分。`visual/replay00/review.json`保留非独立复核结论。

## CUDA700诊断与续跑

截至09:05 UTC，3例完整回放，task10 validation_unseen_background_2失败。worker日志先在第918步报告arm_state_jump_too_large，额外尾帧期间首次记录sg_SparseGridClearDensity CUDA700，继而iso_ComputeParticleDensityUsingSDFSparse及其他内核级联失败。不能仅凭末尾CUDA异常认定偶发Isaac故障。

源LMDB有1166条有限动作；918附近相邻手臂目标变化约0.00038147rad，910–925窗口最大约0.00877476rad，夹爪在918处无变化，底座为零。证据见first_cuda_failure_context.txt、failure_action_window.json。

用户要求继续诊断推进：在原4.1主机GPU0上以新run ID `align20261104_diag_03_101016`重新冷启动同一候选/配置/动作。旧日志保留。队列新增进程锁、每次独立run ID及独立失败清单；重复失败不计为通过，保留问题后继续其他案例，最终只要有失败就标记COMPLETE_WITH_UNRESOLVED_FAILURES。必要的旧版对照仍待冷复现结果决定；本次没有更改物理参数或接收目录。

## 2026-11-05 银镜零分复核

28例最终选择版本均生成结果；所有执行命令逐条与LMDB原动作/末目标保持核对一致，尾部底座增量为零。银镜四例原记录仅90/62/62/64条动作，后续保持到7000步，不构成完整任务示范。各例overlook/top的起始、源片段中间、源片段结束与运行末帧复核未见入浴操作；12次原生采样均sample_not_in_water、heated_seconds=0、deposition_progress=0，0分与这些证据一致。该结果不能证明完整任务成功，也不能独立归因为资产故障。此前应先识别短片段，避免将长时间保持当完整示范验收。

最终选择worker日志指定标记检查未发现新的physics-error callback、invalid-state或traceback；并非全启动日志零错误认证。静态假浴水模式评分读取repair:bath_valid，不能仅凭tollens:pbd_valid=false判失效。原CUDA700失败保留，冷启动成功只说明此次未复现。证据：all_action_audit.json、runtime_state_audit.json、silver_zero_score_review.json及visual/validation_mixed_*/silver.jpg。候选尚未安装。

## 2026-11-05 收尾检查

112路视频全量解码通过；28例原命令与末目标保持逐值核对通过。检查最终选择运行的server和对应Ray worker原始out/err，均找到日志，未检出扫描的Error/Traceback/illegal-memory/SCIENTIFIC_HEAT_ERROR标记；不将此表述为没有警告。已由实现者查看全28例overview起/中/末画面，并补查水浴低分、银镜短片段的top视角；非独立、非逐帧零穿透认证。

水浴mixed_1与unseen_prospect_2的烧杯相对加热盘偏移，原生状态bath_outside_plate_support、无加热；mixed_2采样状态sample_not_in_water，画面未显示完成入浴；unseen_instruction_1反应可见但末态试管未回架。低分保留，不用改布局或放宽评分制造成功。按既定修复继承/兼容范围，收尾状态为CANDIDATE_REVIEW_COMPLETE_WITH_DISCLOSED_LIMITS；不宣称完整策略成功或CUDA故障根因已解决。

已生成validation-alignment-reviewed-r2.tar.gz、reviewed-SHA256SUMS及CLOSEOUT.json，位置同本次证据根目录。尚未安装或推送：Gitee HTTPS认证仍缺失，无法确认远端端点。接收目录新增task07 metric未提交改动，本次未触碰；本次50文件的原始哈希仍匹配。后续合入须保留该同事改动并再次核对运行占用。

后续：2026-11-05已完成实际安装与远端推送，最终提交8bb1df43；见[最终交付记录](2026-11-05-validation-alignment-delivery.md)。本记录保留候选、失败、回滚和验收过程，不作为当前未交付结论。
