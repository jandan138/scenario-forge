# 科学实验修复：当前交接入口

更新：2026-10-12 中途收尾。**仅滴定已交付，另外三项未完成；当前没有本任务评测队列运行。**
先读本页，再读[阶段记录与踩坑台账](../records/2026-10-12-scientific-repair-checkpoint.md)。
[旧验收流水](../records/2026-10-11-scientific-five-item-acceptance.md)仅用于追溯，旧“当前/正在运行”不代表最新状态。

## 当前状态与位置

工作根 W：`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010`。

| 任务 | 当前状态 | 继续入口 |
|---|---|---|
| task10滴定 | 已发布到本人目录；原版120Hz/1582步满分，坏例及v2.1数据已验证 | `W/delivery_releases/task10_standalone_r1_20261011T162354Z/README.md` |
| task09称量 | 未发布；两次reset正常，完整4000/.5/sr0，两粒入瓶、三粒留舟 | `W/evidence/task09_default_offsets_summary.json` |
| task12水浴 | 当前物理版本未获完整资格；成功示范允许待重采 | `W/evidence/rim_v2_full_badcase_gate_revocation.json` |
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

1. 核对本页、阶段记录、CURRENT_STATUS与证据SHA；检查远程GPU/8087占用。当前只读检查为空闲，恢复时应重新检查。
2. 称量从三粒留舟的已存视频/动作开始；同一慢倒方案已失败，不再原样重复，也不据此导出新成功数据。只有training001使用最新初始化候选，不直接推广全部入口。
3. 水浴/银镜先定位一个完整失败例的触发条件。局部夹具PASS保留限定范围，不再立即放行整批队列。每个新试验写一个假设、预期观测与停止条件。
4. 新版本完成原版120Hz、完整日志、任务结果、四视频审查，再进行受影响坏例、成功数据和独立安装。新版本单独封包，不覆盖滴定。

用户已接受的约束不重复征求：称量4000步，水浴/银镜首轮7000步；后两项成功示范/训练待重采。
7000步仅58.333秒，部分加热本身需59–60秒；首轮保留这个预算限制，不擅改任务时长。
称量慢倒已获批准并测试失败；成功后才能重建数据的条件没有满足。

## 必须保留的验收区别

按[VAL-001至VAL-004](../standards/validation-and-delivery.md)，分别报告：

- 静态闭包、局部物理夹具、完整原版运行、任务成功、视觉与数据资格。
- 完整server及worker的启动/初始化/执行错误、警告、碰撞降级，不能只看回调。
- 最新称量PhysX错误行0，但有328765条faceIndex警告与其他警告；未证明警告无害或造成此次失败。`gate_pass`仅基础设施，不代表`demonstration_success`。
- 最新称量LCD数字166，小数点难以辨认；1.66g来自代码与两粒质量一致性推断，没有最终net/tare属性记录，不宣称独立测量了正确读数。
- 评测MP4的30fps编码与120Hz物理采样不同；LeRobot视频120fps。新动作不能配重复的旧观察充当新采数据。
- 引擎异常/noresult与正常回放任务失败分开；不通过改目标、质量作弊或降低计分门槛制造成功。

## 停靠验证

本次只改文档、证据索引及制作区状态；不改变USD、轨迹、metric或已封包文件。
验证完成：16份证据文件SHA及25个本地文档链接通过；`git diff --check`通过。
`make check`退出0：1255 passed、1 skipped（549.10秒），ruff、package-smoke与phase10x-smoke通过。
日志：`W/checkpoints/20261012_midway/make-check.log`。这些是仓库与记录检查，不增加场景物理资格。
