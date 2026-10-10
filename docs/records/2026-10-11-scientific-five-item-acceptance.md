# 科学实验修复：五项交付边界与原版验收

状态：实施中，尚未交付。延续 2026-10-10 启动的修复任务；运行时间以各 receipt 的 UTC 为准。

用户明确限定最终交给陈建同的内容：task config YAML、USD/assets、task data、
scientific_experiments metric 代码、LeRobot 数据集。生产、测试、转换辅助脚本允许保留在
朱子厚工作目录，但接收方不能依赖它们或修改 GenManip core。

实验分支 `experiment/scientific-repair-runtime-hooks-20261010` 保留既有诊断，不作为交付。
干净验收 worktree 位于
`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/baseline_runtime`，基于
`0e99ea01eec7780e53fa2ce3ecb0fce1a6b4500a`。588 个非允许目录的受跟踪文件与原版一致，
也已只读核对与陈建同当前 checkout 一致。子模块以 gitlink 单独处理，不将目录当文件哈希。

## 实现与证据边界

运行初始化与原生物理时钟嵌入 USD，只导入 Isaac SDK、NumPy 和标准库。
重置数据通过原版已有 `initial_prim_attributes` 和 `initial_particle_states` 恢复。
metric 所需纯判断放在允许的 metric 目录。滴定动作先依据原始遥测核对时长，再离线展开
到 120 Hz task data；原始 LMDB、metadata 和转换记录保留。重复的旧图像不冒充新采的
120 Hz 训练观测。

称量第一次原版完整回放
`five_item_task09_positive_20261010T155820_629968Z` 得分 0.3，success_rate 0，4000 步。
前三阶段通过，五颗固体仍在料舟。与实验捕获成功回放比较，指令相同、机械臂关节差异
小于 0.001 rad，但原版左夹爪一根手指从初始阶段停在 0.044 m 开口极限。
之后仅在 USD 内增加播放前的回读设置初始化，原版回放
`five_item_task09_sdk_graph_20261010T164048_441466Z` 在3372步取得得分1、success_rate1。
未改变动作、评分权重、机器人源码或4000步上限。日志确认早期设置在 `playing=False`
时执行；周期原生时钟记录的 dt 为1/120、wrong_dt_count为0。视频完整解码与最终数据集
核验另行进行，不能把得分替代视觉验收。

此前手工构造的早期图误将 execution 端口写成 token，导致原版相机初始化失败；尝试
`five_item_task09_early_readback_20261010T163519_438394Z` 保留为基础设施无效结果，
不记任务零分。SDK生成图使用 uint 端口及 isExecution 元数据，随后原版回放通过。

滴定第一次原版回放 `five_item_task10_positive_20261010T162353_677908Z` 完成2000步，
得分0.4、success_rate0。与实验成功回放的前1574条动作逐条相同，机械臂和夹爪实际
位置差异很小。限定SDK对照发现：通用粒子恢复与USD控制器自身重置同时执行，释放
5.454mL仅接收0.016875mL；只保留控制器完整重置则接收5.454mL、零洒出。
从41条task metadata去除重复的`initial_particle_states`，仍通过原版属性恢复接口
提供四组初始粒子/速度、epoch和重置标记，USD控制器恢复点、速度、ID、宽度和质量。
未推断未隔离验证的PhysX内部机制。

修复后 `five_item_task10_controller_reset_20261010T173404_890739Z` 使用原服务和
未修改的原客户端，1574步得分1、success_rate1；接收16.26075mL、零洒出。
所选训练源的原版完整回放仍单独验证，不能只以评测源成功替代训练源资格。

训练源首次独立验证在1313步触发`arm_state_jump_too_large`，结果0.2；初始夹爪状态与
捕获时有差异。为滴定20个USD加入称量已验证的播放前readback初始化后，
`five_item_task10_controller_reset_training_early_20261010T180717_910594Z` 满分通过1582步，
并用最终USD复核评测源：`five_item_task10_controller_reset_eval_early_20261010T181926_167601Z`
满分通过1574步。二者均使用未修改原客户端和原core。训练源机器人状态与捕获不是逐位
一致，差异报告保留；不能借用称量的逐位一致结论。
四任务各20个USD环境变体已迁入原版验收目录。80个组合入口的依赖扫描无缺失、无
目录外引用；这是静态闭包检查，后续修改仍须刷新相应哈希与动态证据。
原版验收目录中普通机器人等已有资产的软链接仅用于本地运行，不属于最终离线包。

## 用户接受的首轮待补项

银镜和水浴允许明确标注“缺完整成功示范，待重采”，首轮交资产修复与真实坏例结果。
这不免除资产有效性、原版可运行、坏例回放和如实报告的要求。未获得成功示范的任务不
生成或标记合格成功训练数据。称量成功示范未获得同样豁免，已完成上文所列原版回放验证。

水浴 candidate13 保持当前候选。仅恢复旧接触参数的 candidate14 未修复完整回架，
不提升为新交付头。候选13的另一条原示范在限定直接 SDK 测试末段插回，但只有95个
连续有效末帧且禁用了任务图，不作为完整任务成功证明。

水浴首条坏例 `five_item_bad_04_20261010T165353_434305Z` 完成7000步，得分0.15、
success_rate0，四路视频完整解码。累计加热达到16.325秒后因试管移出水浴停止，
实现者抽查四路0/3500/6999/7000帧，末段试管横躺桌上保持可见；不是逐帧排除穿透证明。

称量首条坏例 `five_item_bad_00_20261010T182936_984791Z` 完成4000步，得分0、
success_rate0。四路完整解码和周期120Hz时钟检查通过；实现者查看四路
0/2000/3999/4000帧，末段颗粒仍在称量舟、瓶在桌上、秤盘为空，未误记任务成功。
终帧总览显示去皮后空盘负值；腕视角随机器人移动存在裁切，不据此声称逐帧无穿透。

银镜首条坏例 `five_item_bad_09_20261010T172035_172141Z` 约2077步出现GPU
articulation solver错误，随后CUDA700。没有完整结果，不记零分；待重采许可不免除
此崩溃的修复。后续银镜队列停止，ConvertAsset生产者正在独立复现与接触隔离诊断。

生产者进一步在独立SDK中复现同类CUDA错误。仅过滤补充壳与机器人接触的诊断虽越过
故障前缀，但丢失必要烧杯碰撞并出现剧烈飞出，不可交付；恢复烧杯SDF并保留过滤的
冷态、升降及2300步前缀通过，完整7000尝试仍在1836步CUDA失败。没有晋升该overlay。
后续隔离反应图及详细GPU接触数据采样路径，不预设密集凸壳是唯一原因。诊断代码提交
`acd22b8`仅在ConvertAsset；完整失败与输入哈希见生产者`silver_bad09_diagnostic/HANDOFF.md`。

新的独立加热门控夹具通过：斐林偏心、烧杯倾斜、试管碰壁，以及银镜偏心。在浴液有效、
试管仍浸水时，各自命中对应停止原因，累计时间不再增长。为隔离条件，部分刚体在夹具中
设为kinematic，未修改交付资产；不扩展为自由运动或机器人资格。证据及约束见
`evidence/isolated_heating_guards_summary.json`，旧的复合失败探针保留。

## 维护与剩余检查

证据根：`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010`。
`evidence/five_item_delivery_boundary.json`、`evidence/jiantong_core_match.json` 和
`evidence/first_round_pending_demonstrations.json` 保存边界、原版核对与用户决定。
最终仍需只含五类文件的清单、依赖闭包、相应原版回放、视频完整解码/目视检查和数据集验收。
旧实验 delivery_manifest 已标记 superseded，不作为交付清单。

滴定补齐材质状态的1582帧离线渲染已转换为120Hz LeRobot v2.1；最终USD上的
原版训练源回放通过后，与称量3372帧数据各自记录为首轮单示范合格，不扩展到完整语料。
实现者检查四相机的0/790/1581帧：末帧顶部视角可见淡粉紫色，但黑色桌面和玻璃折射
使色彩偏暗，中途手臂遮挡、腕视角裁切保留为WARN。称量3372帧离线渲染的四路
0/1700/3371帧已检查，总览和右相机末帧清楚显示4.56g；这仍是记录状态离线重放，
不标成原版服务的原生录像。独立审查未进行。

规范无需变更：ASSET-002/003、STATE-002/003/005、VAL-001/003/004 已要求依赖自包含、
证据匹配最终运行内容及未通过项如实区分。本次没有改变核心 package/schema/API。
此前 Scenario Forge make check 的 1255 passed、1 skipped 只证明当时仓库检查通过，
不代替本次原版服务任务验收。陈建同目录未写入，飞书文档未修改，仓库未推送。

metric-only提交为 `9d85d222e213d34bda43e8834266e4fff401ce56`，仅允许目录内5个文件，
17项纯判定边界测试通过，Black格式化前后AST一致且提交钩子通过。操作入口见
[受限交付说明](../operations/scientific-five-item-handoff.md)。
