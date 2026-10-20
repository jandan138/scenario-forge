# Task18：引擎异常隔离与材质更新候选

本记录续接 [Task18 交付准备](2026-10-20-task18-silver-mirror-delivery-preparation.md)。当前未交付，未安装建通目录，未发布 READY。运行机日志仍使用 2026-10-20 UTC 时间，保留原 run ID，不按本记录日期重命名。

## 已确认的结果

实验根目录：
`/cpfs/user/zhuzihou/dev/task18-silver-delivery-20261020`

- v3 的 mixed_3 曾发生 CUDA700；后续启用与移除接触报告的对照均完成 7000 步，因此不能把移除报告称为引擎修复。
- v4 移除了“碰壁不再停表，但可选接触采集器异常仍会中断加热”的依赖。实际函数回归在 v3 失败、v4 通过。这是逻辑修复；v4 mixed_3 仍在已确认 2940 动作之后发生 CUDA700，故未获得稳定性资格。
- 私有夹爪 10N 试验仍发生 CUDA700，不进入交付。机器人原始资产和 GenManip 核心未修改。
- 三组私有诊断均完成 7000 步、0.15 分、无记录到的引擎错误：真实粒子但暂停反应；禁用液体并暂停反应；完整 v4 加 CUDA 同步执行环境。见 `evidence/physics_isolation_queue.json`。这些结果只缩小调查范围，不能单轮确认因果，更不能把停反应、去液体作为交付方案。

## 显色演示已有证据

`controlled_v4/report.json` 完成规定的 84 秒无机器人夹具试验。原生步长约 1/120 秒；银镜进度到 1，重置到 0；样液全部保持在测量容器范围内。水浴记录的 72 次离开范围事件均为开口上方、开口半径以内，结束时所有粒子回到范围内；不能解释成持续漏液，也不推广为任意轨迹防漏。

亲自检查 0、20、36、60、77、83 秒画面：初始透明、早期暗色沉积、逐渐形成反光银镜、移出后保留、重置透明。初始及移出阶段的试管顶部超出构图。检查的是抽帧，不是逐帧碰撞认证，也不是机器人成功示范。报告见 `evidence/controlled_v4_review.json`。

## v5 改动和当前验证

v5 仅对不变的材质／可见性值省略重复 USD 写入，Float32 值先按 USD 精度归一化；数值状态、物理参数、动作、反应时长、评分不变。同时补齐 mixed_7 残留的旧碰壁说明。它针对可能的重复更新干扰，目前没有证明这是 CUDA 根因。

验证已通过：

- 实际 v4/v5 内嵌函数在 13 个输入点（含重复值、完整反应和重置）的 USD 属性值一致。
- Float32 的 0.18 重复写入 100 次不产生更新，改变到 0.19 时仍正确更新。
- 9 项规则测试、可选接触采集器独立性回归。
- 20 场景依赖闭包、原始 PhysX schema、20 配置 120Hz/7000 步、原反应时间及冻结哈希。

证据：`evidence/v5_visual_equivalence.json`、`evidence/static_candidate_v5.json`；测试脚本位于外部实验根的 `tools/`。

远端 `10.150.164.127`：

- GPU3：v5 mixed_3 原动作完整回放；成功后自动重复一次，任一异常则暂停该队列并保留失败。
- GPU0：v5 无机器人完整显色、液体检查与重置渲染。

已启动自动衔接协调器：两次 mixed_3 完整回放均通过后，等待对应 GPU 锁释放，分三路运行其余八条文档坏例。任一引擎／运行异常阻止后续入队；已在运行的作业保留自己的日志和收尾。见 `evidence/v5_schedule.json`、`evidence/v5_coordinator.json`。所有完成结果仍须画面复核，协调器不会自行安装或发布 READY。

当前状态入口：实验根 `CURRENT_STATUS.json`。上述队列启动不等于验证通过。

## 接收端准备与原版补充对照

再次读取飞书文档，revision 6888 的 Task18 修复项未变。除原目标外显式核对了背景容器碰撞：v5 解包后的 20 场景均有 5 个背景物件、每场景 27 个启用且有效的碰撞形状。见 `evidence/v5_background_collisions.json`；结构存在不代表动态接触已经认证。

`receiver_v5` 从建通 HEAD `9490df9a3710bbcea97cd2470adc364a13883914` 重新克隆，实际解压 `provisional_v5/task18_offline_PROVISIONAL.zip` 中 562 个离线文件，仅另放入 1 个指定 metric 文件。全部哈希与候选一致；公共 `repair_checks.py` 与接收基线相同，未覆盖。制作脚本未复制进接收目录，已有机器人／公共材质继续引用接收基线。

这是个人目录中的隔离验证，不是安装；归档旁有 `NOT_READY`。见 `evidence/receiver_v5_preparation.json`。

接收端自动队列已准备并等待候选九条坏例及关键重复回放、受控演示数值通过，之后分四卡执行 20 配置初始化、视频解码和 80 张图提取。画面审核、代表完整回放及最终安装仍须后续完成，初始化协调器不发布 READY。

另外启动 GPU1 的原版 mixed_3 同动作完整回放，补充此前只覆盖 mixed_17/mixed_20 的原版校准范围。见 `evidence/original_mixed3_baseline_queue.json`；运行完成前不作结论。

## v5 受控演示与实际 metric 方法复核

v5 无机器人演示现已完成：84 秒、2520 帧，原生 10082 个步事件（含初始化步），银镜进度 1、重置后 0；样液测量保留率最低 100%。浴水 285 次范围离开事件均位于开口上方且半径内，最终外部粒子列表为空。12 个阶段画面已亲自查看，完整 MP4 已解码，报告与视频哈希保存于 `evidence/controlled_v5_review.json`。该结论仅覆盖规定夹具轨迹；试管顶部在初始／移出构图中部分被裁切，浸入显色区域可见。

仿真完成后的封装脚本曾因批量版本名替换把 `yuv420p` 错改为 `yuv520p` 而失败；已修正并从原始帧编码，不重跑或改写仿真。原 launcher 失败日志保留。仿真日志的唯一通用错误扫描命中是 `SimulationApp` 导入弃用提示中的 Traceback 字样，已核实其处于明确 DEPRECATION WARNING 区段，不是运行异常。

实际 metric 的 `check_status` 方法与未修改的几何桥接函数另完成 12 项检查，使用真实 USD 相对变换：竖直落座通过；架顶悬置、横放、架外拒绝；运行错误与液体无效拒绝；50%/95%仍保持严格大于边界。见 `evidence/v5_actual_metric_tests.json`。只在内存中改动测试姿态，不保存资产，不等同于机器人实际回架资格。

个人暂存包增加 `README_DRAFT.md`，明确原始时间预算限制（7000/120=58.33秒，mixed_18完整反应终点59.48秒）、无机器人证据范围及未完成的交付门槛；没有发布 READY。

## mixed_3 第一轮完成及液体有效性追查

v5 第一轮 `silver_v5_g3_0_mixed_3_20261020T172304_998275Z` 已正常结束：7000 步、0.15 分、client_exit=0、无引擎错误，四路 MP4 完整解码。7000 条 arm_action（含夹爪）及 base_motion 与原记录逐项一致。关节最大单步变化约 0.082 rad，底座记录最大单步变化约 0.000155。第二轮自动复跑已启动，单轮无错不能关闭间歇性错误问题。

第一轮四路各 12 帧已查看：试管被提起、保持在杯旁，随后释放在加热器附近；没有有效入水／显色和回架成功。所查画面未见大幅弹飞，但试管底部在部分画面被加热器遮挡，不能宣称逐帧无穿透。证据在 `v5_first_mixed3_review/`。

周期状态从 native_count=3600 起报告液体无效，`water_surface_z` 随后接近杯底。检查实际控制器发现：当杯内粒子比例低于99%时，函数返回杯底的退化占位 profile。因此“液面到底”不能被当作整杯水漏光的测量，更不能直接证明漏壁或正常洒水。GPU2 已启动独立 `mixed3_v5_liquid_observer` 副本，仅在已有粒子局部坐标计算处增加包含比例、杯体姿态、越界分类记录；阈值、物理和动作不变，诊断代码不进入交付。见 `evidence/v5_liquid_observer_identity.json`。

原版同动作 `silver_original_mixed3_baseline_20261020T172649_249659Z` 亦完成 7000 步、0.15 分、无引擎错误。全部7001帧关节／夹爪／底座状态与原记录逐项相等，补齐这条来源的协议校准；不据此推断物体接触状态一致。见 `evidence/original_mixed3_state_comparison.json`。

20场景内嵌脚本的制作侧路径检查未发现 `/cpfs`、`/mnt/data`、`/shared` 或自行追加模块路径；模块依赖见 `evidence/v5_script_dependency_audit.json`。这不能替代后续接收运行验收。

## 独立 metric 交付文件暂存

在个人隔离接收仓库生成提交 `f0dedfb29b2561e7f92bc4371fdcae43af555acd`，父提交为建通基线 `9490df9a3710bbcea97cd2470adc364a13883914`，只修改 `genmanip/extensions/metrics/scientific_experiments/task_z4_silver_mirror_reaction.py`。已有工作区文件字节未因此改变；后续接收验证将记录此提交。

`provisional_v5/code/` 中 bundle 和 mbox 是同一改动的两种选择，均标记 PROVISIONAL。已在建通仓库执行只读 `git bundle verify` 与 `git apply --check`，两项通过；没有应用补丁、切换建通分支或安装离线包。回执和文件哈希见 `evidence/metric_commit_preparation.json`。仍需完成运行资格，不能把“补丁能应用”当成可交付。

## 浴水杯底越界已复现，批量入队暂停

私有粒子观察器在 native_index=3293 记录同时28颗位于参考杯底以下，包含率0.987931；累计30次由内到外的转换分类为 `below_floor`，不能把30次直接解释为30颗独立粒子。此前2640/3240的周期记录仍为全部包含。触发时杯体原点高度约0.83159m，先前约0.826m，伴随短暂倾斜；后续部分粒子仍在杯外。这不是“全部水漏光”，但也不能按杯口正常溅出放行。正在完成该诊断全程，参考轮结果不保证每次完全相同。

已写入 `evidence/v5_global_stop.json` 暂停批量坏例和接收初始化的新入队，现有第二次关键回放及液体诊断继续正常收尾。暂停原因是液体物理证据，不是把低分当失败，也不是新增引擎报错。v5演示和metric局部检查仍保留其原有范围，不能覆盖这次机器人接触条件。

原浴水配置 maxVelocity≈0.3m/s、粒子CCD关闭；粒子平滑明确关闭。杯体活动碰撞仍为原SDF主体／杯沿等，旧 `WaterbathCollision/Floor` 的碰撞为关闭状态，不能误把它的偏移参数当作当前活动杯底。没有为本次试验启用旧碰撞代理。

新增两项单参数试验，静态逐属性对照确认每项仅改变一个属性：GPU0最大速度1.0m/s，GPU1开启粒子CCD，均保留诊断日志、120Hz、7000步、原动作和评分。身份与运行入口为 `evidence/bath_motion_trials_identity.json` 和 `evidence/bath_motion_trials_queue.json`。这些仍是私有诊断，不进入交付，尚不能认定限速就是原因。

参数含义核对 [NVIDIA PhysxParticleSystem 文档](https://docs.omniverse.nvidia.com/kit/docs/omni_usd_schema_physics/latest/physxschema/class_physx_schema_physx_particle_system.html)：maxVelocity限制粒子速度，enableCCD用于帮助减少粒子穿透。文档支持试验方向，不保证该Isaac4.1场景的修复结果；本任务具体取值不提升为通用规范。

## 提速试验退化并提前终止

maxVelocity=1.0 单参数试验明显退化：native120 时包含率约0.861，native600时约0.367，1468颗处于参考杯底以下，记录的粒子世界Z最低约−2.938m。已经不是边界少量误差。仅终止该试验拥有的客户端进程组，由原生 helper 完成服务清理；client_exit=-15、服务已退出。保留 `evidence/bath_vmax1_rejection.json`、原始日志及 `bath_vmax1_observer_rows.json`，不把它记为完整7000步失败分数，不提升至候选。

只开启CCD的一组仍在运行，早期记录全部包含，未得出最终结论。追加其对应 mixed_3 场景的无机器人受控显色／重置验证，沿用该场景原始反应时间；GPU3在原有回放释放锁后自动启动，入口 `tools/run_controlled_bath_ccd.py`。该无机器人夹具及粒子观察代码仍仅属于诊断，不随正式包交付。

v5关键 mixed_3 的第二轮已完成，两个回放均为7000步、0.15分、无引擎报错，四路视频均完成解码。该重复结果单独保留；由于浴水杯底越界尚待解决，不能据此恢复正式验收入队。当前对照快照入口为 `evidence/bath_motion_comparison_snapshot.json`，其中周期最小值是所记录样本范围，越界累计次数不等于独立粒子数量。

## CCD 单独不足，核对几何后测试接触检测距离

CCD组跨过原事件阶段后也出现越界：native3293包含率0.987931，27颗分类在参考杯底以下、1颗径向越界；native3720有30颗留在容器范围外，累计记录35次杯底、3次径向离开事件。不能以此前native3000全部包含的中途状态宣布通过。该组继续收齐其运行产物，未提升为正式候选。

进一步检查了活动杯身网格相对杯体的顶点高度：外底0m、内底0.003m、口沿0.11349m。测量profile内底0.003000000026m与实际内底吻合，没有证据支持放宽包含阈值或修改测量基准。见 `evidence/bath_floor_geometry_audit.json`；这仍不等于已测得运行时SDF的逐点接触面。

下一项单参数对照只把浴水 `contactOffset` 从引擎自动值设为0.015m；保持 `restOffset=0.005m`、粒子间距、粒子数、maxVelocity≈0.3m/s、CCD关闭及其余参数不变。改的是粒子与非粒子物体的接触检测距离，不是液体粒径或体积。静态逐属性对照确认仅此一个差异，GPU2启动原动作完整回放与相同的粒子观察记录。见 `evidence/bath_contact15_trial_identity.json`、`evidence/bath_contact15_trial_queue.json`。效果尚未验证，不作通过声明。

## 接触距离对照未解决，追加位置一致性诊断

contactOffset=0.015m在native3293仍触发保护：同时41颗超出参考范围（32颗在杯底以下、9颗径向越界），包含率0.982328；native3840仍有39颗在范围外。该参数不能关闭问题，保留本次回放收尾产物，不继续叠加未经隔离的参数。

另在GPU3启动只读位置一致性诊断：同一次计算内比较 dynamic-control 杯体位姿与自动写回USD的杯体位姿，并分别计算相同粒子的包含比例／局部Z范围。未修改物理参数、实际守卫、动作或评分。早期native480两者一致，但必须继续覆盖问题阶段，不能把早期一致推广到发生碰撞时。身份与队列见 `evidence/liquid_pose_coherence_identity.json`、`evidence/liquid_pose_coherence_queue.json`。

读取并保存了远端实际Isaac4.1 `PhysxParticleSystem` schema片段至 `evidence/native41_particle_system_schema.txt`，确认该版本的contactOffset/restOffset定义及合法关系。不能仅凭不同版本网页缺少某个方法名认定资产参数无效；本轮接触距离对照确实只改变了受支持的contactOffset。

## 杯体位置一致，但仍单独核对粒子读取阶段

位置一致性诊断此次在native2317出现无效状态，两种杯体位姿计算的包含率同为0.968966，位移差为0，局部最低Z约−0.00691m。该回放中杯体后来移离加热器，不能把它当作前几轮完全相同的接触轨迹。见 `evidence/liquid_pose_coherence_snapshot.json`。

这份比较只证明所查杯体位姿一致，不能单独证明粒子写回时机与杯体相同。因此新增同一场景内的只读 `post-Kit-update` 粒子／杯体观察器，保留原 compute 阶段日志以便同轮比较，不改变实际物理或评分。已在GPU0启动，身份与队列为 `evidence/post_update_observer_identity.json`、`evidence/post_update_observer_queue.json`。

观察器早期记录到SDK初始化中的零物理位姿及较大采样间隔：这些启动瞬态不作为动作阶段的漏液证据，也不把累计的初始化越界计数当成实际丢失粒子数。正式动作阶段已出现native720、step_gap=1、杯体位置一致且全部包含的记录；仍需继续覆盖碰撞阶段。判断会区分采样阶段与时间间隔，不凭事件API名称直接宣布物理同步。

## 同轮帧后记录确认越界，组合提速仍失败

新增分析按worker日志的 `Reset complete` 时间分隔初始化与动作阶段，并扣除最后一条初始化快照的累计事件。native3292时compute与post-update两份记录相同：包含率0.985776，33颗在范围外，其中18颗低于参考杯底、15颗径向越界；帧后采样step_gap=1，杯体USD/DC位移差0，局部最低Z约−0.001313m。见 `evidence/post_update_phase_analysis.json`。不能把本次越界归因于前述初始化零位姿或仅仅是杯体位置不同步。

基于分项实验，又分别测试了maxVelocity=1.0与contactOffset=0.015、maxVelocity=1.0与CCD开启的两项组合，均未改其他液体参数、粒子数、时间或评分。两者均发生大量早期漏失（约六成粒子超出范围，出现负世界Z），已仅终止各自拥有的客户端进程组并由helper清理服务，不记为完整7000步分数。身份与拒绝回执为 `evidence/bath_combination_trials_identity.json`、`evidence/bath_combination_rejections.json`。停止继续沿提速方向扩展。

诊断目录多层shared clone遇到Git alternates嵌套深度限制；失败构建保留，后续实验直接从建通基线克隆Git对象，再复制明确的候选任务文件，避免继续增加对象库引用深度。没有修改运行中的源目录。

## 统一SDF碰撞网格细分试验

实际杯身网格闭合、绕序一致，768个四边形在碰撞三角化后为1536个三角形，但最长边约113.5mm。参考 [NVIDIA 对 SDF／凸包夹取弹跳的说明](https://forums.developer.nvidia.com/t/sdf-and-convex-hull-collision-bounces/288053)，大三角形的接触采样可能影响动态物体的碰撞表现；这是本任务待验证推断，不是已定位根因。

准备了不平滑、共边一致的线性细分工具，验证封闭性、绕序、面积、体积和边界。实际先运行最大边10mm候选：46592个三角形，实际最长边约9.451mm，体积相对差约3.3e-9，边界不变。另准备的5mm版本未启动，不宣称有运行证据。

原视觉杯身原样保留，只关闭其碰撞；一个隐藏的同形状细分SDF碰撞网格替换原杯身碰撞，同时服务固体和液体。杯沿／壶嘴保持原样，启用的烧杯碰撞形状总数仍为3；没有新增一套液体专用保液面。浴水速度、粒子数、初态、厚度、体积、metric和动作均不变。

GPU1已启动 `silver_v5_refined_beaker10` 原动作完整回放，初期已正常步进、保液比例1。静态证明不能代替完整运行。证据：`evidence/refined_beaker10_trial_identity.json`、`evidence/refined_beaker10_trial_queue.json`；工具全部留在外部实验根，不进入Scenario Forge核心层或接收运行依赖。

## 细分网格仍越界，转向杯体接触动力学对照

10mm细分网格在native3293仍出现41颗范围外粒子，其中37颗低于参考杯底；native3720尚有46颗在范围外。故没有将它提升为最终资产，也没有用其静态几何通过覆盖运行失败。

下一组回到原始v5几何与液体设置，仅分别调整烧杯刚体属性：GPU0将 `physxRigidBody:maxDepenetrationVelocity` 设为0.1m/s，GPU2开启 `physxRigidBody:enableSpeculativeCCD`。前者限制求解器为分离重叠而引入的修正速度，不是全局运动限速；后者是杯体的预测接触，与此前浴水粒子CCD不同。保持动态刚体，不固定、不转kinematic，不改变机器人、粒子参数、动作、时间或评分。额外只读记录杯体线速度和角速度。

参数定义核对远端Isaac4.1 schema并保存于 `evidence/native41_rigid_body_schema.txt`。逐属性检查确认每组只有一个物理字段改变，另一个脚本差异仅为速度记录。身份和队列：`evidence/beaker_dynamics_trials_identity.json`、`evidence/beaker_dynamics_trials_queue.json`。两组已启动，尚无修复结论。

同时排查质量解释：远端 `particleUtils.py` 将单粒质量乘粒子数后写入 `PhysicsMassAPI.mass`；现有浴水约0.349095kg是总质量，样液总质量约0.004kg，烧杯0.18kg。逐粒自定义记录与总量相符，未发现“将总质量误作每粒质量”的证据，未修改质量。见 `evidence/particle_mass_authoring_audit.json`；这不是独立的运行时测力校准。

## 刚体参数未通过；发现并封闭杯底微小贯通孔

maxDepenetrationVelocity=0.1试验在关键接触附近发生CUDA非法内存访问，client_exit=1且无完整result，不能因回执error字段为空而认为无错误。日志摘录见 `evidence/beaker_depen01_engine_failure.json`。烧杯speculativeCCD试验在native3294仍有30颗低于参考杯底，native3480仍有28颗，亦不能放行。

进一步检查原杯身拓扑，底面中心有两圈各128个顶点、半径约1e-7m的环，之间由128个面连接，形成贯穿3mm杯底的极细轴向通道。原网格作为玻璃实体是封闭且绕序一致的，但这不等于容器底部没有通道：原三角网格Euler特征为0。

新增独立几何试验将两圈分别合并为对应高度的中心点，去掉退化的轴向面，保留底面三角扇。修复后仍封闭、绕序一致，Euler特征为2；三角形由1536降到1024，边界不变，体积增量约9.4e-17m³。只替换统一SDF碰撞，原外观网格保留；不叠加先前失败的细分、提速或刚体参数改动。该孔对运行失败的因果作用尚未证明。

GPU3启动原动作完整回放。身份与队列为 `evidence/sealed_beaker_trial_identity.json`、`evidence/sealed_beaker_trial_queue.json`。本次静态发现属于现有MAT-003开口／封口语义检查范围，暂不新增通用参数规则；不会据此静默重写已交付的水浴或其他历史包。

## 封孔未解决；统一凸分块杯身获得首个完整保液结果

封孔版本仍在native3293出现60颗范围外粒子（50颗杯底、10颗径向），后续仍有漏失。该微孔是几何事实，但未证明是本次故障根因，未将封孔试验当作修复通过。

改用已有凸分块表示作独立碰撞路径对照：关闭原杯身SDF碰撞，启用256个凸壁块及1个凸底面；底面半径扩到原外底轮廓37.27mm，高度仍0–3mm。保留原杯沿SDF与壶嘴碰撞。将烧杯分块从Supplement成员及RigidScene排除列表中移除，使全部烧杯碰撞同时服务固体和液体。共259个启用形状，外观不变，没有独立液体保液层；这是32边分块近似，不宣称与SDF几何逐点等价。见 `evidence/convex_body_trial_identity.json`。

`silver_v5_convex_body_20261020T194319_968247Z` 已完成7000步、0.15分、无引擎错误；7000条手臂（含夹爪）和底座动作逐项与源记录相同，四路视频完整解码。按Reset complete分隔后，compute及post-update记录的最小包含率均为1.0，动作阶段新增越界事件为0。证据：`evidence/convex_body_phase_analysis.json`、`evidence/convex_body_full_numeric_review.json`。录像仍需目视复核；单案例诊断通过不等于全任务或任意动作资格。

从正常v5资产重新构建干净v6的20场景，应用相同碰撞调整，未包含私有观察器。静态检查确认259个活动烧杯形状、257个隐藏凸杯身形状、正确的碰撞组成员关系；所有反应逻辑与v5逐字相同。与诊断mixed_3的全部属性／关系比较仅inputs:script不同（诊断读出移除）。9项规则测试、12项实际metric场景检查、接触观察器独立性测试以及20场景闭包／时长／120Hz7000／哈希通过。见 `evidence/v6_static_test_summary.json`、`evidence/v6_collision_contract.json`。

GPU1开始干净v6的mixed_3完整回放及复跑，GPU2开始干净v6无机器人银镜／保液／重置演示；协调器在首条完整回放通过后自动衔接其余8条文档坏例，复跑并行继续，异常阻止新入队。见 `evidence/v6_schedule.json`、`evidence/v6_coordinator.json`。未恢复旧v5队列，未发布READY，也未安装建通目录。

已向用户异步确认少量粒子漏失是否属于首轮阻塞范围；回答前继续原严格边界，不因问题已提出而放宽要求。本次新候选仍在追求不发生已测杯底越界。

## 干净v6演示完成，接收端从归档还原

干净v6的84秒／2520帧无机器人视频已完整解码，12个阶段画面已查看：初始透明、暗色沉积、银镜形成、移出保留及重置透明均可见。进度到1、重置到0，无运行错误；样液最低包含率1.0。浴水最低0.985345，但所有记录到的离开事件均在杯口上方且半径以内，最终没有粒子留在容器外，未记录杯底／侧壁离开。保留该瞬时杯口现象，不改写为每步100%包含，也不推广到任意动作。见 `evidence/controlled_v6_review.json`。

`receiver_v6` 已从建通基线克隆，导入已有metric提交 `f0dedfb29b2561e7f92bc4371fdcae43af555acd`，再实际解压v6临时归档。562个离线文件与1个metric文件均匹配冻结哈希，仍有NOT_READY标记。建通工作区未安装或切换分支。

20配置接收初始化协调器已启动：每张卡对应的候选回放队列完成后，在空闲卡上自动启动该组5个冷启动，保存四路视频和初始图；任何候选／初始化失败停止新入队。这样接收检查可与其他卡尚在运行的坏例并行。图像仍需逐项审核，协调器不会安装或发布。入口 `evidence/receiver_v6_coordinator.json`。

## 收尾门槛与规范同步

引擎异常仍是交付阻塞项。还需最终版本九条坏例复核、20 配置接收端初始化／80 张图、代表完整回放、离线三目录与 metric 提交、备份安装、READY 和飞书同步。不更新 LeRobot，不要求旧动作全部成功，不以修改动作、缩短时长或放宽评分制造通过。

适用 STATE-001/002/003/005、VAL-002/008 及材质／液体证据范围要求。规范无需变更：以上为 Task18、Isaac4.1 的特定候选与有限实验，不足以形成通用 CUDA、夹爪力或流体参数规则。核心包、适配器契约及既有交付包均未改变；诊断脚本继续留在仓库外。
