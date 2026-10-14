# 水浴旧成功回归：计时与抓取分离诊断

状态：诊断运行中；交付仍被有效旧成功回归门槛阻塞。

## 用户决定与现状

19组首轮筛查全部完成：17组.15、2组.3，均未成功；六次坏例原版回放也全部完成。
细分metric确认.15仅获取出分，.3另获回架分，19组均未获显色50%/95%分。
用户确认原操作节奏优先，必要时允许统一调整反应时长、低于原文30–60秒，并明确记录任务定义变化。
仍保持原生120Hz、每物理步只计一次、7000步；原文倾斜/偏心/碰壁停止加热及真实回架要求不删除。
不按每条轨迹拟合时长，不改动作或评分阈值。称量生产保持运行；本轮未改正式候选。

工作根R：`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/task12_liquid_color_20261012`。
新连接`root@10.150.163.77:22`（公网919备用）；已恢复公钥授权。
新主机`dsw-529861-5584fffbd6-q9tpr`，GPU `GPU-0bf4ccdc-c995-41e7-1e2a-59ed12c937c6`。
旧GPU/旧主机运行证据仍保留，不把身份变化当相同机器重复试验。

## 三对诊断

代表为catalog索引0（GPT mixed5）、15（旧60000 unseen_instruction4）、13（40000 unseen_prospect10液体无效）。
创建两个独立原版core工作树：当前可获取旧USD/taskdata/metric，与冻结新版USD/taskdata/metric。
两边共用冻结新版YAML的120Hz、7000步、TGS、64–128迭代、128MiB容量及机器人摩擦；
三例对应的初态五阶段反应时间数组逐一相同。
当前可获取旧资产/metadata未证明是9月26日精确快照，不声称完全历史复现。

诊断目录：`R/clock_diagnostics_20261014T023450Z`，身份`evidence/clock_diagnostics_identity.json`。
原脚本只追加观测器，记录原生物理回调、每步compute调用次数、deltaSeconds、实际加热增量、
显色进度、停止原因、实际刚体位姿及旧静态水面条件的旁路判断。旁路不控制任务，不写回位姿或粒子。
静态试管架没有RigidBodyAPI，按静态USD姿态记录，不向dynamic_control请求不存在的刚体。

辅助工具位于R/tools：`task12_clock_observer_fragment.py`、`prepare_clock_diagnostics.py`、
`run_clock_diagnostic_case.py`、`run_clock_diagnostic_queue.py`。不进入接收方依赖。
观测器单测通过：同一物理步三次原compute调用均完整保留，时间输入/结果不变，未偷偷去重。
队列首条为旧mixed5，随后新版mixed5，再旧/新15与旧/新13；首错停止。诊断成功不自动触发发布。

## 已得到的部分运行证据

旧mixed5进入水浴后，连续229个有效加热物理步测得加热增量/真实物理dt约2；
稍后只读快照扩展到1073个2倍步，另1个接触边界步约1倍。每次输入deltaSeconds为1/120，
同一原生步发生两次compute调用，两次均推进了加热。该证据来自实际累计，不是用低分反推倍率。
`old_available_00_partial_multiplier.json`及JSONL保留取证时点；仍待完整运行与三个新版对照。
这仅支持当前可获取旧场景在本诊断配置下重复累计，不唯一解释全部历史掉分。

计时v2草案把`fehlings:timing_seconds`定义为有效仿真秒，另存reference_timing_seconds和统一reaction_time_scale，
并显式迁移timing_version=2。实际heated_seconds继续累计真实物理秒。
5项单测通过：参考/有效时间分离、拒绝静默解释v1、拒绝逐案例任意缩短、重新随机化保持统一映射、
调用实际appearance证明统一0.5时长映射保留原五阶段外观曲线。
`prepare_timing_v2_candidate.py`仅已准备，未执行：必须六次诊断完整通过、三组旧/新倍率中位数均为2/1，
才允许产生统一0.5的计时候选；物理/材质/动作/YAML/metric不随之改变。

## 抓取静态差异（尚非因果证明）

ConvertAsset只读审计确认试管根质量18.008921g、COM/惯量、可见GlassShell网格相同；
新增真实样液的整体动力学影响不能据根质量相同而排除。机器人摩擦配置两边相同。
旧刚体碰撞为整管SDF，contact/rest为10/1mm；新版为LowerSDF加24个rim，contact/rest为0.8/0mm，
并新增speculativeCCD。新版LowerSDF的sdfMargin/narrowBand为0.01，旧为0.00035，
这两项是AABB对角线比例，分别约1.504mm/53.425µm，不是1cm/0.35mm。

两套PBD系统过滤目标均恰好为上述25项；它们均归RigidScene。恢复这25项偏移不直接改PBD边界，
但会影响试管与所有刚体的接触，运动变化仍间接影响液体，不能称仅影响夹持。
`evidence/grasp_contact_static_comparison_20261014.json`保存原路径/参数。
后续最小对照先仅恢复contact/rest参数组，其余SDF/质量/CCD/液体不同时改变；
若分单标量，先增contact到10mm，再增rest到1mm，避免rest大于contact。
当前尚未应用或运行该物理候选。

## 验收与规范

先分离共同显色问题与回架物理/判定问题，代表案例通过后独立重复首个真实成功，再回归全部适用旧成功及坏例。
不以恢复旧不合理误判为兼容目标；缺少历史身份或时序证据时保留限制。
规则依据STATE-001/002/003、ASSET-001/003、VAL-001/002/003/004。通用规范无需变更：
本次是明确用户授权的任务节奏版本化及受限诊断，旧任务包/旧规则历史保持原字节。
核心package/schema/API未变；此次未运行完整make check，前次1255通过/1跳过为已有仓库基线。


首条旧场景/共同新版配置对照实际完成7000步，worker返回0.5分（视频/审计尚在收尾）；
最后可见加热约36.4833秒、显色约0.94594。它没有复现旧历史1分，因此绝不把此次旧侧称为成功基线。
为分离引擎配置混杂项，另准备同一旧场景/旧metadata/旧metric、仅换回当前可获取旧YAML的mixed5控制。
该配置仍120Hz/7000步，只恢复原来未显式设置64–128迭代、CCD及容量等的配置；不改正式候选。
运行名old_original_config，在六次计时配对完成后执行一次，状态original_config_control_queue.json。
如果仍无法复现历史成功，将继续标明历史版本/初态身份缺口，不以此强行解释掉分。


首条旧对照随后通过完整运行审计：7000步/.5，6542源动作加458保持，14716条compute记录，
7414个观测native索引；有效加热倍率中位2，2188个2倍步、2个边界1倍步，maxheat36.483335s，
maxprogress0.945942，无shadow计算错误或引擎error。它仍不是历史1分的精确复现。
新版配对在进行中时已观测1881个有效加热步倍率1；其中326个native步在旧水面旁路和当前触水判断
均为True时由tube_touches_beaker停止，另有少量水面差异。旧真实触水累计约18.24秒，新触水与停止条件
需与同帧姿态/实际碰壁证据继续对照，不能将所有碰壁直接视为旧误判。
证据`partial_old_new_clock_comparison.json`，新版完整运行及其他两对尚未结束。

恢复旧刚体偏移的生产者诊断候选已作者到ConvertAsset的
`outputs/sciben_waterbath_120hz_20261010/task12_original_rigid_offsets_diagnostic_20261014`。
组合逐属性比较只发现25形状的50项contact/rest变化，粒子过滤关系不变；未进入正式候选。
引用式诊断基础层对外PhysicsScene关系的范围警告已注明，probe强层显式绑定到/World/PhysicsScene。
三冷态/一升降队列`original_rigid_offsets_bounded_queue.json`等待七次计时/配置控制完成后运行，
仅通过这些限定范围才可继续真实机器人抓取/回架验证。

`timing_v2_trial_queue.json`已排队：须六次计时对照及旧配置控制完成、偏移候选限定测试通过，
再由受门禁保护的作者工具产生只改时间的版本，先跑0/15/13三个代表。该版本不合入偏移，以分离时间因素；
仍待画面和物理修复判断，不自动全量回归或发布。初态metadata哈希与原动作在各次回放中核验。

## 04:30 UTC：第二组完成及接触逻辑候选

0与15两组旧/新配对均已完整运行：0为.5/.15，15为.85/.15；两组有效加热倍率均2/1。
15新版7000步、1162有效加热步、9.683334秒、最大progress .079040，无引擎或shadow错误。
第三组13正在运行。当前可获取旧版本仍未复现历史1分，不能声称已还原原始历史环境。

15新版实际触水约21.116668秒，其中11.433334秒被碰杯门槛拦住。
在记录姿态上只把五阶段时长统一乘0.5，progress仍仅.368872；这个离线归因不是新物理回放结果。
证据`clock_diagnostics_20261014T023450Z/pair_15_offline_attribution.json`。

被动contact订阅器只复制事件数据，不二次调用get_contact_report，也不控制任务。
实际事件包含正间隙点，故FOUND/PERSIST数量不能直接等同几何触碰。
`analyze_passive_contacts.py`重放所有保留碰撞对（包括未收到LOST的睡眠对），对齐native索引与旧计数。
1372个触水且碰杯阻塞步中，710步计数相符，662步不符而排除解释；相符步中587步
在暂定restOffset之和加0.1mm阈值下没有近接触，共4.891667秒。
相同点数仍不证明控制器与订阅器取得完全相同的碰撞对；不能将这些秒数直接加回或声称成功。
报告`new_frozen_15_passive_contact_attribution.json`保存源文件哈希与适用限制。

接触计数草案保留真正接近/穿透与睡眠持久接触，按separation与rest距离判断，
不以零impulse排除接触；原始点数仍用于容量检查，坏数据fail closed。
真实冻结类在2mm正间隙反例上先失败；草案7项通过，计时5项及被动订阅1项通过。
证据`evidence/contact_and_timing_unit_tests_20261014.json`。0.1mm仍是待运行验证的任务候选值。

已作者独立`contact_logic_probe_20261014T042933Z/scene.usda`，组合比较只有FlowController脚本一处变化；
物理参数、液体、时间、动作、metric未变。该绝对引用overlay仅作个人诊断，不能直接交付。
`evidence/contact_logic_probe_identity.json`保存入口、来源和哈希。
`contact_logic_fixture_queue.json`串行等待既有计时试验，随后运行正常显色、碰壁、倾斜和偏心夹具，
首错停止；即使全部通过，仍需距离边界/休眠、原机器人动作及重复回归，不能自动发布。

称量此时457/600完成且继续渲染。通用规范无需变更：本次仅扩充STATE-007/VAL-002的
任务级测量证据和未资格化候选，尚无依据推广接触距离默认值。恢复步骤同步至操作文档。
