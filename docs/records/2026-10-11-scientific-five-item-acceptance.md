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

称量第二条坏例 `five_item_bad_01_20261010T184418_791945Z` 完成4000步，得分0.3、
success_rate0。四路完整解码及周期120Hz检查通过，实现者查看四路0/2000/3999/4000帧；
颗粒仍在舟中，空瓶由夹爪握持在秤盘外，空盘显示去皮后的负值。抽帧不证明全程没有
自发位移，真实失败结果保留。18条当前状态汇总见 `evidence/current_bad_case_acceptance.json`。

称量第三条坏例 `five_item_bad_02_20261010T190110_873494Z` 完成4000步，得分0、
success_rate0。四路解码及周期120Hz检查通过，查看0/2000/3999/4000帧：中段右视角
可见瓶内已有3颗固体、桌上散落2颗，终帧装料瓶放在秤盘上显示毛重52.17g；所有阶段
得分仍为0，装料瓶未被误记为空瓶称量或去皮。这不等同于逐帧碰撞认证。

滴定坏例 `five_item_bad_03_20261010T191652_101574Z` 完成2000步，得分0.2、
success_rate0；四路完整解码、周期120Hz和物理错误扫描通过，四路关键帧已查看。
原580帧arm/base动作逐帧完全保留，后续保持原末帧；2001行机器人观测均有限，
原记录的巨大关节/基座跃变未重现。早期原策略仍有突变指令（某关节目标由-0.012
变为-0.884rad），未通过平滑动作掩盖；详细数值及限制见
`evidence/task10_bad_robot_state_comparison.json`。腕视角裁切仍记WARN，未声称逐帧物体碰撞认证。

银镜首条坏例 `five_item_bad_09_20261010T172035_172141Z` 约2077步出现GPU
articulation solver错误，随后CUDA700。没有完整结果，不记零分；待重采许可不免除
此崩溃的修复。后续银镜队列停止，ConvertAsset生产者正在独立复现与接触隔离诊断。

生产者进一步在独立SDK中复现同类CUDA错误。仅过滤补充壳与机器人接触的诊断虽越过
故障前缀，但丢失必要烧杯碰撞并出现剧烈飞出，不可交付；恢复烧杯SDF并保留过滤的
冷态、升降及2300步前缀通过，完整7000尝试仍在1836步CUDA失败。没有晋升该overlay。
后续隔离反应图及详细GPU接触数据采样路径，不预设密集凸壳是唯一原因。诊断代码提交
`acd22b8`仅在ConvertAsset；完整失败与输入哈希见生产者`silver_bad09_diagnostic/HANDOFF.md`。

后续生产者的fluid-only候选通过银镜限定本地资格：10秒冷态、17秒规定升降逐native步
保液，以及管杯底/侧和动态落架接触；完整原坏例7000动作完成7302个120Hz native ticks，
无引擎错误，原反应图和接触读取均启用。接触事件确认原SDF与机器人、管杯、管架
仍实际接触；采样姿态无远飞/NaN。日志仍有非致命SDF face-index警告，不称为无警告。
生产者提交 `c1f3106`，独立层 `fluid_only_rigid_delta.usda` SHA256为
`7f3ec6b60c7a25cb2342038720926614ff9d88295645c78d16785cd6340005d1`。
该层仅恢复杯原SDF碰撞并定义两组过滤，使补充壳只承担液体边界；保留必要原刚体接触。

已接入20个银镜场景：每个入口新增强层级payload `[producer delta, original scene.usd]`，
在/World阶段组合后映射到/World/_scene；原scene.usd字节不变，原wrapper备份于
`silver_before_fluid_only/20261010T192606Z`。20场景静态关系/依赖检查通过，own main同步。
原版远端9条银镜坏例已排队等待非银镜队列释放GPU；本地通过不替代该验收，不推广到斐林。
生产者完整证据见 `silver_bad09_diagnostic/fluid_only_qualification.json`；集成证据见
`evidence/silver_fluid_only_integration_20261010T192606Z.json`。

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

自己的主 checkout 已切回 `delivery/scientific-five-items-20261011`，HEAD为上述metric-only
提交。四任务候选同步后3172个文件与验收目录哈希一致，588个非允许范围原版Git blob
无差异（其中1个为原始软链接）；实验core保留历史分支，旧资产/data单独归档。
本次只同步候选，不宣布银镜或全部坏例通过；验收目录运行不受主checkout切换影响。
证据见 `evidence/owned_main_restored_20261010T185138Z.json`。

静态时间预算复核发现：当前水浴/银镜7000动作步在120Hz下为58.333秒，斐林
`mixed_6`/`unseen_prospect_6`要求59.968秒加热，银镜`mixed_18`要求59.482秒，
尚未计抓取、观察与回架时间。该范围的完整成功示范不仅缺失，还受原步数预算限制。
证据 `evidence/waterbath_time_budget_review.json`；已向用户确认首轮保留原上限还是
本轮调整，未收到答复前保持现有配置和坏例对照。称量4000步上限不涉及此讨论。

已生成不可视为最终合格的五类候选归档：
`delivery_candidates/20261010T193046Z`。离线覆盖包含3188个YAML/USD资产/task-data文件，
另有独立metric补丁和两份各10文件的单示范LeRobot归档；生产/验证脚本与core补丁不在
归档内。所有tar成员哈希、gzip完整解压流/CRC/长度与归档SHA通过。
候选状态仍为 `CANDIDATE_NOT_FINAL_QUALIFIED`，不以打包成功替代剩余原版坏例验收。
