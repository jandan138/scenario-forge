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
