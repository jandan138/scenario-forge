# 水浴：旧版校准完成，进入正确执行方式下的新版验证

状态：旧版三个代表校准通过，新版对照实际运行中，尚未交付。
运行时间以各receipt的UTC字段为准。

## 旧版结果与画面复核

工作根R：`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/task12_liquid_color_20261012`。
mixed5完整分段模式两次5902步1分，已执行5903个机器人观察帧与原记录逐元素相同，最终画面已核对。
catalog15在3162步1分、catalog13在3722步1分，均与历史成功步数一致；手臂、夹爪、底座全记录最大误差0。
本轮补完两条的同帧最终overlook复核：机器人、架子及回架试管位置一致，保留曝光差异。
`remaining_original_acceptance.json`保存复核；`original_success_gate.json`已置PASS_ORIGINAL_BASELINE_CALIBRATED。
范围是上述代表原任务执行校准，非新版液体资格，也不宣称恢复了所有原HTTP请求字段。

关键修正发生在个人回放辅助脚本：保留原动作值/顺序，恢复有证据的绝对/相对底座语义及分块/渲染方式。
mixed5使用chunk8和完整分段模式；两条Pi05代表使用chunk30、原零底座命令的relative语义及默认subframes2。
不能把之前统一absolute/单步执行得到的19组退分直接归因于新USD。

## 新版隔离对照

新入口`tools/run_calibrated_new_case.py`仅允许已校准的catalog0/15/13，按动作来源选择对应helper，
不把mixed5模式表套到其他动作。源meta_record、配置、初始化metadata哈希在执行前核验；仍禁止核心源码改动。
原生SDK时钟、完整日志、原动作逐帧值、视频解码继续由既有native audit验收。

`calibrated_new_timing_pair_queue.json`实际串行执行catalog13两次：

1. 冻结新液体包receiver_archive_install_20261013T031857Z，正确chunk30/relative-zero回放。
2. 已有只改反应时长的timing-v2候选，正确回放；有效时长统一0.5，物理/材质不变。

这仅测试已授权的时间候选，不将0.5宣称为全部历史执行方式的精确反算倍率。
保持原生120Hz、7000上限、真实PBD、碰壁等守卫，不同时合入接触判断或刚体偏移候选。
任务低分保留作对照；引擎/物理错误首错停止。第一条启动时一次SSH连接重置，确认未创建进程后重连，
主机身份和空闲GPU正常，再创建唯一进程；没有重复启动。

## 后续门槛与交付边界

先根据该配对分清显色和回架结果，再决定后续最小修复，不盲跑旧队列。
剩余动作执行协议必须逐来源确认，最终同一版本19组各两次成功、坏例和干净安装验收要求不变。
交付仍只依赖允许的YAML、USD/dependencies、task data、scientific metric；诊断helper不成为运行依赖。
水浴LeRobot本轮不做；称量仅为此前独立后台任务。

规范依据STATE-001/002/007、VAL-001/002/003/004；通用规范无需变更，本次是任务级执行语义校准和隔离验证。
核心package/schema/API未变，不引入仓库episode runner。同步operations，未声称重新执行全仓库make check。

## 新实例恢复与重复对照

用户停止旧远端后提供10.150.163.175:22（公网123.57.187.96:900）。公钥重新授权后连接成功，
hostname为dsw-529861-6cb4cb97bf-vdwmr，GPU为GPU-b9f30517-2560-4f0b-9a9b-275b89c9000e。
Isaac版本4.1.0-rc.7+4.1.14801.71533b68.gl，客户端依赖和共享工作区可用，8087与GPU空闲。
身份保留在remote_restored_20261015.json，不再重试停止的旧地址。

calibrated_new_timing_repeat_queue.json已经启动，分别执行calibrated_frozen_h13_b、calibrated_timing_h13_b。
仍只重复原A/B版本，不改倍率、物理参数或评分。新实例/GPU与首轮不同，因此跨机器差异本身
不能证明同机不稳定；必要时在新实例继续同版本重复，分离主机变化与版本效应。


## 新实例首对完成及同机复跑（03:56 UTC）

新实例B对照正常结束，两条均7000步、success_rate=0：冻结版0.15，时间候选0.85。
原生审计及动作验收退出0，画面复核仍待完成；不能把审计退出0称为任务成功。
对应证据为R/evidence/calibrated_new_timing_repeat_queue.json及其引用的两条run报告。
旧实例冻结版0.30与新实例0.15存在主机混杂，尚不能判定同机随机不稳定。

在确认新实例GPU空闲、8087可用、上一轮服务退出后，启动同一实例上的第二对冷启动复跑。
入口R/tools/run_calibrated_new_timing_samehost_c.py，队列
R/evidence/calibrated_new_timing_samehost_c_queue.json，启动收据
R/evidence/calibrated_samehost_c_launch.json（supervisor PID 44263）。
后缀c仅表示复跑次数，不是“timing v2 scale=1”的第三资产候选。
复用既有runner与原版本，仅更换输出身份；未更改资产、动作、metric或核心代码。
目的为比较同一主机B/C重复性，全部结果保留，不按最高分选取资格。
规范无需变更：本次落实VAL-008和已批准的重复对照计划，仍未满足交付门槛。


本轮后台运行期间完成四条A/B记录的机器人观察对照，保存于
R/evidence/calibrated_ab_robot_comparison_20261015.json（各源meta_record绑定SHA256）。
新实例冻结B与时间B从103帧出现浮点级差异：关节4.66e-10rad、夹爪9.31e-10m；
全回合夹爪最大差异约6.215mm。首个非零差异不能直接当作失稳起点或根因。
这是机器人观察比较，不含试管刚体位姿，尚不足以区分夹持滑移和回架碰撞；
后续需结合视频和只读试管/夹爪相对位姿。跨主机比较仍不作同机不稳定证据。

目视复核B两版本overlook帧3000/3722/7000：两者回架后均可见倾斜，时间候选终帧已横倒在架后缘附近。回架失败有物理画面对应，不能仅靠修改metric消除。稀疏帧尚不能定位滑移/松爪/碰撞先后，不测量图像角度或推断保液。非独立复核记录及图像哈希位于R/evidence/new_b_visual/review.json。

追加原成功视频与时间B同帧3580/3640/3680/3720对照（R/evidence/new_b_visual/release/review.json）：3680可见松爪，3720双手撤离。旧视频回架时也有斜向投影，不能把图像斜向直接当20度判定；需实际tube/link6相对位姿定位。新版撤管后杯内可见橙色斑块，列为样液留存待核项，不能凭图像确认泄漏数量。

静态复核实际case13组合场景3428个prim、属性默认值、关系、脚本AST和初始化metadata：两候选只发现时间版本/倍率/阈值和_read_timing函数差异；未发现组合后的质量、碰撞或粒子默认参数差异。报告R/evidence/timing_pair_static_case13.json，脚本R/tools/audit_timing_pair_static.py。范围仅该case静态组合，不替代运行时求解器、时间采样属性或全部20场景资格。

已准备new_liquid_rack_observer_fragment.py，扩展旧只读诊断以记录架子局部试管变换和显色遥测；原metric只执行一次。计数/抽样不变的CPU测试1项通过；未装入正在运行的A/B，尚无GPU非干扰资格。准备收据R/evidence/new_liquid_rack_observer_preparation.json。后续独立诊断副本使用，不能成为接收方依赖。

独立诊断副本已创建于/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/task12_liquid_color_20261012/diagnostic_new_liquid_observer_20261015T040420Z，核对711个复制文件哈希、588个非允许改动目录内的基线文件原字节。仅task12 metric追加只读观察，原候选未改；tools/run_new_liquid_observer_case.py限定catalog13并使用校准chunk30客户端。尚未启动GPU诊断，等待现有同机对照结束。

诊断追加每20物理步读取一次SampleParticles中心的腔体内数量、试管局部质心与高度分位，用于核对杯内橙色残留疑点。读取USD Points需先验证与live同步，不能直接充当保液合格标准；没有写入粒子。变换/腔体统计及NaN拒绝2项测试通过，原计数中性1项仍通过，独立副本metric哈希已刷新，尚未运行。
