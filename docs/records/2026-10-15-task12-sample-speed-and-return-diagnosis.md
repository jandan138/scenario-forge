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
