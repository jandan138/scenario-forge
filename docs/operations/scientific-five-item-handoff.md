# 四项科学实验修复：受限交付操作记录


当前验收补充：完整 server stdout 与 worker 日志都必须检查，含回调注册前的启动和
初始化；参见 VAL-001 与任务记录 `full-engine-log-coverage`。旧 worker-only PASS
不代表全程无错。滴定封包两次运行追加全日志复核均 0 错误、0 碰撞降级，封包字节不变。
称量 default_offsets 候选两次 reset 正常且完整日志无错，批准的慢倒完整4000步/0.5分，视频确认三粒留舟、两粒入瓶，未成功；
只有 full score=1/sr=1、原生120、全日志、四视频与标准 reader 通过才生成成功交付数据。
其训练入口尚未推广，不能直接复制候选根。水浴/银镜容量和 PGS 完整对照均失败，仍未放行。

已交付（16:42 UTC）：task10单独包位于
`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/delivery_releases/task10_standalone_r1_20261011T162354Z/`。
状态RELEASED_TASK10_ONLY，安装说明见包内README；仅安装五类内容，标准原版回放1582步满分，
原生120Hz，四视频和LeRobot v2.1验收完成。metric提交38425dc6eb18fba6560184745acf27fe91241e10。
建通目录未写入，生产/测试脚本不安装。称量及水浴/银镜继续，其他旧候选的通过/失败只保留
对应历史范围；尤其rim v2完整坏例引擎失败，不得将旧测试gate或局部PASS用于交付。


最新状态（16:30 UTC）：用户选择滴定先单独交付，其余继续。task10_standalone_r1归档
及独立安装静态检查完成，最后原版正例运行中，发布以RELEASE_MANIFEST为准。
rim v2完整bad11先遇接触缓存溢出；只改两项YAML缓存后仍CUDA700，14例测试gate已撤销。
称量仍缺稳定初始化及新成功示范，诊断脚本/观察器不进入任何交付。以下旧状态为历史过程。


当前状态（15:44 UTC）：两批均未发布。task10已独立安装成功；task09授权慢倒示范因
动作前左夹指异常得0.3，尚无新成功数据。四初始驱动目标候选不足以稳定重置，正在
原core/原robot的短reset诊断中；只读观察器及生产工具不得交付。`task09_task10_r1`
仍为NOT_RELEASED，不能用旧成功证据封包。
第二批rim_v2_candidate_runtime已通过限定生产者资格与bad11=1800/bad08=3200两短窗口，
完整14条7000步坏例于16:03:52启动，首条bad11；状态查rim_v2_full_badcase_queue.json。
同字节夹爪正常/异常对照均未见DriveAPI意外添加，重解析试验不构成修复证据。
此段为当前状态，下文保留历史过程，旧gate不可复用。
详见同日验收记录15:44节和工作根CURRENT_STATUS.json。


当前按用户确认分两批，但第一批尚不能发布：独立安装滴定1582步满分，称量4000步仅0.3分，初始左第二夹指停在0.044m，正在原版短启动对照。归档已标 `NOT_RELEASED_TASK09_CLEAN_INSTALL_FAILED`，不得部署。第二批 task12/银镜也仍未合格；口沿分区v1被发现漏写Physx schema，退化为凸包，此前drop/rack数值不再被当作预期SDF方案资格，v2重新验证。所有历史中途通过均不能替代最终资格。
旧归档与名含 `final` 的实验目录都不代表最终资格。最新决定及证据限制见[任务记录](../records/2026-10-11-scientific-five-item-acceptance.md)。

工作根为 `/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010`。
第一批唯一构建身份看 `evidence/batch1_build_identity.json`，归档位于
`delivery_releases/task09_task10_r1_20261011T131822Z`。在该目录最终发布状态完成前，
`BUILD_STATUS.json` 仅代表构建/安装进度。独立验证目录 `batch1_receiver_runtime` 从
归档安装，没有复制实验 mesh cache；完整运行仍使用原始服务与原始 LMDB 客户端。
第一批 metric 为 `7900236d09f18472f370569936a9389298368230`，仅称量、滴定及公共
`repair_checks.py` 三个文件。不能使用下文历史四任务 patch 代替这个子集。

以下主 checkout 与四任务候选描述用于追溯历史，不能整目录发给接收方。
其中 `baseline_runtime` 是以原版 GenManip 为底座的验收 checkout。自己的主 checkout
已切至 `delivery/scientific-five-items-20261011`，同样为原版core加允许的metric提交，
并同步四任务当前候选；3172个候选文件哈希与验收目录一致。588个非允许范围的原版
Git blob（587个普通文件和1个原始软链接）保持原内容。旧core实验保留在
`experiment/scientific-repair-runtime-hooks-20261010` 历史分支，旧资产/data另存工作根
`experimental_main_payload_snapshot/20261010T185138Z`。候选仍有未通过项，不能
把整个主 checkout（含本方工具和实验记录）作为交付包。

## 允许交付的内容

| 类别 | 接收仓库内的相对路径或形式 |
|---|---|
| task config YAML | `configs/tasks/scientific_experiments/` |
| USD及其资产依赖 | `saved/assets/scene_usds/scientific_experiments/` |
| task data | `saved/tasks/scientific_experiments/` |
| metric代码 | `genmanip/extensions/metrics/scientific_experiments/`，单独代码提交 |
| LeRobot | 完整数据集目录，包含 metadata、Parquet、视频 |

生产、转换、验证辅助脚本保存在工作根的 `five_item_tools` 等目录，不作为接收方运行依赖。
当前部署与验收只在朱子厚目录进行；没有向陈建同目录写入，也没有推送或改飞书文档。

metric提交为 `9d85d222e213d34bda43e8834266e4fff401ce56`，父提交为原版
`0e99ea01eec7780e53fa2ce3ecb0fce1a6b4500a`。它只改允许metric目录中的5个文件。
工作根的 `metric-only-9d85d222.patch` 是同一提交的补丁；原版core未列入该提交。
具体文件清单与补丁SHA见 `evidence/metric_only_commit.json`。

## 运行与数据含义

运行目标为 Isaac4.1、原生120Hz。USD自行携带任务控制和必要SDK初始化；metadata通过
原版已支持的属性恢复接口工作，不依赖新增core helper。

滴定的 `titration:initial_points`、初始速度、重置标记和epoch由metadata恢复，再由USD
控制器统一恢复粒子点、速度、宽度、ID和质量。该任务不同时启用通用
`initial_particle_states` 恢复：限定对照中，重复恢复导致接收量异常，控制器单独恢复
则在释放5.454mL时全部接收、零洒出。完整原版机器人回放仍作为最终门槛，不能用此
无机器人对照替代。

滴定动作的120Hz转换保留原LMDB及转换记录。为帧数兼容而重复的原观测不是新采的训练
观测；训练数据来自实际物理状态捕获与对应离线渲染。原生评测视频编码30fps，查看
动作时以帧号定位；LeRobot候选按真实捕获频率标为120fps，不混用两种播放时间。

用户已确认LeRobot沿用v2.1格式，并注明验证环境。独立RGB导出工具修复BGR/RGB顺序，最终
数据集不导入或调用该工具。旧的非RGB候选已标记 `NOT_QUALIFIED`，不作为交付。
生产机旧LeRobot与datasets4.5不兼容；隔离验证使用未修改的LeRobot0.1、datasets3.6、torch2.10、av16.1及pyav，
未改写原环境。导出文件中11个固定float32向量的Hugging Face描述由新`List`规范化为
v2.1兼容的`Sequence`，所有Arrow数值和视频字节不变。称量3372帧、滴定1582帧均已
通过未修改读取器的首/中/尾帧读取。本轮按现有v2.1格式交付；兼容性证据限于上述
未修改读取器环境，其他接收训练环境尚未验证。

标准候选目录为工作根 `lerobot/final_candidates/task09_native120_v21` 与
`task10_native120_v21`。两者均已有首轮单示范资格记录 `QUALIFICATION.json`。
滴定训练源在最终USD和未修改原客户端/core上1582步满分通过，评测源1574步满分通过；
机器人状态差异保留在证据中，不能套用称量的逐位一致结论。仅覆盖各一条示范。

## 验收与已接受的待补项

称量原版关键回放 `five_item_task09_sdk_graph_20261010T164048_441466Z` 已取得1.0分、
成功率1、3372步；原始4000步上限不变。四路视频完整解码通过，实现者查看了四路
关键帧，总览和右相机可见末帧4.56g；顶部裁切与腕视角遮挡记录为WARN。没有独立审查，
也不宣称逐帧目视检查。

用户允许水浴和银镜在首轮明确写“完整成功示范待重采”，先交资产修复和真实坏例结果。
不得为其合成成功轨迹或将初始化片段当成成功训练样本。此决定不免除原版可运行、
资产有效性和坏例证据要求。

验收目标是文档全部18条坏例按原动作顺序回放。当前冻结称量/滴定的4条已完成，
记录输入SHA仍一致；历史上8条有完整结果，但不能把不同水浴/银镜候选的结果合并
成最终版本验收。使用工作根 `evidence/current_bad_case_acceptance_v2.json` 查阅
明确选择的证据；旧的非版本绑定汇总不作为交付依据。

水浴/银镜此前多个连续碰撞候选在机器人共同接触时出现CUDA失败，全部保留。
floor8/noCCD/table9mm组合曾通过本地前缀，但原core286条记录后CUDA失败，另有
提拉1粒出界，已拒绝，原报告保留。当前回到原杯SDF与tube617，仅原桌面contactOffset
设17mm、两body sweep/speculative CCD关闭；容器/加热器/PBD offsets、restOffset、
质量和动作不变。17mm依据倾倒时管口单步15.124mm下移，不是通用参数。

新 `table17_validation_runtime` 的40入口静态通过并冻结1320个输入文件；本地50mm
落碰482tick、严格300实际物理步预热+700动作、指尖几何/同帧接触计数均通过。
原版首例 `five_item_bad_17_table17_20261011T005347_628509Z` 已完成7000步，score0.15、
成功率0，四视频解码及关键帧目视审查完成；两任务最终保液/门控和限定5mm落座也通过。
10组生产者证据与1320文件SHA核对后曾放行队列；bad17、6、4、5、7完整7000步，
四视频/native120/关键帧审查完成。但bad08（task12 mixed5）在2916条记录后CUDA失败，
没有完整结果；队列已停止，测试gate另有revocation记录，当前禁止交付。局部夹具
通过和五条完整回放不能覆盖该失败；后续将按新证据修复并重新绑定验收。
最新状态查工作根 `CURRENT_STATUS.json`；进度工具同步读取worker物理错误，仍不能
替代完整结果与视频审查。

本方各个 `*_validation_runtime` 都是有版本区分的隔离诊断checkout；目录中的
`final`、`shared`、`speculative` 等词不是资格标记。`baseline_runtime` 和本人主checkout
仍包含未合格的水浴/银镜旧候选，不能直接复制整个目录交付。

自动检查覆盖结果、视频完整解码、原生时钟日志
及物理错误，画面仍需另行查看。周期时钟日志不保证包含最终计数快照，其限制应保留。
坏例任务未成功与基础设施异常分别记录，不能用零分替代没有完成的运行。

工作根 `delivery_candidates/20261010T193046Z` 已有五类候选归档及逐文件/归档哈希，
3188个离线覆盖文件、metric补丁、称量/滴定各一份LeRobot数据。tar成员哈希与gzip
CRC/长度完整验证通过；当前状态已更新为 `CANDIDATE_WITH_UNRESOLVED_WATERBATH_PHYSICS`，保留在本人目录，
尚未完成其余水浴/银镜坏例验收，不用于覆盖接收仓库。

最终打包前核对：五类路径白名单；无包外资产引用/逃逸软链接；哈希绑定最终内容；
原始140个评测goal的阶段结构和权重不变；20环境映射保留；每项待补与已通过范围清楚。
当前证据见工作根 `evidence`、`baseline_runs` 与 `audits`，不能仅凭目录名含`final`
或进程退出码0判断可交付。

USD依赖扫描与MDL字面资源检查需分开解释：80个入口的USD依赖无缺失；原始MDL中
2568处可选材质浏览器缩略图注解指向未附带的`.thumbs`文件，未发现缺失的运行时贴图
字面引用或目录外贴图路径。此限制不能写成“所有浏览器缩略图完整”。

规范依据为 ASSET-002/003、STATE-002/003/005、VAL-001/002/003/004/005；没有新增通用
物理参数或包契约。运行器、辅助导出代码及大型场景/视频不进入Scenario Forge核心层。


追加诊断：solidcap_trace_runtime 使用底部实心玻璃重划分和只读traceV2，
运行ID见CURRENT_STATUS.json。其3200动作上限与robot report wrapper只用于定位，
不得进入五项最终覆盖包或冒充原机器人完整7000步验收。旧table17 gate保持撤销。
水浴与银镜首轮都允许注明成功示范/训练数据待重采；仍分别保留资产资格与坏例证据。

solidcap短诊断3200完成无引擎错误，原robot完整7000 bad08另行运行；但是新cap
Fehling lift有1粒底部越界，producer夹具队列已停止。故solidcap同样尚不可交付，
不能从短诊断成功或静态40入口通过推断保液资格。当前没有新整批测试放行gate。


隔离的水浴/银镜runtime只含这两项资产与taskdata，虽然Git配置树含其他任务，
不能直接作为四任务完整交付根。inventory与archive builder均检查四任务三类离线树
及每任务20个入口；完整性测试见evidence/inventory_completeness_guard_test.json。
20261011T053555Z草稿来自局部runtime，已标INVALID_PARTIAL_RUNTIME_NOT_DELIVERY_INVENTORY，
没有打包。最终使用合格两任务覆盖到保留09/10冻结内容的完整基线后再生成清单。


PBD作者128试验有场景上限限制：当前pbd128_validation_runtime的YAML Min/Max64，
不能称有效128。该原core单例已主动停止并保留invalid_attempt，生产者局部PASS不能
解释为128次求解已生效。后续需scene上限与实际个体请求一同核对，禁止据此发布gate。

用户已确认首轮水浴/银镜保持原7000步，称量保持4000步；重采时再调整时间预算。
120Hz下7000步=58.333秒，部分场景仅加热约59–60秒，未计抓取/观察/回架，
因此首轮坏例保持同预算对照，不能把所有任务未成功都归因于策略。决定与来源见
工作根evidence/first_round_time_budget_user_decision.json及waterbath_time_budget_review.json。


最新测试队列：scene128_validation_runtime固定1325个输入（含原robot仅用于验证），
evidence/scene128_badcase_gate.json只放行剩余13条原版坏例，不是最终交付。
首条bad08为five_item_bad_08_scene128_20261011T060030_512029Z，7000/.15/sr0/client0，
四视频解码/native120/人工抽帧完成。末管水平落在架旁桌面，失败归槽如实记录。
队列状态为evidence/scene128_queue_state.json，顺序17,9,10,11,12,13,14,15,16,6,4,5,7；
若引擎错误或结果不完整即停止，旧table17测试放行已撤销，不复用。
生产者receipt为ConvertAsset输出silver_bad17_diagnostic/recovery_scene128_scoped_qualification.json，
SHA670ebb0477ebc5888c3626fbc7239bc5f5ea56b99b6ba0f50e93e80f0a711792；仅限定姿态/动作资格。


队列续跑更新：bad17曾出现PBDinvalid，经原版前段视频确认杯被动作碰倒、从开口大量
洒液；正确停止加热，按真实坏例保留，没有据此改资产。旧队列在17后暂停的记录保留，
同冻结版以scene128_r1继续余12例9,10,11,12,13,14,15,16,6,4,5,7。
当前状态改查evidence/scene128_r1_queue_state.json；两条已完成的新版本结果为08和17。


最新阻塞：bad11 run five_item_bad_11_scene128_r1_20261011T103212_811754Z，
10:38:43首mArtiSolveBlockPartitionFunction/CUDA700，1574条记录后client1/noresult。
scene128_r1队列停止，scene128_badcase_gate_revocation.json已撤销放行，四条完整结果仅保留
历史证据，不提升为全局合格。目前仅bad11_trace_runtime内1800动作只读接触诊断在跑，
run见CURRENT_STATUS.json；独立robot报告包装不交付、不改共享源或GenManip核心。


新方向仅处于短窗口验证：sdf_candidate_runtime保留完整配置，使用源GlassShell作为
唯一tube rigid碰撞、473代理仅PBD，修正SDF比例单位。sdf_probe_runtime是共享资产
的诊断入口，仅bad11=1800/bad08=3200，不可交付。bad11短窗口已通过并确认实际杯内
松管，bad08正在验证；尚无新最终资格或新全量坏例放行。
