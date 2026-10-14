# 水浴原版成功复现前置与38次最终回归

状态：执行中；新版物理调参及正式交付阻塞，称量渲染继续。

## 已确认的执行决定

用户要求持续修到有效旧成功恢复，不设修复轮数，不以重采替代解决退化。
19组历史1分来源以建通repo原USD和动作记录为准，先核对复现链路，不以尚未确认历史版本为由排除案例。
旧版成功复现是继续新版物理调参的前置：mixed5至少两次独立成功，其他代表差异查清。
最终同一修复版本19组各独立运行两次，38次均score=1/success_rate=1；失败不能用挑选成功尝试覆盖。
其后还须坏例、规则、视频和仅允许交付项的干净安装验收。
120Hz、7000步、原动作值/顺序及碰壁等停热条件保持；水浴LeRobot本轮不做。

## 来源与最新结果

工作根R：`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/task12_liquid_color_20261012`。
mixed5汇总目录的manifest指向建通原始`single/sft14260926_t12_m05`目录，
meta_record.pkl与result_info.json逐字节相同，原记录明确score=1/success_rate=1。
对应原YAML指向task12的unseen_scene_5/scene，120Hz、7000步、warmup300。

三组旧/新计时配对全部完成，原生倍率旧2/新1。
仅将当前可获取旧YAML恢复的mixed5控制也已结束：7000步、score=.5，maxheat36.483335秒、
progress .945942，无引擎错误。它与共用新版YAML的旧侧得分相同，不能据此声称原资产只能得.5。
刚体偏移候选三次冷态和一次升降通过，仅支持限定夹具范围。
既有时间候选与接触候选队列以KeyboardInterrupt记录结束，未完成代表回放，不能当作失败的任务得分或通过。

## 原版校准执行

`evidence/pristine_old_baseline_identity.json`绑定新的个人工作树，637个任务配置、USD、task data和task12 metric
均与建通目录逐项哈希一致。未追加诊断观察器。核心基于0e99ea01；与建通当前核心比较，差异仅在
另两项scientific metric文件，不涉及task12核心执行。共享repair_checks只供既有launcher清单读取，原task12 metric不导入它。
机器人与公共材质仍引用建通只读资源，正式交付独立安装另行验收。

首条无观察器回放run ID为`task12_pristine_original_h00_a_20261014T060401_277381Z`，
状态`evidence/pristine_original_h00_a_run.json`；原动作值/顺序逐帧核验，完整日志、视频审计与状态差异保留。
不在原场景附加时钟仪表，因此只声明配置120Hz，不把缺少独立计时记录写成实测认证。

之前旧配置回放与历史观察比对显示：手臂首个>1e-5差异约2867帧，夹爪首个>1mm差异2908帧，
底座首个>1mm差异4851帧。更小差异已在之前出现，这些阈值不是因果起点。
2800/2920帧同机位画面可比，试管位于架上方/靠近夹爪，细小姿态差异可见，遮挡不能证明准确接触或插架。
本次目视由实现者完成，非独立审查。证据`evidence/original_baseline_divergence_audit.json`。

## 门禁与恢复

`evidence/original_success_gate.json`当前BLOCKED_PENDING_PRISTINE_OLD_SUCCESS。
辅助工具original_success_gate要求两条不同run ID的mixed5完整成功、动作一致及目视通过，并要求其他代表差异解决。
待确认运行报告后才能填写通过，不把状态字符串本身当运行证据。
时间作者/回放、偏移限定队列和接触候选入口均调用此前置；4项单测通过，覆盖未决、空通过、重复run和独立通过。

旧finalize_coarse_phase1_release已明确停用：其首轮“成功示范待重采”描述和冻结粗粒版本不满足新要求。
最终封包必须基于新安装清单、38次同版本成功、重新验证的坏例和规则证据；不能仅解锁旧发布脚本。

涉及STATE-001/002/007及VAL-001/002/003/004。通用规范无需变更：本次是任务验收强化、
原版来源与复现诊断，没有改变核心package/schema/API。同步operations恢复顺序；未执行完整make check，
此前仓库测试基线不能冒充此次重新运行。
