# Task18 银镜修复与交付操作说明

最新配置交付（2026-10-21）：在同事 rebase 后的 `cc2b38e1` 上追加 `f67879b5`，称量40、水浴50、银镜20个既有交付 YAML 已进入 Git 并正常推送。银镜配置不再只存在于未提交工作区；USD/task data 仍离线交付。34项局部测试及三个代表冷启动通过，原问题限制不变。见[配置补交记录](../records/2026-10-21-genmanip-delivered-config-submission.md)。以下历史段落的提交号与安装状态按当时版本理解。

提交历史最新说明（2026-10-21）：本地修复已按用户要求汇总为两个节点并正常推送Gitee。`feature/scientific_experiments` 当前为efe5d08a，银镜metric包含在第一个汇总提交109c809e中；安装时的f6ec55ae通过[新旧提交映射](../records/2026-10-21-genmanip-two-commit-remote-integration.md)追溯。最终文件树、已安装资产和未提交配置保持原样，既有物理/碰撞限制不因历史整理而关闭。以下安装记录中的“未push”和f6ec55ae是当时状态。

状态：2026-10-21，银镜代码已本地提交并安装建通目录，问题未全部关闭，未push、无全部验收完成READY。当前安装回执入口为 `/mnt/data/zhuzihou/GenManip-Sim/saved/deliveries/scientific_experiments/task18_silver_mirror_install_20261021/README.md`，见[本地安装记录](../records/2026-10-21-task18-receiver-local-install.md)。阶段评估包eval_r1及其原校验和保持不变，见[评估交付记录](../records/2026-10-21-task18-evaluation-delivery-r1.md)。

接收分支规则：保留 `feature/scientific_experiments`。用户后续批准保留Task04并接入银镜；外部操作先将Task04的a7084a99合回feature，本次再快进加入银镜f6ec55ae。署名为 `zhuzihou <zhuzihou@pjlab.org.cn>`。原集成分支和既有修改保留。下文v8安装脚本为历史草案，切换delivery分支方式已停用；当前安装脚本和回执在task18-receiver-install-20261021。冻结实验副本不回写改动。

本任务遵守[场景规范入口](../standards/README.md)和[验证与交付](../standards/validation-and-delivery.md)，特别是 VAL-002 的证据分类及 VAL-008 的回放协议。诊断过程见[当日记录](../records/2026-10-21-task18-engine-isolation-and-visual-update.md)。

## 身份与范围

当前阶段：冻结B原样验证的自动队列已结束，阶段包随后按用户批准安装至建通原分支。`provisional_B`保留为历史验证材料，`receiver_B`是独立验证副本；代码与资产身份以页首安装回执及eval_r1 MANIFEST对应关系为准。液面参数范围、碰撞/穿透和机器人回架问题仍保留限制。验证过程见[冻结B验证记录](../records/2026-10-21-task18-frozen-B-qualification.md)。

飞书 Task18 对应 `task_z4_silver_mirror_reaction`。当前制作根为
`/cpfs/user/zhuzihou/dev/task18-fehling-baseline-20261021`；从其中 `evidence/diagnostic_queue_r2.json`、`evidence/A_identity.json`、`evidence/paired_jobs_r2.json` 定位菲林基准与最小迁移对照，见[新阶段记录](../records/2026-10-21-task18-fehling-baseline-reset.md)。旧制作根 `task18-silver-delivery-20261020` 及其 v8 为历史实验，接收端失败后未获交付资格。状态文件须结合实际进程、日志及产物核实，不能单凭 RUNNING 字样重启或判断运行完成。

本轮只安装 Task18 的三个规范相对目录和独立 metric 提交：

- `configs/tasks/scientific_experiments/task_z4_silver_mirror_reaction`
- `saved/assets/scene_usds/scientific_experiments/task_z4_silver_mirror_reaction`
- `saved/tasks/scientific_experiments/task_z4_silver_mirror_reaction`
- `genmanip/extensions/metrics/scientific_experiments/task_z4_silver_mirror_reaction.py`

本轮不更新 LeRobot，不改 GenManip 核心、SDK 或机器人资产。制作侧启动、观察、转换、验证脚本位于外部制作根，接收运行不能依赖它们。metric 仅按运行状态评分，不承担动作回放或轨迹修正。已有 `repair_checks.py` 沿用接收基线，不重复增加未声明代码变更。

原始 120 Hz、7000 步及各场景30–60秒反应时间保留；取消碰壁单独停表，保留入水、有效液体、姿态、加热器位置与支撑条件。7000步为58.33秒，部分原配置单是完整反应就超过此预算；按用户确认的首轮边界保留限制，不逐轨迹改时间。完整机器人成功示范可注明待补采，受控银镜生成与重置演示必须完成。

## 回放与验收

本次记录源的协议已单独校准：OpenWAM 指定源逐步请求，Pi05 指定源30步分块；此规则不推广为其他记录的默认值。mixed17原动作6922帧，随后保持末帧手臂、零相对底座增量至回合结束，必须把补尾与原策略输出区分。不得平滑旧动作。

原生评测视频通常每动作步存一帧、按30fps编码，视频播放秒数不能当作物理秒数。受控演示每4物理步存一帧，以30fps播放。

逐例检查客户端退出码、最终结果、四路视频完整解码、原动作一致性、机器人状态、完整服务/worker日志及专项画面。外层启动器退出0或 `receipt.error=null` 都可能伴随客户端异常及CUDA错误，不能单独作为通过条件。收尾还须再扫终态日志，避免漏掉最后一次轮询之后的错误。

低分按真实任务失败保存；没有结果或引擎异常独立记为运行失败。抽帧未见异常不能宣称逐帧无穿模。原生meta/RRD不含试管、烧杯的完整逐帧位姿，不能用机器人关节状态代替物体接触证据。诊断观察器会影响调度，其结果应与无观察器版本分开归档。

本轮整包要求包括9条文档坏例、重点重复回放、20配置接收初始化和80张初始图、代表完整接收回放、普通服务独立启动、受控银镜/计时/重置及几何评分反例。测试方法通过、文件闭包通过、运行完成、任务成功、视觉检查分别陈述。

## 本轮已定位的操作问题

浴水原表面距离8mm与网格间距2.91mm不满足本机 Isaac 4.1 schema 的 `surfaceDistance < 2.5 * gridSpacing`；改为3.3mm网格纠正范围问题，但单改仍出现CUDA700。扩大网格容量的试验也失败，因此不能把这两个改动写成已证实的崩溃根因修复。当前组合候选及资格以制作根清单为准，历史失败保留。

无机器人演示曾灰屏。短对照中，相机绑定和2034个USD变换一致，隐藏液体、刷新相机或可见性均未恢复；仅在制作进程内给Gprim写入语义标签后RGB恢复，且已完成对应完整演示。标签不保存进交付USD，不改变物理步、刚体或粒子；该初始化经验仅适用于记录中的演示工具/运行环境，不提升为通用渲染规则。

普通无窗口启动有一条已单独验证的 GLInterop 缺窗口消息。验证工具如允许它继续，必须保留原消息和匹配范围；不泛化为忽略 `[Error]`，PhysX/CUDA错误仍阻止交付。

## 安装与回退

`provisional_v8` 只作待验收材料，即使 ZIP 和563个文件哈希一致也不代表可交付。最终发布必须有对应冻结版本的验收报告、离线文件、metric代码交付、视频、SHA256SUMS及回退说明。

制作根 `tools/install_receiver_v8_guarded.py` 默认只读；执行路径要求最终验收证据和清单哈希、接收Git状态一致。安装仅替换三棵Task18树及metric，保存原树、原metric、分支/工作树状态与逐目录事务回执，检查称量、滴定、水浴及其他受保护文件。只从离线清单暂存，不整树复制运行后产生的缓存。

metric bundle 广告引用是 HEAD；bundle 与mbox为替代方式，不重复应用。当前代码提交为 `f0dedfb29b2561e7f92bc4371fdcae43af555acd`，父提交为 `9490df9a3710bbcea97cd2470adc364a13883914`；实际安装前重新检查，不假定接收仓库未变化。

安装后仍须普通入口冒烟、哈希及其他任务保护复核，才写 READY 并同步飞书和仓库入口。中断时依据事务回执恢复本任务树和metric，保留失败版本；不使用全仓库 `reset --hard`、全局停止进程或覆盖其他任务。
