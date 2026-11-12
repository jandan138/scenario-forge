> 2026-10-21：Task18银镜正在独立制作根验证，尚未安装或发布READY；本轮不更新银镜LeRobot。当前入口与证据边界见[银镜交付操作说明](task18-silver-mirror-delivery.md)，不要使用下方旧银镜阶段状态判断当前进程。

> 2026-10-20：Task12真液体水浴r1已安装发布，READY与证据在 `/mnt/data/chenjiantong/scientific_experiments_data/releases/task12_real_liquid_r1/`。接收仓库当前分支 `delivery/task12-real-liquid-r1`（9490df9a），称量既有内容保持；本轮不更新水浴LeRobot。验收范围与限制见[水浴收尾](../records/2026-10-20-task12-delivery-closeout.md)。

# 科学实验修复：当前交接入口

2026-10-19 OSS补充交付已完成：标准目标下 `task_09_solid_weighing_300/`、`task_09_solid_weighing_500/` 共4008个对象全量MD5校验及SSH代表回读通过；本地READY保持原范围，OSS回执见[发布记录](../records/2026-10-19-task09-oss-publication.md)。

通用方法见[单任务制作与交付指南](genmanip-task-delivery.md)，新任务可复制[交付与验收清单](templates/genmanip-task-delivery-checklist.md)。本页保留具体任务的阶段记录；判断当前产物时，以最新交付入口及其验收范围为准。

2026-10-19：标准 v3 已安装交付并生成 READY。正式数据及回执位于 `/mnt/data/chenjiantong/scientific_experiments_data/releases/task09_standard_v3`；正式仓库分支为 `delivery/task09-standard-v3-final`（82cabca5）。两档reader、40独立初始化、四条回放链路及视频检查通过；四例分数为0.1/0.1/1/1，不代表全部任务成功。一次SDK启动超时重试记录保留。见[接收安装与验收记录](../records/2026-10-19-task09-receiver-installation.md)。下文旧日期内容为历史阶段快照。

## 历史阶段记录（不作为当前运行指令）

2026-10-18 最新：500 条渲染已完成，300 档导出及验收 PASS。旧导出主机失联后，500 档从已提交的 354 条复制到独立候选目录，在四卡主机 `10.150.164.127` 的持久 tmux 会话续导。当前状态读取 `/cpfs/user/zhuzihou/dev/task09-current.json` 中的 `active_queue`（`export_recovery/STATE.json`），旧 multi/COORDINATOR 不再代表当前执行。续导后自动进行完整 500 档验收，接收目录安装仍待完成。见[导出恢复记录](../records/2026-10-18-task09-export-recovery.md)。

2026-10-17最新称量生产：四卡实例通过完整资格检查后，已与原两台合并为六卡队列，交接时保留291条已验收记录。当前使用`standard_v3/tools/multi_status.py`或`standard_v3/multi/COORDINATOR.json`；下文双机入口为此前阶段快照。完整导出及最终接收安装仍待完成，见[六卡运行记录](../records/2026-10-17-task09-six-gpu-render.md)。

2026-10-17当前称量生产：标准流程v3已切换为两台单卡并行，实时状态读取制作根下`standard_v3/dual/COORDINATOR.json`或运行`standard_v3/tools/status.py`。旧队列迁移时242条已验收结果全部保留；v3完整数据导出和接收目录安装仍待完成。见[双机渲染记录](../records/2026-10-17-task09-dual-host-render.md)。

2026-10-15补充：[回放协议与交付影响清单](../records/2026-10-15-replay-protocol-delivery-impact-audit.md)已完成定向审计。
滴定/称量原版LMDB成功资格按原范围保留；滴定历史弹飞因果及历史时间精确等价仍需补证。
称量状态渲染不等同600次物理成功；水浴旧19组未校准回放不能直接归因新USD。
历史包未改写。下文2026-10-12状态是阶段快照，水浴最新状态看任务自己的CURRENT_STATUS及[水浴操作说明](task12-uniform-liquid-repair.md)，
称量实际生产状态看production/queue.json，不用全局旧快照判断是否正在运行。

更新：2026-10-12，**滴定坏例配对补证已完成：重建旧包3次、新包3次均2000步未弹飞，修复因果仍未证实。**
原滴定封包保持不变；称量运行内容已完成新规则验收，600条数据于2026-10-15完成渲染、导出和远端reader验收，最终就绪看下表入口；水浴在独立工作目录继续修复，银镜未交付。
完整结果、原日志纠正及视频入口见[滴定配对回归](../records/2026-10-12-task10-badcase-paired-regression.md)。
先读本页，再读[阶段记录与踩坑台账](../records/2026-10-12-scientific-repair-checkpoint.md)。
[旧验收流水](../records/2026-10-11-scientific-five-item-acceptance.md)仅用于追溯，旧“当前/正在运行”不代表最新状态。

## 当前状态与位置

工作根 W：`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010`。

| 任务 | 当前状态 | 继续入口 |
|---|---|---|
| task10滴定 | 已发布到本人目录；原版120Hz/1582步满分及v2.1数据已验证；旧/新各3次未复现历史弹飞，因果未证实 | `W/delivery_releases/task10_standalone_r1_20261011T162354Z/README.md` |
| task09称量 | 标准v3已安装至建通目录并READY；300/500两档reader、40初始化及四回放链路通过，分数0.1/0.1/1/1；未做训练或连续切场认证。旧600仅归档 | [接收交付记录](../records/2026-10-19-task09-receiver-installation.md)，正式release内README及READY.json |
| task12水浴 | 旧版三个代表的执行协议已校准；新液体包进行同版本显色/回架验证，最终要求19组各两次成功；未交付。具体运行状态以任务队列为准 | `W/task12_liquid_color_20261012/CURRENT_STATUS.json`及[操作说明](task12-uniform-liquid-repair.md) |
| task_z4银镜 | 完整bad11引擎失败；加容量、PGS均未解决；成功示范允许待重采 | 同上及 `W/evidence/rim_v2_pgs_diagnostic_run.json` |

本次停靠证据SHA见[小型索引](../records/2026-10-12-scientific-repair-checkpoint.evidence.json)。
全局`W/CURRENT_STATUS.json`仅作任务入口路由；实际进度以各任务自己的CURRENT_STATUS和队列为准。
全局记录及本页历史数字可能是快照；2026-10-12快照在`W/checkpoints/20261012_midway/`。
不要按目录名`final`、最近编号或旧gate的PASS选择交付版本。

## 历史交付范围与冻结内容（2026-10-12阶段）

以下保留2026-10-12阶段的交付范围及当时状态，不代表后续Task09标准v3的实际代码差异；后者的标准渲染修复和已安装状态见页首接收记录。新任务的范围按通用指南与本次约定核对。

当时约定只安装下列五类；接收者无需生产/测试脚本，不修改GenManip core、SDK或机器人源。

| 类别 | 相对路径/形式 |
|---|---|
| YAML | `configs/tasks/scientific_experiments/` |
| USD及依赖 | `saved/assets/scene_usds/scientific_experiments/` |
| task data | `saved/tasks/scientific_experiments/` |
| metric | `genmanip/extensions/metrics/scientific_experiments/`，代码提交/补丁 |
| LeRobot | 标准v2.1数据集，注明读取环境 |

本轮GenManip交付阶段的试验和交付均在朱子厚目录。接收仓库
`/mnt/data/chenjiantong/GenManip-Sim`只读，尚未安装或发送给同事；飞书文档未改。
资产物理制作留在ConvertAsset，Scenario Forge不接纳episode runner或SDK核心依赖。

滴定包已经封存，不在原包内追加后续诊断或改文件：

- 发布目录：`W/delivery_releases/task10_standalone_r1_20261011T162354Z/`。
- 原版基线：`0e99ea01eec7780e53fa2ce3ecb0fce1a6b4500a`。
- 仅滴定metric提交：`38425dc6eb18fba6560184745acf27fe91241e10`（两文件）。
- 离线包、metric补丁、LeRobot归档的安装顺序、SHA、依赖和限制见封包README与RELEASE_MANIFEST。
- 保留20环境入口的静态检查；动态资格仅限已记载回放，不宣称20条策略全成功。
- 原成功例用标准LMDB客户端；原坏例用独立测试客户端提交原动作，工具不成为安装依赖。

## 历史阶段的恢复顺序（须先核对当前入口）

1. 核对本页、阶段记录、CURRENT_STATUS与证据SHA；检查远程GPU/8087占用。补证收尾已确认本次进程全部退出；最终状态看配对回归comparison_summary/final_cleanup，恢复时重新检查。
2. 称量按[新数采制作说明](task09-recapture-dataset.md)检查最终READY与MANIFEST；600条已完成，不因历史SSH失败重启渲染。原版机器人成功及新验收口径见[新记录](../records/2026-10-12-task09-readout-range-acceptance.md)，旧慢倒失败保留历史资格。
3. 水浴按[当前操作说明](task12-uniform-liquid-repair.md)定位已校准协议下的新液体对照；不得重启旧的统一absolute/单步回放。最终同一版本须完成19组各两次成功、坏例和安装验收。水浴LeRobot本轮暂缓；称量600条状态独立见上项，不随水浴试验重做。每个新试验记录假设、预期观测和停止条件。
4. 新版本完成原版120Hz、完整日志、任务结果、四视频审查，再进行受影响坏例、成功数据和独立安装。新版本单独封包，不覆盖滴定。

用户已接受的约束不重复征求：称量4000步，水浴/银镜7000步；银镜成功示范可待重采，水浴已升级为旧成功恢复及19组各两次验收，不再用待重采替代完成。
7000步仅58.333秒。水浴允许有证据的统一反应时长版本调整，不允许逐轨迹调时或擅增上限；具体候选与验证见水浴操作说明。
称量旧慢倒已测试失败；后续用户提供新60条成功数采，并明确取消最终连续稳定要求，采用同一步有效4.0–5.0g净重及五颗在瓶内的口径。当前运行内容资格与旧慢倒版本不同，不能继续套用旧“不可导出”结论。

## 必须保留的验收区别

按[VAL-001至VAL-004](../standards/validation-and-delivery.md)，分别报告：

回放另外遵守[VAL-008](../standards/validation-and-delivery.md#val-008)：交接说明记录每个来源的
控制模式、单位、动作/物理/视频时间轴、分块/渲染、初态和终止方式。缺失字段标为未知或有证据的推断，
不写统一的8步/30步或absolute默认，不要求接收方安装诊断脚本。

- 静态闭包、局部物理夹具、完整原版运行、任务成功、视觉与数据资格。
- 完整server及worker的启动/初始化/执行错误、警告、碰撞降级，不能只看回调。
- 旧称量慢倒运行PhysX错误行0但有大量faceIndex警告；保留其原范围，不用它解释新版本。各次运行的错误、警告与任务结果分别核对。
- 新称量接受时字段快照为4.01g；原生末帧LCD数码清晰度有限，不把数值快照当成人工读图，也不宣称读数波动已修复。
- 评测MP4的30fps编码与120Hz物理采样不同；称量600条v2.1按现有工具导出15FPS时间轴，原数采频率未确认，不能将其写成120FPS。新动作不能配重复的旧观察充当新采数据。
- 引擎异常/noresult与正常回放任务失败分开；不通过改目标、质量作弊或降低计分门槛制造成功。

## 停靠验证

本次只改文档、证据索引及制作区状态；不改变USD、轨迹、metric或已封包文件。
验证完成：16份证据文件SHA及25个本地文档链接通过；`git diff --check`通过。
`make check`退出0：1255 passed、1 skipped（549.10秒），ruff、package-smoke与phase10x-smoke通过。
日志：`W/checkpoints/20261012_midway/make-check.log`。这些是仓库与记录检查，不增加场景物理资格。

2026-10-17：Task09标准流程v3增设双机渲染调度。用户提供的新SSH实例实际只分配一张GPU，经确认与原单卡实例并行生产；不是四卡资格。数据版本、300/500训练划分、40评测任务和交付分支不变。实时进度以`standard_v3/dual/COORDINATOR.json`为准，调度就绪不代表安装就绪，见[双机记录](../records/2026-10-17-task09-dual-host-render.md)。
