# task12旧满分轨迹全量回归与掉分归因

状态：执行中，正式交付新增回归门槛；并未认定旧评分错误或新版规则正确。

## 用户决定和交付约束

用户要求全量验证旧满分动作；确认“旧画面确实成功、初态/时序已对齐，而新版失败”的未解问题阻塞正式交付。
不能仅凭原版程序不崩溃、以新版metric更严格为理由、改变动作或注明待重采绕过回归。
称量渲染及当前水浴坏例队列不停止，新回归使用相同单4090在坏例队列结束后串行运行。
仅允许YAML、USD及依赖、task data和scientific metric进入接收方；无核心/SDK/机器人修改或辅助脚本依赖。
水浴LeRobot仍暂缓。120Hz/7000步不变；超出此预算才能还原旧时长的情形要单列冲突再讨论。

## 来源清单与冻结版本

工作根R为`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/task12_liquid_color_20261012`。
扫描建通`scientific_experiments`与`scientific_experiments_old`分别327/80条水浴结果，找到17/4份score1且success_rate1。
21份来源有19组不同动作；两份60000旧记录有相同动作/case/初始机器人状态的重复副本，别名与原文件身份全部保留。
每帧16维手臂/夹爪目标及3维底座目标均有限，动作长度与旧结果步数一致。旧满分不自动认证真实成功。

完整清单`R/historical_success/catalog.json`包含原路径/哈希、旧结果、动作哈希、初始机器人观测、视频、
对应新YAML/初始化metadata哈希及别名。catalog冻结SHA为`15c87f1fc650a7b8229df8087d1657d18bb239ada427bd963b15db184692935d`；
运行状态、视觉与归因报告分开保存，不改catalog。当前接收版本`receiver_archive_install_20261013T031857Z`。

| 索引 | 原运行 | case | 动作数 |
| --- | --- | --- | ---: |
| 0 | gpt6_all14_mixed_20260926 | mixed_5 | 6542 |
| 1 | gpt6_all14_mixed_20260926 | mixed_1 | 3622 |
| 2 | gpt6_all14_mixed_20260926 | mixed_8 | 4202 |
| 3 | openwam_all20_100000_resume64_fixed_20261001 | mixed_1 | 2802 |
| 4 | openwam_all20_100000_resume64_fixed_20261001 | mixed_3 | 2342 |
| 5 | openwam_all20_100000_resume64_fixed_20261001 | unseen_background_9 | 2862 |
| 6 | openwam_all20_100000_resume64_fixed_20261001 | unseen_instruction_9 | 2782 |
| 7 | openwam_all20_100000_resume64_fixed_20261001 | unseen_prospect_3 | 2362 |
| 8 | pi05_all14_100000_20260924 | mixed_7 | 3362 |
| 9 | pi05_all14_100000_20260924 | unseen_prospect_4 | 3022 |
| 10 | pi05_all14_40000_20260924 | unseen_background_5 | 2822 |
| 11 | pi05_all14_40000_20260924 | unseen_background_9 | 2822 |
| 12 | pi05_all14_40000_20260924 | unseen_instruction_10 | 3682 |
| 13 | pi05_all14_40000_20260924 | unseen_prospect_10 | 3722 |
| 14 | pi05_all14_40000_20260924 | unseen_prospect_3 | 2562 |
| 15 | pi05_all14_60000_20260922 | unseen_instruction_4 | 3162 |
| 16 | pi05_all14_60000_20260922 | unseen_instruction_9 | 2842 |
| 17 | scientific_step60000_all20 | unseen_prospect_1 | 3022 |
| 18 | scientific_step60000_all20 | unseen_prospect_10 | 3242 |

## 实现与验证

辅助工具均在R/tools，未加入Scenario Forge核心或接收包。
`run_historical_success_native.py`与`audit_task12_historical_native.py`沿用已验证原版服务流程，
增加catalog来源/配置哈希校验与初始机器人状态比较；每次新run ID，原动作逐条回放，耗尽后保持末目标。
原记录无权威动作时间戳，首轮只是120Hz逐目标筛选，不宣称原时间轴或闭环策略等价。

正确mixed5来源通过新增审计；用错误来源审计同一次回放被拒绝且不产生通过报告，
见`historical_success/audit_positive.log`和`audit_negative_wrong_source.log`。
索引0复用最终版本mixed5两次7000步/.15结果，原sourceSHA与runtime已核验；其余18组由
`run_historical_success_queue.py`等待旧队列完成后执行，状态`historical_success/queue.json`。
低分保留并继续筛查，引擎/基础设施错误停止队列，不记录为普通任务失败。

封包程序`finalize_coarse_phase1_release.py`已增加`historical_success_release_gate.json`前置门禁，
要求19组筛查、视觉/时序复核、零未解有效旧成功回归，且证据绑定最终runtime和catalog哈希。
当前门禁BLOCKED_PENDING_FULL_SCREEN_AND_ATTRIBUTION，旧坏例队列全完成也不能直接发布。

## 首条掉分线索与证据边界

GPT mixed5旧结果1分/6542步，当前同版本两次.15分/7000步，源6542目标全部消费、随后458步保持。
旧视频抽帧见`historical_success/old_visual/history_00`：3271/4906帧样液已呈橙色，
末6541/6542帧试管在架附近更竖直/倾斜；新版显色停在绿色且管横倒。500帧旧视觉样液为短蓝色体，
新版动态样液有管口飞溅。已记录`mixed5_old_visual_preliminary.json`，不能因此直接认定旧成功无效。
实际孔位/插深、旧时间轴及改变物理结果的原因仍需核对。

只读解析旧RRD（现有SDK rerun0.28.2，无SimulationApp/GPU）：只有视频引用与机器人关节/夹爪/底座数据，
无物体位姿、反应进度或原生物理时钟。stable_time步距1/30秒，当前导出器明确使用frame_index/fps；
log_time也在旧episode结束后生成。因此它不能证明原动作30Hz或用于擅自重采样。
原路径没有对应旧server日志目录，历史运行USD/metric快照身份仍待寻找。
证据`mixed5_old_rrd_schema.txt`与`mixed5_rrd_timing_limits.json`。

## 后续归因和验收

逐组核对旧画面真成功、初态/动作语义/保持时长，随后分离同状态新旧metric与新旧USD对照。
缺少对象状态时不能仅凭机器人记录离线重打分；需要隔离的复现采集。缺少历史资产快照时不作完全复现声明。
针对真实回归在允许范围内修复，再对受影响样本重验；首个新版真成功需独立重复。
最终对照表必须包含旧成绩、旧画面、等价性、新成绩、失败阶段、因果证据及修复状态。

规范依据ASSET-001/003、MAT-002、STATE及VAL-001/002/003/004。规范无需变更：这是任务级回归门槛和证据补齐，
不改变核心包/schema/API、通用评分或物理默认。既有make check1255通过/1跳过仍为仓库基线；本轮仅外部工具和文档。
