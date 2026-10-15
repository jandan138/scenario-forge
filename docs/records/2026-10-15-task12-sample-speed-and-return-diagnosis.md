# 水浴：完整位姿诊断与样液速度上限候选

状态：未交付；时间候选重复0.85，回架未成功。以下速度修改尚未运行合格。
工作根R：`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/task12_liquid_color_20261012`。

## 完整诊断结果

当前主机上冻结B/C均7000步0.15；时间B/C均7000步0.85。
独立时间候选只读诊断pose_h13_a也为7000步0.85，实际7000条试管/夹爪位姿与
meta_record机器人关节的逐帧对齐误差为0（offset=0）。试管USD与live位置误差为0，
轴向最大差约0.002516度。证据：`evidence/new_liquid_pose_h13_a_pose_summary.json`。

加热期间试管在夹爪内的相对位置较稳定；放回阶段发生明显相对位移，最终试管倾斜约24.182度。
实际回架metric检查339次，无一次通过。仅凭相对位移尚不能区分碰架、夹持滑动和释放动作。
因此启动原成功版本同一case13的独立只读位姿对照：
`evidence/old_case13_pose_identity.json`、`evidence/old_case13_pose_a_run.json`，启动PID93721。
旧版诊断仍须恢复1分并核对原记录，才可作为接触差异参考。

诊断在个人副本metric内追加读取，不改变正式候选的metric。其与无诊断B/C之间的
动态非干扰不能仅由同分证明；同版本B/C本身已有非逐位重复，必须保留这个限制。

## 样液速度限制与实际动作不匹配

`evidence/sample_velocity_limit_diagnosis.json`记录：

- 管内SampleSystem速度上限为0.2m/s；实际试管原点最高速度约1.747m/s。
- 提取和移回阶段多步超过0.2m/s。100帧13905个粒子中心在管腔内，200帧6203个，
  3400帧仍6203个，3580及末帧只剩732个（按所读Points中心与真实内腔profile计算）。
- 安装的USD运行脚本明确开启粒子/速度回写USD并关闭抑制回读；所读点数据变化，
  离开管腔的粒子群在后续多次渲染后仍存在。尚未记录逐粒live速度，数量结果也不是新的保液容差标准。
- 先前静止/缓慢120mm升降夹具的保液通过，不能覆盖这里的快速机器人运动。

这些证据足以提出速度上限的单参数因果对照，尚未证明改高后就能恢复保液或回架。

## 已准备的单参数候选

`evidence/sample_speed3_identity.json`定位独立副本。
仅将20场景SampleSystem.maxVelocity从0.2改为3m/s；Bath参数、粒子数、质量、
几何碰撞、原动作、120Hz/7000、反应时间候选和评分规则保持原值。
3m/s高于这条已测平移速度，并与已有task10 Falling的数值一致；不继承其资格，也不推广成液体默认。
`evidence/sample_speed3_static_audit.json`逐场景对组合属性、关系和schema复核，唯一差异是上述属性。

`tools/run_speed3_after_old_pose.py`等待旧版只读诊断成功后才启动速度候选，GPU串行。
队列：`evidence/speed3_after_old_pose_queue.json`，启动收据：`evidence/speed3_after_old_pose_launch.json`。
候选仍带独立只读诊断；若有效，需要移入干净候选后重新做完整原生验收。
不能将提高速度上限当作完成修复，也不能靠0.85或颜色终态替代液体保留和回架成功。

## 规范和交付范围

依据MAT-001/003/004、USD-001/002、VAL-001/002/003/008、STATE-002。
通用规范无需变更：尚属特定任务的未合格参数候选，不建立新的通用速度默认值。
外部工具未进入Scenario Forge核心包；GenManip核心、机器人代码、同事目录均未修改。
交付仍限YAML、USD/依赖、task data、scientific metric；水浴LeRobot暂不做。
最终旧成功19组各两次、坏例、实际保液/显色/回架及独立安装门槛保持。


## 旧版位姿对照已完成，速度候选运行中

旧版pose_a在3722步恢复1分、success_rate1，全部3723观察帧的关节/夹爪/底座与原记录误差0。
观察trace与本次meta_record逐帧精确对齐，最终倾角1.069633度。
将旧版实际最终姿态代入未修改的新版tube_in_slot几何谓词，结果为true；新版原时间候选最终为false，
倾角24.182381度。因此这条有效旧示范不需要靠降低新评分标准才能接受。
证据：evidence/old_case13_pose_a_analysis.json、old_case13_pose_a_pose_summary.json、
old_new_completed_pose_comparison.json。

1000帧尚未回架时，新旧试管相对夹爪位置已相差约7.5mm；到3580帧差异减小，但插入后新版底部
停在更高位置，3660帧旧/新架子局部z约0.03433/0.06325m；3680旧版已满足几何落座，新版仍未落座。
不能把这些位姿差异直接归因于单个碰撞参数或仅归因于架子，继续以单参数因果验证推进。

速度候选已由队列自动启动。另核对41份初始metadata均没有SampleSystem/maxVelocity覆盖项；
诊断增加每20步读取实际system上限、粒子速度和回读开关，以核实运行时确实生效。
这些额外读取只在独立诊断metric中，正式候选metric不变；当前尚无速度候选运行结论。


## 速度单参数候选失败，转静止初始化隔离

3m/s在运行时确实生效，粒子速度读数达到约3m/s，updateParticlesToUsd为true。
但动作100帧（提管前）只剩602/13905粒子中心在内腔，最小局部高度约-9.44m；
到500帧仅420个在内腔。故单独放开速度上限不可接受，已按失效诊断提前停止，
不能计作完整7000步结果。记录：evidence/sample_speed3_early_rejection.json。
监督器随后记录的Traceback来自此次有意中断，需与此前已存在的液体失效区分；不能据此称引擎先崩溃。

开始两个5秒无机器人静止对照（原0.2与3m/s），定位是否基础容器/种子在放宽速度后就失效。
首轮漏了既有probe.usda入口，未加载Stage即失败；已原样补入该入口、验证组合后的上限数值，
以新输出编号_r1重试，原失败日志保留。当前队列evidence/sample_cold_pair_retry_queue.json，
源与修复说明evidence/sample_cold_pair_retry_identity.json。此为诊断入口修复，无资产参数变化。


## 短时隔离结果与未解决项

原0.2m/s静止5秒无越界；3m/s从第一步越界，最大13004/13905越界。
按原producer seed_profile恢复0.8mm规则排列、同数量/质量并清零初速度后仍第一步失败（最大13017）。
SDK4.1自带ParticlePostProcessingDemo.py使用spacing=2*fluidRestOffset；把0.516mm改为匹配0.8mm排列的0.4mm后，
首个越界延到第6步，但仍最大11123越界，不合格。不能由初态近邻距离小就独立断言它是根因。

静态凸包检查473个保液代理，规则初态没有粒子中心在代理凸包内部；这是静态几何检查，不证明cooking或接触间距有效。
固定试管、两秒静止，对比启用/关闭25个名义上已被粒子过滤的刚体面，均从第一步失败（12398/12344越界），
关闭这些面并未解决问题；不是可交付修复，也未证明所有过滤的完整行为。

接下来在原初态上，仅把maxDepenetrationVelocity从2调到0.2，保持总速度3，区分碰撞纠正与正常移动限速。
诊断账本evidence/sample_stability_diagnostic_ledger.json，当前尚无高速度保液合格候选。
保液是与回架并列的未完成交付门槛；过程分0.85不证明样液仍留在管内。


后续短测：maxDepenetrationVelocity0.2未消除失稳（最大13061越界，第1步开始）；
固定试管关闭sample selfCollision后仅72越界（第9步），但该设置不具备正常流体资格，不能交付。
匹配间距候选的particle solver128->16后最大6270越界（第5步），改善但仍失败。
远端SDK schema默认particle solver16；当前追加SDK自动offset基准以排查手工offset组合，尚无结论。
SDK4.1 particleUtils确认MassAPI设置的是整个粒子集合质量（helper将per-particle mass乘以数量），
没有把0.008kg改成“每粒质量”；保留8g总量，未按未经证实的质量假设改动。


SDK自动offset基准仍失败（9838越界，第5步）。恢复原完整GlassShell SDF并关闭498个proxy/partition
也失败（13548越界，第3步）；此诊断使用旧SDF contact/rest和采样参数，不能代表所有SDF设置。
仅保留样液系统仍第一步失败（12902越界），Tensor读取solid/fluid/particle offsets为0.28/0.516/0.68mm，
与USD一致；没有发现仅由Bath系统存在或文件属性未生效导致的解释。

原完整SDF的margin/narrowBand均0.00035，SDK schema明确这些为相对包围盒对角线的无量纲比例，
默认0.01；不能按0.35mm解释。当前测试现有producer完整GlassShell设置（margin/band0.01、
contact0.8mm/rest0），保留完整SDF、3m/s、标准offset和16迭代的短测。尚未合格，不归因单一参数。

生产者标准SDF设置短测也失败（13758越界，第5步）。当前短测批次全部结束、GPU已由各自owned runner释放，无高速度保液修复合格。下一步需进一步隔离无约束流体内部求解与容器接触，不继续把静止低速结果提升为机器人运动资格。完整账本sample_stability_diagnostic_ledger.json。


## 接触检测范围与回架分支继续

无样液重力+固定试管的26步对照，不论开/关nonParticleCollision均无越界；
固定试管有重力的242步仍失败，动态试管但样液无重力的242步通过。
这将问题集中到下沉/接触过程，但移除重力的通过不构成流体资格。
单颗真实PBD粒子在固定试管、无重力下以1或3m/s撞壁均逃逸；将非粒子contactOffset设0.03m，
显式restOffset保留0.6732mm后两者都被侧壁拦住。0.03m大于3m/s在1/120秒的0.025m行程，
是检测范围对照，不代表将平衡间距扩大至3cm。

完整13905颗正常重力验证：原参数+大检测范围仍1070越界；标准offset/16迭代/规则初态同范围仅2颗越界，
严格检查仍FAIL，且标准参数下粒子高度分布明显变化，体积/外观尚未合格，不能仅因越界少就采用。
保留原液体尺度/质量/初态，只降128->16粒子迭代，最大84颗越界，仍FAIL。
大检测范围运行有大量PxShape::getMaterialFromInternalFaceIndex警告，日志保留；不宣称无警告或其影响已完全排除。

用户询问为何从回架转到液体：已澄清保液是在回架诊断中发现的新增交付阻塞，尚不能证明它是回架失败的全部原因。
为避免回架工作被保液完全阻塞，启动独立contact/rest对照，保留同一PBD基线，仅将25个刚体碰撞面恢复旧版
contactOffset0.01m/restOffset0.001m。静态case13组合对比恰50个标量差异，其他属性/关系不变；
20个场景已生成独立副本。原动作、120Hz/7000及评分保持，metric只读追加仍限定诊断副本。
证据rigid_offsets_native_identity.json、rigid_offsets_native_static_audit.json、rigid_offsets_h13_a_run.json。
即使此分支拿到1分，也不得越过未完成的保液交付门槛。
