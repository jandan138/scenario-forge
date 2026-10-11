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

水浴第二条坏例 `five_item_bad_05_20261010T192812_896201Z` 完成7000步，得分0.15、
success_rate0，四路解码、周期120Hz及错误扫描通过。四路0/3500/6999/7000帧已查看：
末段试管斜躺在架顶，仍在工作区可见；烧杯保持桌上，日志加热为0、未浸水，没有反应
成功误判。抽帧不能证明全程无穿透，也不代表已正确落座。

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

## 后续新增失败：候选仍不具备最终交付资格

水浴 `five_item_bad_06_20261010T195420_029770Z` 在约3177动作发生PhysX
mArtiSolveBlockPartitionFunction/artiPropagateImpulses2 CUDA700，随后Curobo FK才报告
非法访存。没有完整结果，不记零分，也不把FK堆栈当作根因。非银镜队列自动停止，
等待中的银镜队列随后退出，尚未在远端运行fluid-only候选。GPU/原服务进程/8087清理
已复核。证据为本run的 `invalid_attempt.json` 和 `cleanup_verified.json`。

生产者对银镜文档mixed_17采用正确unseen_scene_7与mixed_17 metadata，原6922条动作
完整回放无CUDA，但没有真正回架。全程pose结合原finger convexHull几何复核发现
最大6.42mm穿入，超过1mm持续20动作步；这是原输入几何，不宣称重建PhysX cooked形状。
早期接触聚合报告仅存最小值，不能据此称“瞬时”；另一次前700动作逐contact补录未
重现深穿入，输入哈希一致而接触后轨迹分离，不能把补录时间线套回原运行。

独立120mm自由落管600步夹具未稳定落座，保留FAIL；另一个对准同c05槽、距支撑面
5mm释放的600步动态夹具通过末120步位置/倾角/速度/径向条件。后者仅证明受控放置
后的支撑可行，不能覆盖120mm失败，也不是完整成功示范。

生产者正在制作少量开放管壁的刚体接触代理，液体细壳继续单独处理；两任务需分别
获得新资格。五类归档字节检查仍有效，但状态现为
`CANDIDATE_WITH_UNRESOLVED_WATERBATH_PHYSICS`，不能作为最终合格交付。

后续rigid_proxy_v2诊断候选使用264个开放管壁刚体单元，PBD细壳保留；新形状对
两个粒子系统单独过滤。单刚体两个shape的Cube和convexHull最小SDK夹具分别证明：
仅指定shape被过滤，同刚体未过滤shape仍支撑粒子。不能仅凭静态filteredPairs字段
推断此语义。原700动作前缀的finger/可见玻璃重叠已低于0.1mm；质量、COM、惯量、
可见网格和粒子参数不改。v1因底部近似偏差拒绝交付，v2仍待完整资格。

独立原版诊断目录为工作根 `proxy_validation_runtime`，HEAD仍为metric-only9d85d222，
新增producer层SHA为 `dea5a36018ea6a5b276ea5206e78d8a6c2fe57e3cc9865285cd43451cae5e943`。
按生产者明确的 `[proxy, fluid-only, original]` 组合40个两任务场景，原始scene.usd不改，
两粒子系统目标、264代理、质量/COM/惯量与依赖闭包静态通过。B/main没有随诊断修改。
`diagnostic_proxy_v2_task12_bad06_20261010T203742_592427Z` 正用原core/原动作/7000上限
重跑先前水浴崩溃例，目前仍在执行，不标通过；证据 `evidence/proxy_v2_diagnostic_integration.json`。

D中的水浴bad06诊断随后完整完成7000步，score0.15/success_rate0，四路解码、
周期native120与物理错误扫描通过，实现者已看四路0/3500/6999/7000帧。最终试管
横放架顶，未记为正确落座；离水后加热停止在21.183秒。旧失败也找到了客户端3177帧
左/总览/右三路拼接部分视频，完整解码该文件并查看关键帧；它不是完整四路回合结果，
最后可见画面正在回架，之后观测报错。见 `audits/client_partial_bad06/audit.json`。

但同v2在生产者直接读D的完整silver mixed17尝试中，331动作后再现CUDA700。
属性/关系/API/child顺序、脚本SHA及observer选项与此前通过前缀一致；微小warmup
差异后轨迹分离，不能从前缀通过推出全程稳健。杯体/杯沿仍为SDF，倒液嘴原为
convexHull，生产者继续定位；不以FK堆栈或某个SDF作为已证实根因。原版远端
`diagnostic_proxy_v2_silver_bad17` 另行启动对照，D/B/main输入保持各自冻结。

原版远端 `diagnostic_proxy_v2_silver_bad17_20261010T210755_996785Z` 也在约270动作
失败，首错PhysX mArtiSolveBlockPartitionFunction/artiPropagateImpulses2 CUDA700，随后
FK报错。没有完整结果，不记分。原版未加载生产者的额外contact事件observer，因此
该observer不是必要触发条件。v2依旧未取得最终资格；水浴单条完成不抵消此失败。

用户再次确认水浴首轮允许注明“待重采”，先交资产修复与真实坏例结果。此范围已写入
`evidence/first_round_pending_demonstrations.json`，不豁免资产有效性或运行时崩溃。

随后生产者的新烧杯96单元代理（`c9bb470e5a3ae4f999480d3f0db6aa19127987037d0026be61ca252a72fb450f`）
与264试管代理组合，在完整接触读取的700动作前缀中于275动作再次FAIL_ENGINE。
首错仍为mArtiSolveBlockPartitionFunction，随后CUDA700；两容器启用碰撞均已无SDF，
因而不能把替换烧杯SDF称为已解决问题。后续逐步记录见132/191/224/236/276/238/259/264接触点，未达到8192容量，
粒子有效标记仍为true也不能证明引擎健康。证据为生产者输出
`silver_bad17_diagnostic/recovery_bath_proxy_v1_prefix700/report.json`。

新的 `bath_proxy_validation_runtime` 仅准备原版core与旧v2载荷副本，尚未集成该失败层、
未启动远端回放。B/main与原D保持冻结。继续以保留真实碰撞及碰壁加热门控为前提，
诊断SDK详细接触读取与事件读取的差异；不交付禁用采样或伪造零接触的探针。

生产者将详细tensor接触读取替换为SDK即时接触报告，保留tensor view注册及杯v1
作单变量对照，仍于271动作FAIL_ENGINE（574个原生120Hz tick）。因此不能把详细
读取调用本身宣布为根因，失败候选不推广。原失败的575个成功warmup/action帧中，
独立SDK事件与tensor接触点数逐帧一致，前后偏移一帧则出现不匹配；这只是原运行
采样对应关系，不是新读取实现的休眠/重置或完整回放资格。下一诊断回到D v2，
以SDK接触报告保留实际碰壁判定，并移除不再需要的tensor view注册。

D v2加即时报告且不创建contact tensor view的短前缀随后完成700动作，状态为
`PASS_BOUNDED_ENGINE`。1000个成功warmup/action帧的graph count与独立SDK事件
逐帧相等，187个正接触帧，最大139；此结果不能外推静止休眠贴壁/重置或完整策略。
对应生产者目录 `silver_bad17_diagnostic/recovery_D_immediate_no_view_prefix700`。

新隔离目录 `bath_proxy_validation_runtime` 现只包含D v2加两任务readout脚本delta，
没有失败的杯v1。40入口验证原/new script哈希、threshold0、264代理/PBD关系、
质量/COM/惯量及依赖闭包；见 `evidence/immediate_no_view_diagnostic_integration.json`。
银镜delta SHA为 `139f2c2e1733f3296b36298ec09739269f58cbe870b4bc1eae550f60a49c7f3d`，
斐林为 `31199ce3f292c177f249b7eb838697f028f3c6da72d5d2d1a32e09d855d234e3`。
原版远端 `diagnostic_proxy_contact_silver_bad17_20261010T213332_344589Z` 已启动完整
坏例诊断，588个非允许范围原版Git blob核验一致；尚无完整结果，不标最终通过。

独立静止贴壁/休眠夹具随后发现即时报告与旧tensor均在休眠贴壁帧返回0，
当步SDK事件也为空。1366个贴壁休眠帧受影响，1564原生tick无引擎错误，语义验收
仍为FAIL。旧实现同样漏判不是豁免理由：需持有FOUND/PERSIST直到LOST的活动
接触状态或等效fail-closed机制，并验证离开、重新接触、epoch/reset和清理。
当前远端即时无view回放继续作为引擎诊断，不晋升为最终加热门控资格。

持续接触状态版本在SDK微夹具通过1564tick计数测试和2346tick实际内嵌wrapper
生命周期测试，2049个休眠贴壁帧保持活动接触，移离/晚初始化fail-closed/epoch变更/
同epoch物理索引回退/cleanup通过。其700动作前缀1002原生tick无引擎错，1000帧
接触布尔与SDK同帧一致；活动记录点数不是每帧重新测量，FOUND随后LOST的同帧
例子有63对64差异，正确释放已离开的pair，不宣称逐帧点数全等。

该前缀也记录一帧raw指尖穿入1.512mm（action146），SDK峰值1.539mm在下一帧147；
各自超过1mm只持续8.33ms，随后恢复约0.1mm。保留此瞬态穿入，不能借用此前
stateless轨迹的0.108mm最大值。证据在生产者 `recovery_D_active_no_view_prefix700`
的grip与 `finger146_transient_audit.json`，仍待完整场景接触/任务验收。

stateless远端诊断在保存2157条客户端动作记录后因上述已知休眠漏判主动停止，
状态 `STOPPED_SUPERSEDED_DIAGNOSTIC`，无完整score；清理后GPU0MiB、8087关闭。
这不是新的引擎失败，也不是完整回放通过。随后启动active状态版原core完整坏例：
`diagnostic_proxy_active_silver_bad17_20261010T214245_506808Z`。
输入位于新的 `active_contact_validation_runtime`，588个受保护原版文件一致；
40入口静态集成与40份内嵌脚本AST/依赖检查通过，分别见
`evidence/active_contact_diagnostic_integration.json`、
`evidence/embedded_script_dependency_audit_20261010T213936Z.json`。
两task active delta SHA：silver `baeea3fe82c2ce78d11d252b9772bc506f3357d7795179318303f3e7a588d39e`，
fehling `366a7c9e520065c302dc0aa2ef03bdd46570e177edb832e427b76959e9f4c372`。

实际银镜场景门控的第一轮1562tick无引擎错，粒子计数96649/13905不变；贴壁、
倾斜、恢复和epoch条件通过，但偏心阶段未产生目标相对位移，命中的是
`tube_touches_beaker`而不是`bath_off_center`，因此该轮总体FAIL，不算偏心资格。
后续修正测试夹具的约束和位姿记录，生产资产保持冻结。

修正银镜夹具 `recovery_active_silver_gate41_03/report.json` 随后通过全部16项，
1562原生tick、0引擎错误，96649/13905粒子数不变；负条件尾30帧确认浴液有效、
试管浸水且加热时间停止，恢复与epoch通过。贴壁段烧杯仍动态，最大活动接触244；
偏心及后续位姿隔离显式约束烧杯，仅证明规则门控，不推广为自由刚体稳定或成功示范。
斐林须以自身场景另外验证。

斐林独立门控 `recovery_active_fehling_gate41/report.json` 同样通过16项，1562个
原生tick、0引擎错误，粒子计数96649/13905不变；范围仍为声明约束下的门控夹具。
后续审查发现初始已休眠且仅收到部分pair的LOST事件时，不能据此宣称所有接触
状态已知。生产者正加强这个late-init边界并另出delta，当前远端输入继续冻结；
当前版本完整回放只能证明它自身及已执行路径，不能替代后续新字节的最终验收。

body CCD独立对照 `recovery_D_active_bodyCCD_prefix700` 于391动作FAIL_ENGINE，
首错为cuEventRecord/cuStreamWaitEvent 700，随后其他求解器报错；虽然早期146帧
指尖穿入有所减小，该变体仍拒绝推广，不能把对照差异宣称为已证明的底层根因。
保留v2物理、不开body CCD；单帧穿入限制继续记录。

更严counter v2已冻结，21项边界测试及SDK生命周期复核通过，后者2346原生tick、
0引擎错、1902个休眠贴壁帧保持门控；实际多shape刚体初次awake PERSIST报告完整性
也经过三个reset轮次核对。新delta SHA：silver
`993cc9b30ab015872e4d2e3345966cf222c0c7ba90a05ed360d2b99f2264662a`，fehling
`7cb770056c479ab55de2bd372e714e26eb5bb05d515468477e5e7871d2fb0e0c`。
集成至 `final_waterbath_validation_runtime` 的40入口静态通过，目录名不代表最终资格；
见 `evidence/active_contact_v2_diagnostic_integration.json`。

最终counter v2本地原动作前缀随后于369动作再次FAIL_ENGINE（672个原生tick），
没有body CCD，也没有contact tensor view。生命周期规则通过不等于物理稳定；
旧active的一条完整原core回放也不能覆盖此失败。最终counter v2的远端bad17
继续只作独立诊断，剩余队列未放行，交付资格仍未建立。生产者开始审查能否减少
数千液体细壳碰撞单元，以独立新候选验证统一开放凸碰撞的保液与接触；尚不认定
形状数量就是根因。见 `evidence/active_contact_v2_runtime_state.json`。

旧active原core诊断 `diagnostic_proxy_active_silver_bad17_20261010T214245_506808Z`
最终完成7000步，score0.15/success_rate0，四路视频全解码、native120与日志错误扫描
通过，退出后GPU0MiB/8087空闲。实现者查看四路0/3500/6999/7000帧：烧杯离开
加热盘并倾斜、液体洒在桌面，试管留在杯旁/杯内而未回架；液体强暗反射和腕视角
裁切保留WARN。仅检查所列帧，不宣称全帧无穿入；旧active结果不覆盖新counter v2
的本地引擎失败。对应原生audit.json内已写目视范围。

本地/远端实际VERSION与GPU驱动只读核对均为Isaac4.1.0-rc.7+4.1.14801.71533b68.gl、
570.153.02、RTX4090/46068MiB，不能把本地失败无证据解释成版本不兼容。
生产者下一shared264候选仅停用试管3745细壳、让264开放管壁代理同时参与PBD；
仍待独立保液/运动和原动作运行，不预先认定形状数量为根因。

随后为缩小实际接收环境中的失败范围，放行当前冻结counter v2的原core文档坏例
诊断队列，等待bad17完整结果后依次跑其余水浴/银镜例；这不是交付资格放行。
`evidence/active_contact_v2_badcase_gate.json` 明确delivery_qualified=false，并冻结
1299个相关配置/资产/task-data/metric文件哈希；本地369动作引擎失败仍保留。
队列遇到原core失败即停止，也可用 `evidence/activev2_queue_stop` 在下一例前停下，
以便更换有新资格的生产者资产。新资产需重新绑定受影响证据。

`five_item_bad_17_activev2_20261010T221121_718390Z` 原core诊断完整完成7000步，
score0.15/success_rate0，四路全解码/native120/错误扫描通过。实现者看四路
0/3500/6999/7000帧：杯仍在加热盘附近、未见旧active-v1诊断那样的大范围洒液，
试管最终斜靠架孔，未认证正确落座；末次遥测PBD_valid=true、heated_seconds=0、
阻断bath_off_center。腕裁切/遮挡仍为WARN，局部SDK369失败仍未被此结果覆盖。
原core队列继续bad06，尚非最终交付资格。

shared264独立10秒静置1202tick通过，但17秒提拉2042tick失败，试管粒子数不变
仍出现275峰值出界。首越界在tick548圆底135度扇区接缝，不靠放宽1mm容差修正。
生产者新底部混合候选保留264粗代理并添加353个PBD底部单元，旧3745细壳inactive；
原生property query确认618个管collider记录，其中617新代理加1个原shape，质量/
质心/惯量与dynamic_control一致。该query只证明解析结果，不证明保液或机器人资格。

底部混合候选 `recovery_bottom_hybrid_silver_02` 随后在银镜独立冷态10秒/提拉17秒
通过，分别1202/2042个native120 tick，两组粒子数不变且逐步outside=0，无引擎
或post-fetch错误。query解释文件明确：管618个parsed记录包括1个disabled原
GlassShell，617个新代理enabled；烧杯260中仍保留其原257液体细壳，不把仅针对
试管的旧fine计数字段推广到烧杯。仍待机器人及斐林自己的资格。

底部混合候选加冻结counter v2的原动作700前缀完成 `PASS_BOUNDED_ENGINE`，
无CCD/无solver变更，仍不推广到完整机器人资格。已按生产者显式层顺序集成至
`shared_tube_validation_runtime`，40场景质量/COM/I、617 enabled/353新底部/144粒子
过滤目标、旧fine inactive、组过滤与依赖闭包通过；见
`evidence/bottom_hybrid_diagnostic_integration.json`。当前旧几何原core诊断队列
收到“bad06完整收尾后停止下一例”标记，以便下一轮验证新候选；不截断当前回合。

混合候选700动作前缀的warmup计数随后核对为279个实际native tick（最初21次
名义world.step未推进），动作0..699各自均恰好1个native tick，总计980。因此保留
为该初始化条件下的限定结果，不称为精确300物理步预热；生产者将补严格计数测试。
原core只读检查另显示 scene.post_initialize 会先等待相机并步进100次，随后
env._setup_episode_layout 执行reset/recovery及配置的300次warmup；其总native计数
还包含前置初始化，不能直接与独立SDK的1002预期值比较。核心文件未修改。

严格native预热复核 `recovery_bottom_hybrid_strict300_prefix700` 完成：reset前置计数1，
实际warmup300，随后700动作各+1tick，总1001；23次未推进调用仅发生在被动启动
预热，无引擎错，fixture未改，实际script SHA仍767ceee5ab61805d37082dac47c738f4325011e9896222b7faad4a1957ccd174。
逐帧0..699几何审计link7/8最大0.10695/0.09410mm，>1mm帧数0；不与279预热
旧run合并。末段杯翻转导致pbd_valid=false，不是任务成功示范。

Fehling混合候选独立冷态10秒与提拉17秒也通过，1202/2042 native ticks，
96649/13905粒子数逐步不变、outside0。新几何下两任务门控与桌面落碰仍在验证。
旧fine bad06原core诊断最终7000步score0.15/sr0，4视频完整解码/native120通过；
实现者查看0/3500/6999/7000四视角，试管横放架顶未正确落座，离水后加热停在
21.16666777秒，bath PBD_valid=true。旧队列在下一例前停止；
`five_item_bad_17_hybrid_20261010T231056_971370Z` 已在新隔离root开始完整原core回放。

原桌面50mm自由落碰在原杯SDF+管hybrid上未通过：最终有效run
`recovery_hybrid_v2_table_drop41_03` 为482tick/0引擎错，管最大穿桌3.400mm
（10帧>1mm，末60帧恢复），杯最大6.544mm且471/480帧>1mm，末段仍振荡。
两者能量峰均小于初值，未见向上弹飞；18958条material-face warning保留。
前两次仅报告numpy标量序列化失败的run按FAIL_HARNESS保留，不补造PASS。

新杯96凸代理与管hybrid617组合的同夹具482tick无引擎错，消除了杯持续穿桌/
振荡及上述material-face warning，但杯第9帧仍穿入1.708mm、管3.401mm且
11帧>1mm，仍FAIL。下一单变量在此新几何组合上测试body CCD；旧CCD失败属于
旧数千细壳+杯SDF组合，既不继承其失败，也不预先认证新组合。各root输入冻结。

新杯凸代理+管hybrid加两bodyCCD的50mm落碰通过：482 native120 tick、0引擎错，
管最大穿入0.08559mm，杯接近数值零，能量峰/初值0.9934/0.9951，末容器稳定，
无World外部子步。对应 `recovery_bath_hybrid_CCD_table_drop41/report.json`。

该组合按[CCD,bath新,active_v2,hybrid,tube_v2,fluid,original]静态接入
`convex_ccd_validation_runtime` 的40入口，管617/杯354 enabled，PBD240目标，
两bodyCCD=true，质量/COM/I与闭包通过。两新层SHA：bath
55f8b67d4e76323a2489ede7faa4d426c165d057df1caa43517a15fbd088d5fb，CCD
59322c1dc23e5e59e3df542700ae51caf14c8edb46423cb2c5ecfe95b9ff3d07。
该静态root未用于原core运行：其直接读取的strict300+700本地probe于278动作
FAIL_ENGINE，首错mArtiSolveBlockPartitionFunction/随后CUDA700。崩前PBD有效、
wall_count266且正确停止加热，指尖>1mm帧数0；不能以落碰通过覆盖此失败。
生产者继续同几何/CCD仅TGS→PGS的单变量对照，尚未认定解决。


PGS单变量对照仍于618动作/native921发生CUDA700，未采用。恢复TGS并仅采用
speculative CCD（两body sweepCCD=false、speculative=true）的50mm落碰通过：
482 native tick，管0.08423mm、杯0.00289mm；机器人前缀先于134动作出现明确
粒子接触容量溢出（需求4373758，配置4194304）。仅将容量增至8388608后，仍于
289动作/native592发生mArtiSolveBlockPartitionFunction/CUDA700；没有先报容量
不足。因此容量调整没有证明解决articulation错误，三条失败分支均不推广。

`speculative_validation_runtime` 已静态整合40入口并修改71份水浴/银镜YAML的
GpuMaxParticleContacts至8388608；去除此键后YAML语义一致。证据为
`evidence/speculative_capacity_8m.json` 与 `speculative_diagnostic_integration.json`。
该root仅诊断，未运行原core、未成为交付；最新生产者试验只减少试管PBD底部角向
分段32→16（353→177形状），质量/COM/I、可见网格、粒子与刚体代理不变，资格待验证。
用户再次确认水浴“允许注明待重采，先交第一轮”；这不改变资产有效性门槛。
规范无需变更：以上为未获联合资格的具体物理配置，不构成通用推荐。


验收索引更新为工作根 `evidence/current_bad_case_acceptance_v2.json`，按receipt的
runtime_root查找视频审计，显式选择冻结称量/滴定的4条坏例并复核记录输入SHA。
当前18条要求中4条通过该证据检查，8条曾有完整历史结果；后者不等于最终资产资格。
本方独立索引工具验证了未选择、输入变更、invalid_attempt均不计入，以及完整零分
结果可以计入坏例证据；它不属于接收方运行依赖，不自动发布资产。


PGS失败分支补充几何审计：0..617动作的link7/8实际最大穿入分别5.758mm
（542）/9.768mm（315），不能把CUDA较晚解释为接触改善。speculative8m分支
0..288动作实际最大穿入0.2209/0.1041mm、无>1mm帧，却仍在289发生CUDA；
当前证据不支持把所有引擎失败统一归因为深夹持。

bottom16银镜冷态夹具通过1202 native120 tick、两液数量不变/outside0；该夹具
禁用任务graph，script SHA e0a311…对应只读物理检查代码，不是任务counter。
任务counter必须在机器人与门控夹具内独立核验767ceee…实际inputs:script。


bottom16提拉2042 tick通过，但strict300+700仅完成329动作即FAIL_ENGINE，native631，
首mArtiSolveBlockPartitionFunction/随后CUDA700；不接入原版评测root。两任务底部
delta虽同字节03aeacf28168f94f05bdd141b9fa9e2fc60fff51e483ad0086ee97799ef991c1，
仍未完成斐林自身保液，也未获联合机器人资格。
过滤核查排除了一个候选原因：原core机器人实际位于/World/_scene/lift2，18个
启用robot collider均属于RigidScene、均不属于Supplement；试管底部177和杯257
则相反。历史四个全凸分支的真实contact header未出现PBD-only形状，详见生产者
recovery_pbd_only_robot_filter_static_audit.json 与 recovery_pbd_only_native_contact_audit.json。
下一结构调查针对杯底多块共面代理带来的冗余接触，尚无根因结论。


杯底floor32→8合并候选复用源坐标，体积相对差1.47e-8；源float缝点使每hull38
顶点，仍低于该GPU凸包限制。两任务delta同SHA
fdf4cf0a663bff6405a3ab37177bfe017795e5c8ef4df85f9296d6e438ca541d。
该候选以tube617/speculative/TGS/8m为基准，未叠bottom16；杯330 enabled、
粒子filter216。50mm落碰482tick通过，管最大0.12784mm、杯0.000325mm，
库存/能量/无弹飞通过；strict机器人仅279动作/native581即FAIL_ENGINE。
因此floor冗余减少未消除CUDA，不推广。生产者将比较连续碰撞路径与普通提前接触
裕量的影响；这只是调查方向，尚无根因结论或参数资格。


以floor8为基准关闭两body sweep/speculative CCD，仅原桌面既有collider设置9mm
contactOffset（restOffset不变）后，50mm落碰482tick通过：管0.1991mm、杯0.00613mm，
无能量增益/弹飞/库存异常。9mm来自此前单步8.19mm跨越的限定证据，原桌自动offset
运行时数值未知，不宣传通用默认。容器0.8mm、加热盘及PBD专用offset均未变。
该组合strict300+700也通过：初始1+300+700=1001原生tick，无零推进动作或引擎错。
raw指尖最大0.10619/0.07513mm、>1mm为0；1000帧当步contact与控制器计数匹配，
脚本仍767ceee…；不把前缀提升为全程成功。

新 `floor8_margin_validation_runtime` 原core9d的40入口静态整合通过：tube617、
bath330、每PBD过滤216、table9mm、两body CCDfalse、质量COMI不变、闭包完整。
强层顺序[table_margin_no_ccd,floor8,bath_new,active_v2,hybrid,tube_v2,fluid,original]，
无旧CCD或bottom16层；生产者完整receipt为
`silver_bad17_diagnostic/recovery_floor8_margin_composition_receipt.json`。
见工作根 `evidence/floor8_margin_diagnostic_integration.json` 与
`floor8margin_frozen_inputs.json`。首个完整原版回放
`five_item_bad_17_floor8margin_20261011T003522_829407Z` 已启动，588受保护blob相同；
两任务各自最终保液/加热门控、该完整回放及其余坏例仍待通过，不是最终交付资格。


上述floor8margin原core首例实际FAIL_ENGINE：286条step记录后，worker1102706于
2026-10-11T00:37:48Z出现mArtiSolveBlockPartitionFunction/CUDA700，client_exit1，
无result_info。helper于00:37:54自行清理；随后独立核实本次4PID均退出、GPU0MiB、
8087释放。没有发送额外终止信号，不把缺失结果记0分；invalid_attempt.json和
cleanup_verified.json保留。SDK700通过不预测原core全程资格，该候选已拒绝，
其余13例未启动。下一回到曾原core7000完成的原杯SDF+hybrid617/noCCD，仅加table9mm，
先验证drop。更新验收索引仍为4条明确选定/18要求，8条有历史完整结果。


被拒绝floor8margin的silver提拉自然收尾2042tick，Sample最大出界1粒、Bath0、
数量不变，无引擎错；原1mm判据保持，记录为FAIL，不因停止后续资格而丢弃此结果。

回原杯SDF+hybrid617/noCCD、仅table9mm的落碰482tick无引擎错，烧杯最大穿入
约0.00111mm，已无持续穿入；试管仍3.040mm，仅218/219帧>1mm。逐顶点核查定位
到倾倒上沿旋转：217→218同点+11.980→-3.040mm，全可见网格最大单步下移
15.124mm，角速约12.3→13rad/s，不能仅以COM竖直速度估算。下一仅table17mm，
加原容器0.8mm形成17.8mm接触裕量，覆盖该限定跨越；rest/PBD/heater/质量不改。
该值不是通用物理默认，不应用于已冻结称量/滴定。原SDF face-index警告20699条
仍保留，需另限解释。依据生产者 angular_impact_audit.json；新结果待验证。


原杯SDF+hybrid617/noCCD/table17mm随后通过50mm落碰482tick：管0.08448mm、
杯0.00138mm，能量/库存/无弹飞通过、rest位置正常，无引擎错。strict300+700
也通过，native总1002（前置2+实际预热300+动作700），每动作1tick、1/120；
保留前置计数差异，不改称1001。新table17层SHA
389448dcceb26936113782cf9b245066c7a895f4a86bd143bdb4414c81c1353a。
新隔离root准备中，仍须原core复验；上述资格不继承被拒绝floor8的未完成检查。


`table17_validation_runtime` 的40入口静态617/260/144、table17、两body CCDfalse、
scriptSHA/质量COMI/闭包通过，1320输入文件冻结。原core首例
`five_item_bad_17_table17_20261011T005347_628509Z` 已启动，588核心blob一致；
独立几何审计700动作指尖最大0.12234/0.16376mm、无>1mm帧，contact1000/1000
同帧匹配。生产者clean6层组合见 recovery_table17_composition_receipt.json。
最终各任务保液/门控和5mm受控落座仍在验证，不能以受控落座冒充成功回架示范。


最终table17两任务各自cold1202/lift2042均PASS，逐步outside0、数量不变；两实际任务
gate各1562tick/16条件PASS。受控5mm c05落座600动作/602native通过，末座高
0.01955mm、倾角1.849°、径向裕量0.50459mm、vz0.0001206m/s，逐步液体outside0。
真实成功回架示范仍待重采，旧120mm自由回架FAIL不覆盖；门控夹具未观测到自然睡眠，
仅按逐字/fixture哈希一致继承counter专门2346tick测试的1902睡眠接触帧逻辑资格。
完整生产者receipt为 recovery_table17_final_qualification.json，consumer核对10组
报告SHA、组合SHA和1320冻结文件后，于工作根 evidence/table17_badcase_gate.json
放行后续13条**原版测试**，仍delivery_qualified=false。

首例five_item_bad_17_table17_20261011T005347_628509Z完整7000步、score0.15/sr0，
client0、四视频完整解码、native120与worker错误扫描通过。实现者亲看四路
0/3500/6999/7000：中途夹管入/近水浴，末管在架孔处倾斜；未见抽样大洒出或消失，
相机有裁切遮挡，不能据此证明所有帧亚毫米无穿入或座深正确。PBD有效、累计加热0，
阻断原因为bath_off_center；保留真实坏例失败。该银镜原仪器OFF静态字样仍可见，
未套用仅task10要求的显示修改。清理核实本次4PID退出、GPU0MiB、8087释放。
后续队列从bad06/unseen_background_8开始；全部18条最终字节验收尚未完成。


第二个最终候选原版坏例 `five_item_bad_06_table17_20261011T012625_608331Z`
完整7000步、score0.15/sr0/client0，native120与4视频完整解码通过、worker物理错0。
实现者亲看四路0/3500/6999/7000：试管中末段横放架顶、未正确插入；未见抽样大洒出
或消失，裁切/遮挡仍WARN。不证明全部帧亚毫米无穿入。native4800/5400/6000/6600
快照加热均21.241667774505913秒，sample_not_in_water、加热false、PBDvalid true，
离水后停止累计。当前继续bad04/unseen_background_3，其余最终字节坏例仍待完成。
40入口脚本AST/编译/生产路径依赖检查通过，证据
`evidence/embedded_script_dependency_audit_20261011T013137Z.json`，40脚本/0失败。


随后bad04 `five_item_bad_04_table17_20261011T015236_021456Z` 与bad05
`five_item_bad_05_table17_20261011T021836_389657Z` 均完整7000步、score0.15/sr0/client0，
四视频完整解码/native120通过、worker物理错0。实现者各亲看四路0/3500/6999/7000：
bad04管横放架顶并伸出架边；bad05末管在架后方倾斜、近景遮挡/裁切，不能确认座深。
没有将任一例视为成功回架，抽帧不证明全部帧微小穿入不存在。两例离水后累计加热
分别约16.19166751和9.67500050秒，heating=false/PBDvalid=true。当前继续bad07，
最终候选水浴/银镜4/14条完整结果已检查，余10条含正在执行者，整包尚未交付。


第五条最终候选坏例bad07 `five_item_bad_07_table17_20261011T024411_914867Z`
完整7000/.15/sr0/client0，四decode/native120/worker健康通过，四路关键帧已亲看：
末管向架后方伸出、被架体遮挡，不能确认正确座深；无抽样大洒出，视觉WARN。
曾在native2400实际启用加热，末6600/7200离水后均16.166667509824038秒，yellowing，
加热false/PBDvalid true。不是成功示范。

第六条bad08 `five_item_bad_08_table17_20261011T031012_762703Z`（task12 mixed5）
在2916条记录后FAIL_ENGINE：worker1230193于2026-10-11T03:19:50Z首mArtiSolveBlockPartitionFunction，
随后CUDA700。client1，无完整result，不能记0分。队列自动stopped_on_failure；另设
stop标记及 `evidence/table17_badcase_gate_revocation.json` 保留原测试放行记录并撤销
后续放行。核实旧queue/server/client/worker退出、GPU0MiB、8087释放，无额外kill。
五个完整通过的局部坏例不能掩盖此反例，table17仍不具备最终交付资格。

实现者亲看partial merged视频2600/2800/2870/2900/2914：先在浴杯处夹管，随后移向
架子，最后夹爪下降到架顶附近，管被双指遮挡；本次触发位于回架阶段，不能套用此前
杯内耦合结论。生产者恢复task12 mixed5复现，原动作附近未见巨大joint-target跳变；
只在独立诊断fixture增加finger接触报告遥测，不改变机器人源文件、驱动或碰撞，也
不把诊断观测层当成交付。截图见 `evidence/mixed5_native_failure_frames`。


针对bad08的独立SDK前3200动作通过（native3502/error0），未重现原core失败，因此
不撤销原core反例。指令邻域joint-target最大单步变化约0.01221、抓指未在2915附近
突变；原rack实际为19个启用collision prim（15852顶点Mesh、approximation=none，
加18槽底Cylinder），残留SDF属性不等于当前SDF碰撞；首错前无明确PhysX cooking或
容量overflow。生产者将生成仅只读遥测的原core诊断USD：任务脚本追加位姿/接触记录，
finger报告API在独立robot wrapper中预声明，避免原create_robot对场景预声明lift2报
already exists。不修改共享robot源文件、驱动、碰撞、质量或GenManip核心；新root明确
instrumented diagnostic，包装层不会交付，也不算原机器人字节的最终验收。


原core只读观测层静态整合至mixed5_trace_runtime：场景无预声明lift2、原task脚本完整
前缀保留，诊断脚本SHA f54df3f46a91c7f93a96113193987fe4e67255e30a26d8b1beaac94d9f4f01c9。
独立robot入口只附加四finger ContactReportAPI，2894非report属性/关系与源一致，
共享源未写；仅临时YAML cap7000→3200。smoke为接口验证，不算task成功。

`diagnostic_proxy_mixed5_trace_20261011T035548_754705Z` 在2918记录后重现原core
CUDA700（04:05:22，原无trace2916），client1无result。884POSE/58562CONTACT、
DIAG_ERROR0；末有效native3332，每tick1/120。末管/指速度仍小，不能直接归因于先
发生高速弹飞。原版观测和SDK近似存在姿态差异，生产者按实际contact shape解析。
本次4PID退出、GPU0MiB/8087释放已核实；未将观测层写入交付或原机器人源。
详情为工作根 evidence/mixed5_trace_integration.json、mixed5_trace_log_index.json，
以及run内diagnostic_scope.json / invalid_attempt.json / cleanup_verified.json。


原版trace归因：末31个有效native tick中，管-架接触集中于Cube_015静态三角网格与
53个rigid底部shape，峰371点/tick、最深SDK separation约-0.2008mm，主要法向Z；
PBD-only shape命中仍0。故不能沿用独立SDK的40°/2.162mm姿态来解释原版。
SDK/native按实际左臂关节对齐得到native_index-SDK_action=415，关节差极小，但
首次观测到管位置差>1mm时已约15.23mm，末差41.23mm，表明抓取后物体状态分歧。
原版证据优先；生产者评估局部冗余底部接触的最小合并，须保持源边界与内腔，尚无新
物理候选。详见producer recovery_bad08_native_trace_analysis 下rack_attribution.json
及SDK_native_alignment.json，均不提升为全局根因定论。


新增 solidcap 候选仅重新划分管底真实实心玻璃：在内腔最低点以下0.1µm处切分，
48个底块的下部合成49顶点凸帽，其余上部仍保留。未把凹内腔用凸包填平；
源边界、质量/COM/惯量、粒子与动作不变。整体tube collider为618（原617），
不是全局减shape方案。生产者482tick落桌、602tick受限回架夹具通过；这不替代原core。
原core独立诊断 `diagnostic_proxy_mixed5_solidcap_trace_20261011T044321_529017Z`
运行于solidcap_trace_runtime，traceV2记录精确负/非负separation点数；机器人只读
report wrapper仍仅供诊断，588个原core受保护blob核对一致。当前尚未获得完整结果。
生产者路径为silver_bad17_diagnostic/recovery_bad08_solidcap_composition_receipt.json；
本方evidence/solidcap_trace_integration.json及run内diagnostic_scope.json绑定新增输入。
用户再次确认水浴首轮允许待重采；该限制不代表允许把引擎崩溃归为正常坏例。
规范无需变更：本次为特定资产/运行时的局部候选，未形成可推广物理默认值。


solidcap短诊断完成3200动作，score=.15/sr0/client0，worker物理/诊断错误0；四视频
完整解码与native120检查通过，实现者抽看0/1600/3199/3200，末管在夹爪与架子附近
倾斜、样液绿色，未认定正常落座。旧故障31tick窗口接触峰371→262，总10920→7764，
但旧负点只有233–2260界限，新精确862，不能声称负点总数下降或单一根因已证实。
只读observer不进入新solidcap_validation_runtime；40入口闭包/40脚本检查通过，原
robot SHA dbdc4f695d7c3e760b99a369e092b1dd0d20e9fee7cca6c5fca9ba46fb1033df。
原7000配置完整bad08于04:58启动，run five_item_bad_08_solidcap_20261011T045813_143650Z。

新cap资格仍未通过：Fehling cold1202 PASS，但lift2042 FAIL（Sample最大outside1，
Bath0，inventory不变，native120无error）。首违例750、管局部z=-1.40005mm、近轴心，
不是已证实的管口溢出；生产者继续定位。lift report SHA
f866c4cf1e433190db17c71ca35eaec4b844711ef1a05d20785c01114492e664，位于producer
silver_bad17_diagnostic/recovery_solidcap_fehling_lift41/report.json。
夹具队列自动停止，未放行新整批gate。原core短程无崩溃不能覆盖保液失败。


新增paired只读lift排查：旧table17 PASS2042/outside0，新solidcap FAIL2042，
同实际container位姿逐步严格一致；新粒子9152于native734..2042连续1309tick越界。
local z732=1.012266mm、733=.546336mm、734=-1.399815mm，与薄Floor进入下半后
被纠正到下表面的解释相容，但无PBD法向遥测，标为推断而非已证实根因。
原Floor0..1.1mm，新realglass cap0...9999mm；候选sharedcap只禁用Floor并从两PBD
filter中取消cap（145→144），其余352环片不动。层SHA
2f812934b2a8e7ca230bc7119b24a8c0c4cddac93df5a944bf7d2703dd650327。
静态40entry成立，但sharedcap lift也FAIL，首次492、局部z=-.781596mm。
因此sharedcap_validation_runtime未启动原core资格或整批gate，不可交付。
下一单变量由producer评估solidcap原几何上的Sample PBD位置迭代64→128；
Bath、rigid及World原生120Hz不变，尚无验证结论。内部求解迭代不等于新增World子步。


原solidcap/PBD64完整bad08完成7000/score.15/sr0/client0，全部worker无引擎错误，
四视频全解码/native120通过。实现者亲看0/3500/6999/7000：末试管斜搭架顶并向
前右侧伸出、绿色样液在低端，不是正常归槽。清理核实helper1294170/server1294193/
client1295567与该runtime cwd进程全部退出，GPU0MiB/8087空。仍因独立liftFAIL保留
为未合格候选历史，不据此交付。

Sample128单变量lift完整PASS2042/outside0/error0，wall241.151s包含启动/收尾，
report SHA dd6fdd79a2b7f18783b51f7e5f8c4878e416fefce94666c576852c3bfd6b6022。
层SHA08e109418a6215a6d60dc0586d9d11f3a2a36a7d93898b72db340cf744c857aa，
仅Sample PBD solverPositionIterationCount64→128；Bath/rigid/Worlddt不变。
新pbd128_validation_runtime从solidcap原Floor组合，明确不包含已失败sharedcap。
尚待其余生产者资格与新字节完整原core坏例，不能将单个lift PASS写成最终通过。


PBD128原core fullbad08于05:33:02启动，run
five_item_bad_08_pbd128_20261011T053302_157711Z，588受保护blob不变。
40入口与40脚本静态审计通过。初次消费检查误用了带physxParticleSystem前缀的属性名，
实际schema为solverPositionIterationCount；仅修正本方检查后逐场景确认Sample128/Bath64，
未改生产者物理字节。任务资产迭代仍需新原core完整结果与producer资格。

本方打包检查发现局部runtime没有09/10资产和taskdata；其草稿清单已标INVALID且未归档。
inventory新增存在性与20入口检查，archive builder在创建目录前强制四任务三类离线树完整。
用完整历史清单、无效局部清单、伪标DRAFT的局部清单三个对照验证，结果均符合预期，
未建立新归档。此工具仅本方制作辅助，最终无接收方依赖；操作说明同步完整基线来源。


关键资格纠正（05:45）：schema文档说明scene maxPositionIterationCount对particles等
对象设上限；此前probe与native YAML场景Min/Max均64。因此作者Sample128属性不能
等同有效128迭代，前述cold/lift PASS只记录该实际组合，不证明128收敛改善。
两处native YAML（generation/evaluation）仍Max64已确认。05:45:07主动SIGINT本次
helper1321116，由其finally清理本次client/server；保存INVALID_FOR_EFFECTIVE_PBD128_COMPARISON，
不把停止后的缺结果记0分。原solidcap64已完成的7000结果保留。
producer核对rigid/Articulation与Bath个体请求，后续若采用Sample128必须同步sceneMax128，
min64/World120Hz不变，并重新绑定probe、actualgate和native配置。没有整批放行gate。


用户追加确认：LeRobot沿用v2.1并注明已验证隔离环境（LeRobot0.1/datasets3.6/
torch2.10/av16.1，pyav）；不再悬置格式选择。水浴/银镜首轮保持7000步，重采再调
完整时间预算；称量4000不变。58.333秒对部分59–60秒单加热需求不足的限制随交付保留，
不改阶段权重、原动作或上限来制造首轮成功。


短SDK上限查询补证：各reset2+3tick，scene64/64时DynamicControl Articulation属性64，
scene64/128时属性128，原USD/loader请求均128；三独立刚体DC属性均64，28robot link
属性16由Articulation控制，不能当独立每帧循环数。getter不是内部实际迭代循环遥测。
因此不加入任何robot setter/USD隐藏控制来强求单变量；下一合法候选为保留原机器人
请求128，并让Sample128与sceneMax128/min64一致，明确是组合改动。

scene128_validation_runtime由pbd128 root克隆：只改两任务71份YAML中
MaxPositionIterationCount64→128（generation/evaluation），递归语义比较其他字段相同，
1254个冻结非YAML输入哈希一致；原goal/7000steps/120Hz/robot/core不变。
receipt为evidence/scene128_validation_integration.json，尚未原core运行，待正确上限
producer lift。旧author128/sceneMax64本次停止已核实3PID及runtime cwd进程退出、GPU0/8087空。


scene128九组生产者资格齐：两cold1202、两lift2042、两实际gate1562/16项、
50mm原桌drop482、5mm受限c05回架602、strict300warmup+700动作共1002native。
后者双指raw最大穿入.10709/.11204mm，>1mm均0，实际同时接触588动作；SDK深度
.12768/.15776mm。drop最大tube .09832mm/bath .06664mm；rack末gap .02946mm、
tilt1.7807°、径向余量+.54695mm、outside0。原始64上限报告不继承物理资格，
仅同字节counter lifecycle逻辑可复用。producer23测试PASS，提交8309755/bbd0727，GPU已空。
资格receipt SHA670ebb0477ebc5888c3626fbc7239bc5f5ea56b99b6ba0f50e93e80f0a711792，
bounded_producer_qualified=true，delivery_qualified=false；受限drop/rack不等于任意投掷/成功示范。

新原core bad08 full7000完成06:31:04，score.15/sr0/client0、错误0；四视频全解码、
native120检查通过。实现者亲看0/3500/6999/7000：末管水平落在架子与加热器旁桌面，
不是归槽；终态内容遮挡，不能凭图宣称无洒漏。native7200遥测PBD_valid=true、有效
加热17.266667567s，sample_not_in_water停止累计。helper1339235/server1339295/client1340663及
runtime cwd进程退出，GPU0/8087空；receipt/audit/cleanup均保存。

核对producer九报告、71配置、全部物理层与首条结果/四视频/人工抽帧/1325冻结输入后，
06:34:54仅放行剩余13条测试队列（PID1367681）。gate=evidence/scene128_badcase_gate.json，
原core顺序17,9,10,11,12,13,14,15,16,6,4,5,7。仍需全队列及最终闭包/完整四任务归档，
未推广为最终交付，不改jiantong目录。规范无需变更：以上只支持具体运行时和限定任务动作。
