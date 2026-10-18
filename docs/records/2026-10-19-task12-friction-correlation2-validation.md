# 水浴2mm摩擦接触点合并距离验证

状态：A轮0.85分、回架失败；B轮1分、显色与回架选帧复核通过；C轮运行中。水浴仍NOT_RELEASED，2mm候选尚未证明稳定性。当前监督PID126500，权威队列为远端 `/tmp/task12_correlation2_20261018/queue_resume_logfix.json`；运行状态必须结合实际进程复查。

## 假设和冻结边界

继承[32/64对照与接触诊断](2026-10-19-task12-iteration32-64-comparison.md)：两种上限均一成两败；同参数私有成功/失败在碰架前已有明显管内夹持相对转动，不能归因唯一参数。运行时FrictionCorrelationDistance=25mm，接触点跨度数据仅构成缩小合并距离的待检验假设，不证明实际patch结构或修复效果。

候选由个人repair目录`evidence/contact_correlation2_identity.json`定位，SHA为`93c35a80900b45318460ec721aaae45a792417b1a4c2fbd2d7a682b3c1fcf167`。51份YAML／102组配置只新增FrictionCorrelationDistance=0.002，20实际场景入口、USD、task data、metric、原动作与32基准相同。保持120Hz、min1/max32、摩擦系数2.5及7000步cap，不增加USD诊断读回，不改GenManip核心。

## 原生验证

使用已通过旧包校准的同一主机10.150.165.46，hostname `dsw-529861-6cb4cb97bf-l8495`，GPU `GPU-420b26cd-ec84-8748-1f98-62a728c069c4`；本轮预检GPU空闲、本地盘约207GB余量。先做代表来源13三次独立冷启动，保留原3722帧命令及既定尾帧保持。任务失败保留并继续固定三次；时钟、输入、引擎或基础设施异常停止并定位。

最初队列为远端`/tmp/task12_correlation2_20261018/queue.json`（现保留停止记录，恢复入口见下文），共享镜像`evidence/contact_correlation2_queue.json`，启动监督PID115984。必须检查进程/心跳和原生输出，不凭本文PID声称仍运行。日志、视频、输入快照、审核图片和状态先写远端本地盘，再归档到个人证据目录并校验SHA；不覆盖历史结果。

审计要求原生启动日志确实出现`GetFrictionCorrelationDistanceAttr().Set(0.002)`，同时核对实际120Hz时钟、原命令、有限机器人状态和四路视频完整性。每轮实际查看显色、回架、松爪后终态；抽帧准备不算目视通过。三次均score1/success_rate1且画面通过，才进入后续保液和代表来源/独立安装验收。无读回回放不宣称逐粒95%保留率，私有读回证据也不直接冒充清洁版本实测。

## 维护说明

辅助工具仍在个人repair目录，不成为接收方运行依赖。规范依据MAT-003与VAL-001/002/003/004/005/008；本轮没有新包/schema/API契约或已验证通用参数，规范无需变更。当前只是受控参数验证，不是扩大任务成功定义或选择性保留成功回放。


## 日志审计恢复

第一轮 `contact_correlation2_a_20261018T194329_035108Z` 原生完成7000步，得分0.85、成功率0。监督器重复的原始 `[ERROR]` 字符串检查误把框架包装的 tqdm 进度条判为异常。移除这条重复检查，继续使用经过7项测试的严格日志分类器，并保留配置生效、动作、时钟和视频审计。没有修改GenManip或重新仿真A轮。恢复监督PID126500，权威状态改为 `/tmp/task12_correlation2_20261018/queue_resume_logfix.json`；原停止记录保留。A轮复核后继续B/C，当前仍不具备交付资格。


A轮主代理已实际查看原生top/overlook选帧：1000帧蓝色、2000帧黄色、3000帧橙色，正常机位可辨识样液；3700帧试管倾斜，3750/3782及7000帧倾倒于架子边，回架未通过。哈希与范围记录于 `evidence/contact_correlation2_a_visual_review.json`。不以选帧推断逐粒保留率或逐帧碰撞。B轮已启动，当前不采用该候选；准备300步原命令前缀的私有摩擦锚点读回副本以支持下一步因果定位，不属于成功示范或交付依赖。


摩擦锚点诊断准备完成：baseline/corr2两个私有300步副本均通过静态来源哈希与USD非脚本属性一致性检查，身份见 `anchor_probe_baseline_identity.json` / `anchor_probe_corr2_identity.json`。新增纯Python锚点汇总和已对齐轨迹分析器，序列化/汇总8项测试通过；分析要求输入trace哈希绑定已有原生状态对齐报告。报告只给每个接触header的锚点跨度及冲量，不推断未暴露的patch ID、摩擦容量或完整回架资格。尚未占用GPU执行这两个诊断，等待当前B/C清洁回放释放设备。无新的已验证物理规则，不修改通用标准。

诊断顺序脚本 `run_anchor_probe_queue.py` 已准备但未启动：必须前序三次清洁回放完整结束、GPU/端口空闲且取得共享锁，才顺序运行两个300步测试；强制核对300步原命令、有限状态、实际时间步、日志、原生对齐及视频，归档后再次校验输入哈希。后续入口准备不等同于运行结果。

已启动一次性后续等待进程130284，绑定当前清洁监督器126500及其/proc启动时间；只有原监督器退出且三轮完成状态满足后才启动锚点诊断，不重启上游或异常任务。状态 `/tmp/task12_anchor_inspection_20261018/chain.json`。A轮原生机器人状态与原记录比较见 `contact_correlation2_a_robot_reference_comparison.json`：3723个共同时刻，手臂最大绝对角差约0.002353rad，第3500帧约0.000199rad；不据此声称试管位姿一致，因为清洁meta未记录试管位姿。

B轮原生worker于2026-10-18 20:25:44 UTC报告 `Goal reached consistently`、3782步、info1.0；此时正式result_info和视频仍在保存，暂记 `contact_correlation2_b_native_pending.json`，不是完整验收。与A轮失败并存，候选仍未通过稳定性要求。

B轮正式结果为score1/success_rate1/3782步；主代理查看蓝/黄/橙显色选帧和回架选帧，并补查原分辨率末帧。左腕机位可见试管穿入架孔，松爪后手已离开，未呈A轮横倒状态。证据 `contact_correlation2_b_visual_review.json` 与 `contact_correlation2_b_terminal_views/`。该轮通过不消除A轮失败，仍不可宣称稳定交付。
