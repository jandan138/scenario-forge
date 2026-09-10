# 受力称重设备的场景集成

天平的显示分度不能由静态 LCD 字样推断。设备需要明确测力来源、时间、单位、有效条件和验证载荷，
再将连续测量值与任务完成条件分开。

## 职责和结构

ConvertAsset 负责机身、独立秤盘、承重关节、按钮、碰撞和质量配置，以及独立设备资格。
Scenario Forge 消费生产者资产与来源绑定的载荷配置，组装原任务布局、设备关系、目标参数和可移植 handoff。
本次仅增加制作脚本，不修改 core/schema API，也不引入 episode runner。

可搬动天平采用自由基座 articulation，三个刚体 link 位于 identity `Instance` 下。
它不使用固定基座 `BaseFixed`，因此不能套用 ART-001 至 ART-004 的固定基座资格。
场景仍只在对象根做摆放，VR 注册对象根和全部刚体 link。

## 数据接口

`BalanceState.update(gross_g, dt, pressed, valid, eligible)` 只做纯计算。
`gross_g` 是实际受力换算的毛重，`dt` 来自物理步；输入不是粒子数量或物体标称质量之和。
`eligible` 表达容器位置、样品进入容器和药匙归还等任务条件，不制造读数。

设备桥接读取 PhysX articulation 的 link incoming force、实时姿态和按钮 DOF，
把 link-local 力投影到世界竖直方向，使用声明的重力和秤盘自重进行换算。
载荷及 articulation 的休眠状态属于测量资格条件。
代码以内容哈希绑定并嵌入生产者 USD；两个版本用不同物理步节点名称接入同一控制器，
并由兼容层选择对应版本的包内 MDL。MDL 辅助模块由 ConvertAsset 现有 AAN 工具收集，不在消费者重写转换逻辑。

根属性 `balance:*` 提供连续毛重／净重、皮重、有效性、稳定性、错误、显示和成功快照。
`balance:container`、`balance:spoon`、`balance:samples` 是场景绑定关系。
标准配置和读取示例以[操作指南](../operations/solid-weighing-r1-guide.md)为准。

## 判定和证据

去皮是边沿触发的等待请求，稳定后执行，超时不覆盖旧皮重。
成功须同时满足任务位置条件、已去皮、有效稳定读数、目标容差及保持时间。
成功快照与后续实时读数分开，明确重置职责。

生产者资格和最终场景资格分别验证两个 runtime、不同初始化路径与独立进程。
报告同时绑定主场景、设备 USD 和包含 USD/MDL/纹理/入口配置的内容指纹，
不能只验证引用它们的那一层 USD 文件。
数值测量、真实画面、受控物理放置与机器人策略证据分别声明，遵循 VAL-001 至 VAL-004。
