# 科学实验修复：当前交接入口

更新：2026-10-12，**滴定坏例配对补证已完成：重建旧包3次、新包3次均2000步未弹飞，修复因果仍未证实。**
原滴定封包保持不变；称量运行内容已完成新规则验收，600条数据在后台生产；水浴在独立工作目录继续修复，银镜未交付。
完整结果、原日志纠正及视频入口见[滴定配对回归](../records/2026-10-12-task10-badcase-paired-regression.md)。
先读本页，再读[阶段记录与踩坑台账](../records/2026-10-12-scientific-repair-checkpoint.md)。
[旧验收流水](../records/2026-10-11-scientific-five-item-acceptance.md)仅用于追溯，旧“当前/正在运行”不代表最新状态。

## 当前状态与位置

工作根 W：`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010`。

| 任务 | 当前状态 | 继续入口 |
|---|---|---|
| task10滴定 | 已发布到本人目录；原版120Hz/1582步满分及v2.1数据已验证；旧/新各3次未复现历史弹飞，因果未证实 | `W/delivery_releases/task10_standalone_r1_20261011T162354Z/README.md` |
| task09称量 | 新规则原版机器人1.0，运行内容已封存；600条LeRobot持续生产，未完整交付 | `W/task09_recapture_600_20261012/CURRENT_STATUS.json`及[操作说明](task09-recapture-dataset.md) |
| task12水浴 | 新候选完整mixed5运行、实际变色/重置及三类守卫通过；归档独立安装通过，剩余四例验证中，未交付 | `W/task12_liquid_color_20261012/CURRENT_STATUS.json`及[操作说明](task12-uniform-liquid-repair.md) |
| task_z4银镜 | 完整bad11引擎失败；加容量、PGS均未解决；成功示范允许待重采 | 同上及 `W/evidence/rim_v2_pgs_diagnostic_run.json` |

本次停靠证据SHA见[小型索引](../records/2026-10-12-scientific-repair-checkpoint.evidence.json)。
可变状态只看 `W/CURRENT_STATUS.json`；本次快照在 `W/checkpoints/20261012_midway/`。
不要按目录名`final`、最近编号或旧gate的PASS选择交付版本。

## 交付边界与冻结内容

只安装下列五类；接收者无需生产/测试脚本，也不修改GenManip core、SDK或机器人源。

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

## 恢复工作时的顺序

1. 核对本页、阶段记录、CURRENT_STATUS与证据SHA；检查远程GPU/8087占用。补证收尾已确认本次进程全部退出；最终状态看配对回归comparison_summary/final_cleanup，恢复时重新检查。
2. 称量按[新数采制作说明](task09-recapture-dataset.md)检查持续生产队列；原版机器人成功及新验收口径见[新记录](../records/2026-10-12-task09-readout-range-acceptance.md)。旧慢倒失败保留历史资格，不重跑它或停止现有600条生产。
3. 水浴按最新独立队列完成剩余四例、人工画面审查及phase1发布；银镜继续定位完整失败触发。局部资格只保留限定范围，每个新试验记录假设、预期观测和停止条件。
4. 新版本完成原版120Hz、完整日志、任务结果、四视频审查，再进行受影响坏例、成功数据和独立安装。新版本单独封包，不覆盖滴定。

用户已接受的约束不重复征求：称量4000步，水浴/银镜首轮7000步；后两项成功示范/训练待重采。
7000步仅58.333秒，部分加热本身需59–60秒；首轮保留这个预算限制，不擅改任务时长。
称量旧慢倒已测试失败；后续用户提供新60条成功数采，并明确取消最终连续稳定要求，采用同一步有效4.0–5.0g净重及五颗在瓶内的口径。当前运行内容资格与旧慢倒版本不同，不能继续套用旧“不可导出”结论。

## 必须保留的验收区别

按[VAL-001至VAL-004](../standards/validation-and-delivery.md)，分别报告：

- 静态闭包、局部物理夹具、完整原版运行、任务成功、视觉与数据资格。
- 完整server及worker的启动/初始化/执行错误、警告、碰撞降级，不能只看回调。
- 旧称量慢倒运行PhysX错误行0但有大量faceIndex警告；保留其原范围，不用它解释新版本。各次运行的错误、警告与任务结果分别核对。
- 新称量接受时字段快照为4.01g；原生末帧LCD数码清晰度有限，不把数值快照当成人工读图，也不宣称读数波动已修复。
- 评测MP4的30fps编码与120Hz物理采样不同；LeRobot视频120fps。新动作不能配重复的旧观察充当新采数据。
- 引擎异常/noresult与正常回放任务失败分开；不通过改目标、质量作弊或降低计分门槛制造成功。

## 停靠验证

本次只改文档、证据索引及制作区状态；不改变USD、轨迹、metric或已封包文件。
验证完成：16份证据文件SHA及25个本地文档链接通过；`git diff --check`通过。
`make check`退出0：1255 passed、1 skipped（549.10秒），ruff、package-smoke与phase10x-smoke通过。
日志：`W/checkpoints/20261012_midway/make-check.log`。这些是仓库与记录检查，不增加场景物理资格。
