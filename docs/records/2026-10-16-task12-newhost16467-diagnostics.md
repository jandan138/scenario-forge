# 水浴新远端接管：环境对齐与同步/抓持诊断

日期：2026-10-16。状态：新机旧包基线执行中，未取得新机任务资格；以外部run和queue记录为准。

## 已完成的配对结论

上一批新增六次运行均已结束。计入绑定过输入、主机和执行协议的两条历史记录：原诊断包有观察器两次1分、无观察器两次0.85分；RC1有观察器一次1分一次0.85分、无观察器两次0.85分。不能将一次满分提升为交付资格，也不能据此把观察器认定为唯一原因。

RC1有观察器的成功/失败两条，在frame128试管相对夹爪位置差超过1mm，frame176超过5mm，frame3480超过10mm。失败回放显色完成；frame3474首次单粒管口相容退出，frame3756保留率低于95%，此时试管已接近横倒。正式episode末样液保留34.0195%，浴水100%；611个退出记录均分类为mouth_compatible，分类不能替代逐事件几何认证。抽看终态画面可见回架失败。大量失液发生在倾倒后，抓持与回架应和液体保留分开诊断。

**更正此前“只读观察器”的笼统称呼：**v10每步调用`update_transformations(False,True,True)`，主动将物理变换及速度同步到USD。它不施加力或写控制目标，但不是纯读取；这个同步是否影响实际抓持、任务读取或显示尚未实验证明。此前关于无solver/位姿控制setter的描述不能当作非干扰证明。接口语义见[NVIDIA文档](https://docs.omniverse.nvidia.com/kit/docs/omni_physics/108.0/extensions/runtime/source/omni.physx/docs/api/python.html)。

## 机器与环境

新机内网`10.150.164.67:22`，公网备用`123.57.187.96:885`；实例`dsw-536338-6789668565-59thj`，GPU UUID `GPU-62efc194-08b4-e378-187a-ee993cc7d832`，驱动570.153.02。首次检查GPU及8087空闲。

Isaac为`4.1.0-rc.7+4.1.14801.71533b68.gl`。与旧机比较：Python/主要依赖版本、cuRobo提交`2fbffc35225398cf9d5f382804faa9de2608753b`、Isaac启动脚本与kit入口哈希、已检查PhysX扩展配置哈希一致；这不等同于整个SDK逐字节相同。共享RC1身份SHA为`d7fd6d4a48424489b3fe56af1beb7c8fc436d56d5be9f802804eaf5fdf8632fa`，两机一致。

唯一已修改的安装项是新机客户端：原0.1.2绑定`/root/GenManip-Sim`，已以`--no-deps --no-build-isolation`改为共享仓库中的0.2.0。修改前后freeze只显示该editable客户端变化；导入路径已确认。原安装文件、清单、恢复命令和安装日志位于证据根的`newhost_16467_environment/`。未升级其他包、未改SDK或GenManip核心。

本机先前的4.1尝试停在初始化错误，八个短测未运行；用户已决定不继续本机环境排障。新机使用原生`/isaac-sim/python.sh`与`/root/miniconda3/envs/client/bin/python`，不使用本机私有依赖。旧远端`10.150.163.175`的称量独立运行，本次未停止或改动其环境。

## 新机执行与门槛

先在独立工作树重放旧包来源13，保持120Hz、原动作、chunk30及既有底座语义。标签`task12_newhost16467_old_h13_a`；首次监督PID32226，状态以receipt为准。要求score1、success_rate1、已执行动作一致、机器人状态最大误差不超过1e-5，原生日志和四路视频检查通过后才允许短诊断。视频解码通过不替代视觉审查或最终交付。

随后四组前300步短测各两次：无观察器、完整观察器、仅删除显式USD同步、仅保留同阶段同步。保留液体/接触参数、初始化和动作；短测只改evaluation步数上限及声明的观察器内容。原本为本机准备但未运行的八个冻结副本重新绑定新主机，逐文件哈希核验；目录/trace中的local41保留准备出处，不表示本机执行。每次使用新机专属run ID，原记录不覆盖。

full和nosync组从live刚体/关节读取对齐抓取阶段；nosync的USD粒子位置新鲜度未证明，不能用于宣称逐粒保液合格。none和synconly组保留原生机器人记录及视频，不能悄悄装回完整观察器。短测过程分不构成任务成功或失败结论。

外部根：`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/task12_liquid_color_20261012`。入口身份`evidence/newhost_16467_old_baseline_identity.json`；新机监督工具`tools/run_newhost16467_baseline.py`、`run_newhost16467_probe.py`、`run_newhost16467_probe_queue.py`；队列状态`evidence/newhost16467_probe_queue.json`。工具锁定新实例主机名，防止误在旧机抢占GPU。基线/基础设施失败停止，短测不自动晋升为交付资格。

交付边界保持YAML、USD及依赖、task data、指定metric；metric只评分，辅助诊断不成为接收方依赖。水浴LeRobot延期。规范依据VAL-001/002/003/004/008、MAT-001/003、STATE-001/002及维护流程；规范无需变更：本轮为任务特定迁机校准和观察器非干扰性诊断，没有新的通用物理默认或包/API契约变化。操作说明同步；历史证据保留原范围。

## 启动阶段误停更正

新机a尝试已到Scene.initialize完成，但新增监督判断将重定向到`[ERROR]`日志级别的stderr进度条误判为引擎故障，未开始正常动作回放就被停止。完整复核该worker日志没有发现分类后的真实错误候选；不将此尝试记为任务失败或引擎不兼容。`newhost16467_baseline_progress_log_review.json`保留原日志与更正结论。

本机c尝试复核也存在同一误停，因此之前“本机仍有初始化错误”的描述不能据此推断环境不可运行；本机a/b缺失cuRobo/yourdfpy的异常是真实存在的。遵循用户后续安排，本机继续停止，不另行重试。

已将任务私有监督改为识别格式严格匹配的tqdm进度条，真实`[Error]`、Traceback、CUDA错误和非进度内容仍报错；空白未完成记录在流式读取时等待后续，最终审计仍检查。七项回归覆盖多行/单行进度条、真实模块错误、PhysX错误、混合错误文本、截断记录及未知后续文本，均通过。未修改GenManip的日志重定向或SDK。

新机b以新ID重试，监督PID35029；基线门控的八次短测队列PID35030，尚需旧包结果/动作/状态和视频审计通过才会接续。具体状态以`newhost16467_probe_queue.json`与本次receipt为准。已消耗本轮已计划的基础设施修复后重试；若仍无法通过基线，停止短测并保留证据，使用旧机空闲后的后备安排。
