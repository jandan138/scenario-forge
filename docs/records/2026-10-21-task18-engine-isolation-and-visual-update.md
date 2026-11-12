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

## mixed_20引擎失败，暂停正式入队并隔离表面生成路径

干净v6首轮mixed_3已完成四路各16帧的目视检查，包含旧异常附近加密帧。机器人留在桌边，试管最终在加热器附近，未完成任务；所查帧未见明显整体弹飞。透明物重叠及局部遮挡仍在，不声明逐帧无穿透。见 `v6_first_mixed3_review/report.json`。

但随后 `silver_v6_g0_0_mixed_20_20261020T202419_511133Z` 出现CUDA700，client_exit=1，无有效任务结果。最先记录到的是 `sg_SparseGridClearDensity` 及等值面相关kernel的失败，之后级联到其他内核和FK读取。异步CUDA错误可能晚于原始故障上报，不能据首个日志名断定根因。该错误已阻止其余正式／接收端新入队；已运行任务按自己的收尾流程结束。见 `evidence/v6_mixed20_engine_failure.json`。

保留的客户端前缀有1581帧，已抽查起始及末段6帧：错误前机器人持管靠近水浴，未见整个机器人弹飞；失败的下一步没有画面，不能用前缀替代完整结果。见 `v6_mixed20_failure_review/`。

启动三组独立诊断：原样v6复跑、关闭两套液体等值面显示、增大等值面缓冲（maxSubgrids40000、maxVertices2000000、maxTriangles4000000）。后两组增加只读的浴水／样液位置范围和包含比例记录，物理参数、动作、时间与评分不变。关闭显示的版本绝不交付。入口 `evidence/v6_render_isolation_identity.json`、`evidence/v6_render_isolation_queue.json`；每卡内存峰值同时记录。

原样复跑也已越过原故障点，故不能凭单个对照暂时通过认定修复。关闭显示组到native2160时两套粒子均有限且全部在参考容器范围内，仍需完整运行及更进一步分析。没有因为诊断启动而恢复READY或放宽要求。

接收端完整代表回放队列（mixed17、mixed20）已准备于 `tools/run_receiver_v6_full.py`，但随候选失败停止等待，尚未执行；不把准备好的脚本算作验收完成。

## 三组均完成，发现离开试管后的无界下落

原样复跑、iso-off及容量增大三组均完成7000步、0.15分，无回执引擎错误。因此对照不能单独证明渲染关闭或容量增大解决了原CUDA故障，原失败仍保留。见 `evidence/v6_render_isolation_review.json`。

只读记录同时发现：浴水保持在烧杯中；样液后来离开试管，iso-off组记录到最低世界Z约−91.15m，容量组中途已低至约−43.37m，所有坐标仍有限。没有据此直接认定它们穿过桌面或认定CUDA原因；部分洒出粒子可能从桌边落下。静态检查发现Room/Asset/Floor没有碰撞，框架 `_setup_episode_layout` 还会移除命名defaultGroundPlane的碰撞。故新增独立地板碰撞对照。

试验仅在任务USD增加一个静态原生Cube，顶面与可见地板Z=0一致，XY覆盖相同6×7.5m范围，厚度向下延伸0.1m；所有物体和液体共用，未删除、钳制或回收粒子。原可见地板、物理场景、机器人、粒子、动作、时间、评分及等值面预算不变。GPU3完整回放进行中。到native3060时，离管样液的最低Z约0.000673m，说明新增地板已产生实际接触；不能以中途结果认定引擎问题已修复。

身份与队列：`evidence/v6_room_floor_trial_identity.json`、`evidence/v6_room_floor_trial_queue.json`。该测试不是重启已失败作业，也没有修改GenManip关闭默认地面的源码。

## 地板对照完整结束，启动干净v7验证

地板碰撞对照完整执行7000步、0.15分，未报引擎错误。动作逐项一致性、四路视频完整解码及Reset complete之后的粒子范围检查保存于 `evidence/room_floor_full_numeric_review.json`：浴水记录中全部留在杯内，离管样液被地板承接，记录坐标保持有限且不再持续下落。单次完成不构成CUDA内部根因证明。

干净v7以v6为基线，只给20场景增加与可见地板齐平的静态Cube碰撞；没有带入诊断读出、粒子钳制、等值面关闭或缓冲增大。静态逐属性／关系／API比较确认，已有prim数据全部不变，每场景仅新增PhysicsRoomFloor。20场景闭包、哈希、120Hz/7000及原时间配置通过，9项规则、12项实际metric场景检查及接触观察器独立性测试通过。见 `evidence/candidate_v7_identity.json`、`evidence/static_candidate_v7.json`、`evidence/v7_floor_contract.json`。

GPU0开始曾失败的mixed_20完整回放与复跑，GPU2并行无机器人银镜／重置验证；首条完整回放结束后自动衔接其余8条文档坏例。入口 `evidence/v7_schedule.json`、`evidence/v7_coordinator.json`。所有图像审核、接收端验收、备份安装和发布仍未完成；v7未发布READY。

## v7接收准备与地板试验画面复核

`receiver_v7` 已从基线导入同一metric提交，再解压v7离线归档；562个离线文件和1个metric文件的哈希一致，仍为NOT_READY。20配置接收冷启动协调器等待受控演示审核及各候选GPU队列完成；GPU0完成其5个初始化后，自动衔接mixed17/mixed20两个接收端完整代表回放。见 `evidence/receiver_v7_coordinator.json`、`evidence/receiver_v7_full_queue.json`。未安装建通目录。

地板诊断完整回放已查看四路各16个选定帧：试管在杯旁被夹持，随后倾斜／滑脱，最终落在加热器附近桌面；烧杯留在加热器上，所查帧未见明显刚体弹飞。地板承接样液主要由数值记录确认，桌面相机没有直接覆盖地板落点；透明玻璃遮挡和非逐帧检查的限制保留。见 `room_floor_review/report.json`。不把0.15分坏动作改写为成功示范。

## v7受控演示审核与接收保护预检

v7无机器人演示已完成并审核12个阶段画面，84秒／2520帧视频完整解码。银镜形成、移出保留和重置透明可见；进度1、重置0，无实际错误。样液最低包含率1.0，浴水最低0.990086，全部离开事件均在杯口上方且半径内，最终外部粒子列表为空。保留抽帧与规定轨迹的范围限制。证据 `evidence/controlled_v7_review.json` 已满足接收协调器的受控演示前置条件。

读取建通当前HEAD、分支、脏工作区及非Task18已跟踪文件哈希，保存 `evidence/receiver_preflight_v7.json`。这是只读预检，不是安装放行；安装前还需重新核对，并对其他任务未跟踪的正式运行树另做保护清单。未覆盖或切换建通工作区。

## 普通服务启动独立性检查已排队

另准备 `tools/run_plain_receiver_native.py`：服务与worker直接使用未修改的GenManip入口，移除测试用worker setup hook，服务PYTHONPATH仅含接收仓库与SDK，不含制作工具目录；外部客户端只负责发送原记录动作。已有核心代码本身已经设置单GPU渲染及设备映射，不需要为此改源码。

`evidence/receiver_v7_plain_full_queue.json` 正在等待接收端前置完整回放完成，再在GPU0执行mixed20普通服务启动的完整回放。它还没有运行，不能提前写成“无辅助脚本验证通过”。该检查不会安装额外文件或改SDK；失败仍阻断放行。

## 收尾门槛与规范同步

引擎异常仍是交付阻塞项。还需最终版本九条坏例复核、20 配置接收端初始化／80 张图、代表完整回放、离线三目录与 metric 提交、备份安装、READY 和飞书同步。不更新 LeRobot，不要求旧动作全部成功，不以修改动作、缩短时长或放宽评分制造通过。

适用 STATE-001/002/003/005、VAL-002/008 及材质／液体证据范围要求。规范无需变更：以上为 Task18、Isaac4.1 的特定候选与有限实验，不足以形成通用 CUDA、夹爪力或流体参数规则。核心包、适配器契约及既有交付包均未改变；诊断脚本继续留在仓库外。


### Clean v7 首条 mixed20 复核及既有任务保护

- 已复核 `v7_reviews/mixed20_first/report.json` 的四机位、各16帧：机器人留在桌边，试管最终落在加热器旁，未回架；得分0.15，不记录为成功示范。7000条手臂和底座指令与来源一致，完整运行无已记录引擎错误。抽帧证据不等于逐帧碰撞或保液认证。
- 远端 `10.150.164.127`、主机 `dsw-536365-78bdb944c8-q99ff` 的 GPU0–3 均在执行 clean v7 回归，接收端队列等待对应回归完成。尚未安装 Task18 或发布 READY。
- `evidence/protected_other_runtime_v7.json` 已保存称量、滴定、水浴三个规范运行树的1578个文件快照，供安装前后核对；不包含 mesh_data、__pycache__ 缓存。
- `provisional_v7/README_DRAFT.md` 是待验收草稿，不能作为交付完成凭证。规范无需变更：本次仅补充 VAL-002/VAL-008 范围内任务证据，不新增通用物理参数规则。

- 后续补充：`evidence/v7_archive_boundary_review.json` 实读 ZIP 全部562个成员，逐项匹配冻结清单和哈希，无重复路径、越界路径或运行缓存；metric单独交付。该检查仅证明封包字节完整性，不代表运行验收通过。`provisional_v7/INSTALL_ROLLBACK_DRAFT.md` 已明确备份原metric工作树、bundle HEAD引用、按归档清单暂存、逐目录回退及其他任务保护流程，尚未执行安装。

- 增加运行结束后的完整日志复扫：`tools/audit_v7_terminal_logs.py` 在远端读取最终 server/client/worker 日志并保存字节哈希及错误候选，补充运行中轮询可能漏掉末尾错误的边界。首条 clean v7 mixed20 三类终态日志均无匹配错误，结果见 `evidence/v7_terminal_log_audit.json`；活跃回放不提前标记通过。脚本仅制作侧审计，不进入交付运行依赖。

### Clean v7 mixed3 完整结果

`silver_v7_g1_0_mixed_3_20261020T221500_363864Z` 完整7000步、0.15分，终态server/client/worker日志无匹配错误；四路视频完整解码由队列完成。另核对7000条手臂/底座指令与原记录完全一致，四机位各16帧目视复核：试管到2500帧仍在夹爪附近，到2950帧已落在加热器旁，终帧未回架；烧杯留在加热器上，抽帧未见整体弹飞。机器人关节最大单步差约0.0820rad，底座约0.000218m；这些不是逐帧物体碰撞认证。证据 `v7_reviews/mixed3/report.json`。队列自动接续mixed17，未修改场景、动作或评分。

### Clean v7 mixed20 重复结果与接收端自动续接

第二次 `silver_v7_g0_1_mixed_20_20261020T221455_534578Z` 完整7000步、0.15分，终态三类日志复扫无匹配错误，原动作一致；四机位各16帧复核已保存 `v7_reviews/mixed20_repeat/report.json`。试管落在加热器后侧/右侧桌面，区别于首次落点；两次同分不代表物体轨迹逐帧一致。抽帧未见整体弹飞，仍不能宣称每帧无穿透。GPU0完成后接收端初始化队列自动启动，PID118837；尚未安装到建通规范目录。

- Clean v7 `silver_v7_g2_0_mixed_1_20261020T221640_860293Z` 完整7000步、0.15分；动作逐帧一致、终态日志无匹配错误。四机位各16帧复核显示试管最终横落在管架/加热器附近，烧杯仍在加热器上，未成功回架；不作逐帧无穿透结论。证据 `v7_reviews/mixed1/report.json`。GPU2已续跑mixed18。
- 接收端mixed1、mixed5初始化和视频检查完成，四张初始图各已目视核对并保存 `receiver_v7_review/<case>/visual_review.json`（共8/80张）；记录透明物体可见性及视角裁切限制，不将初始化通过作为任务成功。

- 文档弹飞案例mixed4已完成 clean v7 7000步、0.15分，终态日志无匹配错误、原动作一致、四路视频解码完成。四机位各16帧未见整场/机器人弹飞；烧杯略移动但仍在加热器区域，试管在撤手后的左腕视角下边缘部分可见，不能据裁切画面断言最终支撑或逐帧无穿透。`v7_reviews/mixed4/report.json` 保存范围与限制。GPU3已续跑mixed15。接收端mixed9四图完成目视，累计12/80张。

- GPU0接收端五配置mixed1/5/9/13/17已完成初始化、视频完整解码和20张首帧目视检查，记录 `receiver_v7_review/<case>/visual_review.json`；近景上端裁切已明确。尚余15配置/60图。队列自动接续receiver_v7的mixed17完整回放（`receiver_v7_full_queue.json`），未安装到建通目录。

### v7 接收端mixed17引擎失败：正式交付继续禁止

`silver_receiver_v7_full_mixed_17_20261020T225112_362893Z` 早期触发 `sg_SparseGridClearDensity` CUDA700，继发isosurface及curobo访问错误；没有最终分数。首错不能仅凭异步日志认定为根因。失败原始日志已拷入 `evidence/receiver_mixed17_failure_logs/`，GPU0进程清理完成。此前mixed20两次、mixed3/1/4正常不能抵消本失败，接收队列已停止，未安装/发布。

保留候选端仍在运行的同动作mixed17对照；重新核对接收563文件哈希一致后，在GPU0启动单独诊断 `silver_v7_diagnostic_plain_mixed17`（监督PID169668），普通未修改服务、无worker setup hook、同场景/动作/评分。该运行用于区分启动包装影响，不直接恢复正式队列。`CURRENT_STATUS.json` 和验收清单已更新失败状态。

- 上述普通启动诊断首次在Ray启动前因AF_UNIX路径超过107字节失败，未执行仿真。仅将外部测试启动器RAY_TMPDIR缩短为`/tmp/t18plain_g0`，保留原运行，以新label `silver_v7_diagnostic_plain_mixed17_shortpath`重试（PID170339）；这不是USD/核心/SDK修复，不能把该启动故障计入物理失败。

- 短路径普通启动对照在仿真初始化前被唯一GLInterop窗口初始化错误拦截（`carb::windowing is not available`），未复现或排除PhysXCUDA700。单独创建制作侧诊断启动器，仅允许这一条明确的无窗口消息并写入回执，其他错误仍停止；不改正式验收启动器过滤规则。新诊断 `silver_v7_diag_plain_headless_mixed17` PID175392，普通服务/worker无setup hook，任务/Core/SDK不变。此运行不直接算正式资格。

- 候选mixed17 `silver_v7_g1_1_mixed_17_20261020T223844_152386Z` 正常完成7000步/0.15分；完整原6922条指令后保持末帧至7000（原底座指令全零），不能将补尾称为原策略新增动作。四机位16帧概览显示倾斜持管、6000/6500附近靠近管架、终帧横落架旁；历史回架穿模问题仍需密集接触帧复核。普通无hook诊断已进入步进并超过先前390条已确认动作附近，尚未结束；这既不排除间歇性CUDA错误，也不证明hook为根因。

### mixed17回架细看与只读诊断

已检查6400..7000每40帧的左腕与俯视图：松爪后试管从架后倾倒，最终水平且局部被架遮挡，未明确看到穿过实心板，但不能证明遮挡处无穿透。范围见 `v7_reviews/mixed17_rack_detail/scope.json`。原生meta/RRD不含逐帧物体位姿，不能凭机器人状态替代物体接触证明（`evidence/native_recording_scope_audit.json`）。

准备`mixed17_v7_telemetry`独立诊断副本，只追加post-update只读观察器，记录两组液体范围/有限性/保留率及试管、烧杯、管架完整矩阵；静态逐属性/关系/API对比仅FlowController脚本不同。普通采样60步、6300..7300区间10步。观察器可能扰动调度，不作干净运行资格。`v7_m17_telemetry_queue.json`监督PID189005等待GPU2当前mixed18完成后自动运行；正式接收失败门禁不解除。

- mixed18完整7000步/0.15分，四机位各16帧已复核：试管早期靠近水浴，后段在架后边缘之外可见而非插孔内，烧杯仍在加热器上，所查帧未见整体弹飞；终态支撑受视角缩短/遮挡限制。证据`v7_reviews/mixed18/report.json`。GPU2只读mixed17诊断已实际输出两组粒子边界及三个物体矩阵，尚未到关键阶段，不提前解释启动采样。

- 只读mixed17诊断早期采样出现不同接触结果：native720/780/840烧杯倾角约30.8/41.1/125.6°，900约140.4°后浴水保留率显著下降，粒子坐标仍有限。顺序支持翻杯洒水解释，不能把低保留率直接写成杯底穿漏；完整视频和时序核对尚待完成。部分数据保存`evidence/v7_m17_telemetry_partial.json`。观测副本不替代无观测候选或接收失败的证据。

- mixed15完整7000步/0.15分的四机位16帧已复核：机器人/管架/烧杯未出现所查画面中的整体弹飞，烧杯初期在加热器上移动，后期试管反复位于架孔及夹爪附近并倾斜，不能据离散帧认证稳定插入或全部接触正确。证据`v7_reviews/mixed15/report.json`。候选九条坏例已有七条完整结果（mixed20另有重复），剩mixed10/11；接收CUDA失败仍独立阻塞交付。

### 后续单参数容量试验（未采用）

在等待当前诊断收尾期间准备 `mixed17_v7_subgrids40000`：仅BathSystem/SampleSystem的`physxParticleIsosurface:maxSubgrids`从10000改40000，逐属性/关系/API检查确认其余不变，不附观察器，不改粒子物理/材质场/反应/评分/动作。v6旧容量实验因原配置也通过而因果不明，此次针对真实接收失败的mixed17，仅作为仍待验证的假设。`evidence/v7_m17_subgrids_identity.json`保存字节身份，监督PID205324等待GPU1 mixed10结束后自动运行。不会据单次通过认定根因或解除接收失败门禁。

- 普通无hook mixed17诊断 `silver_v7_diag_plain_headless_mixed17_20261020T225940_425605Z` 完整7000步/0.15分、client0，四视频完整解码及动作一致性核对完成。终态日志仅一条事先明确的headlessGLInterop启动消息，未有其他匹配错误。四机位16帧可见烧杯早期翻离加热器、周围液体水洼，机器人留在桌边，试管后期回到架边；与候选物体轨迹不同，不证明hook导致此前CUDA。证据 `v7_plain_headless_mixed17_log_review.json`、`v7_reviews/plain_headless_mixed17/report.json`。正式接收失败仍未解决。

- mixed10 `silver_v7_g1_2_mixed_10_20261020T230313_533718Z` 完整7000步/0.15分，动作一致性及四机位16帧复核完成：试管最终横落架前桌面，烧杯留在加热器上，所查帧未见整体弹飞，非任务成功或逐帧无穿透证明。`v7_reviews/mixed10/report.json`。候选九条已完成八条（尚余mixed11）；GPU1已自动接续40000稀疏网格容量试验，未采用为交付版本。

### 40000容量试验失败，继续拆分后处理

`silver_v7_m17_subgrids40000_20261020T232721_692247Z` 客户端已确认390步后触发同类`sg_SparseGridClearDensity`CUDA700，client1、无有效结果。receipt.error为空不能当通过，完整日志已另存；`evidence/v7_subgrids_rejection.json`明确否决此单参数修复，不继续盲增容量。先前接收失败同样在390条已确认动作之后发生，不能把确认步数当精确首错物理步。

准备两个独立单开关诊断：`mixed17_v7_anisooff`仅关闭两系统粒子各向异性后处理，保留液体表面；`mixed17_v7_isooff`仅关闭两系统表面生成，用于定位且永不交付。均保留粒子物理/动作/反应/metric；外观可能变化。GPU1 anisooff PID213041；GPU0 isooff监督PID217819等待前者首次reset后自动启动。未更改正式candidate_v7或receiver_v7。

- 只读位姿/粒子诊断完整7000步/0.15分结束，共207个采样，native0..7380，粒子坐标采样均有限；浴水翻杯后保留率降至0，样液最低约0.000673m，浴水最低约0.759961m。烧杯最大倾角140.37°。这些是离散采样且物体轨迹与干净候选不同，不能据此认证全部帧无漏液或解释被遮挡的另一运行。完整数值/原始行见`v7_m17_telemetry_complete.json`、`v7_m17_telemetry_rows.json`；四视频已解码，抽帧准备完成，目视待做。Anisooff已超过630条确认动作，isooff已启动；都尚未终态。

- 只读诊断四机位各16帧目视完成：烧杯早期翻倒、液体水洼可见，试管留在翻杯区域桌面，后期机器人空夹爪去架子。画面与翻杯数值方向一致，但此运行没有实际后段持管插架，不能解决另一干净回放的遮挡接触判读。`v7_reviews/mixed17_telemetry/report.json`及complete报告已明确范围。

### 发现本机schema范围违规：浴水表面距离与网格间距

重新核对远端Isaac4.1本机 `omni.usd.schema.physx/plugins/PhysxSchema/resources/schema.usda`，surfaceDistance须满足 `[0,2.5*gridSpacing)`；原文及文件哈希存`native_isosurface_distance_schema.json`。v7全部20场景浴水distance0.008m、spacing0.00291m，上限0.007275m，超出文档范围；样液均在范围内（`v7_isosurface_range_audit.json`）。这是已确认authoring问题，尚未证明是CUDA根因。

独立试验`mixed17_v7_gridspacing33`仅改BathSystem网格间距为0.0033m，保留表面距离8mm、PBD动力学、粒子数、透明度、反应和评分/动作，静态对比唯一该属性变化且两组均满足范围。网格分辨率变化需目视验证；未推广到20场景或正式包。GPU2诊断PID225911已启动。该数值是本任务候选，不提升为通用默认；规范无需变更，验证后再更新交付资格。

- mixed11完整7000步/0.5分，四机位16帧复核完成：长时间持管在浴区，后期向架子移动，终态试管位置未能从所查帧确定；不据暗背景/透明遮挡宣布接触合格。分数包括50%反应门槛，无完整成功。至此v7九例+mixed20复跑共10条完整结果，汇总`v7_candidate_regression_complete.json`，不是交付PASS；接收CUDA700及已确认参数范围违规仍阻塞。
- GPU3空闲后启动3.3mm网格候选的84秒无机器人银镜/重置对照，监督PID231245，输出`controlled_gridspacing33`，保留原反应时长/受控轨迹；仍待运行和目视结果。

- `silver_v7_m17_gridspacing33`也在390条已确认动作后CUDA700，client1无有效结果。合法范围修正是必要authoring纠正，不能称为充分稳定性修复；日志另存`v7_gridspacing33_failure_logs`，结论`v7_gridspacing33_failure.json`。不撤销/覆盖原失败。
- 新独立组合`mixed17_v7_validgrid_anisooff`仅Bath网格3.3mm+两系统anisotropy关闭，isosurface保持开启；静态diff为这三属性，PBD动力学/轨迹/反应/metric不变。GPU2 PID232905启动，未作为正式候选或交付。GPU0/1的两个单开关对照继续，GPU3范围修正受控演示继续。

- 准备20场景实验`candidate_v8`（尚未采用/运行合格）：仅浴水网格3.3mm+两系统anisotropy关闭，表面开启，逐场属性/关系/API对比确认仅3属性不同，563文件哈希冻结，v7源哈希未变。构建完成后9项规则、12项实际metric方法测试通过；不等于GPU或动态插架合格。组合受控演示监督PID239501已排在GPU3前一演示后，仍待结果。

- 仅grid3.3mm受控演示84秒/2520帧完整解码，12阶段已目视：透明初态、沉积、银镜、提离保留及清晰重置可见。progress峰值1/末0，样液保留1，浴水最低约0.997845，仅杯口上方波动且末帧全部返回。`controlled_gridspacing33_review.json`为规定无机器人范围通过，不抵消其机器人CUDA失败。组合受控演示已自动开始，尚未完成。

- 实验v8的20场景/20配置资源闭包、原生PhysX标签、粒子数、120Hz/7000与原反应时间、冻结文件哈希复核通过，并新增每场两系统surfaceDistance范围和isosurface开启/anisotropy关闭断言；`static_candidate_v8.json`仅静态资格。
- anisooff与isooff两对照均完整7000步/0.15分、client0，末尾server/client/worker日志无匹配错误，`v7_postprocess_terminal_comparison.json`保存终态。原配置也曾通过，故不证明单一根因；isooff永不交付，anisooff单项仍有原浴水参数范围问题，需看组合试验及重复验证。

### 组合受控渲染灰屏，停止无效运行并保留证据

`controlled_validgrid_anisooff`在实际输出0/30/57帧目视均为灰屏、无场景可见；约10分钟仅84帧。确认仍存活且同一自有进程组后，SIGTERM仅停止PGID239501的受控演示，未动GPU2机器人回放。`controlled_validgrid_anisooff_blank_rejection.json`保存原因和帧数，原report的RUNNING保留为中断证据，不伪记完成。此异常尚未归因相机/初始化或表面生成；实验candidate_v8改为受控渲染失败待诊断，不进入正式验收。

- 灰屏短诊断`render_inspection_combo`完成，3次render画面仍灰；相机矩阵有效，浴水/样液生成网格3686/2394顶点且坐标有限、空间范围约厘米至分米，当前数据不支持“网格坐标爆炸”解释。继续同进程显示隔离`render_visibility_isolation` PID246005，依次显示全部/隐藏全部液体/仅隐藏原始粒子/仅隐藏生成面；仅内存visibility诊断，不保存USD，不改动力学。正式v8仍未获资格。

- `render_visibility_isolation`在同进程内显示全部/隐藏全部液体/仅隐藏粒子/仅隐藏生成面均保持灰屏；已亲看全部液体隐藏帧，当前不支持“液面遮挡相机”解释（仍有渲染刷新限制）。不进一步据此改PBD。GPU3启动此前可见的gridspacing33基线同一短探针并记录RenderProduct相机绑定，PID247636，用于区分演示渲染初始化与新参数问题。

- 灰屏基线对照`render_inspection_gridbaseline`同一短探针正常出图，RenderProduct绑定`/World/ProbeCamera`。进一步`render_xforms_combo`与`render_xforms_baseline`均完成，2034个USD world矩阵逐项比较无>1e-6差异、相机绑定一致；`render_xform_comparison.json`。这排除了已观测USD变换差异，仍不能证明GPU侧渲染状态正确；不再把灰屏归因通用初始化慢。新组合保持待诊断。

- 组合机器人回放已最终7000步/0.15分、client0，四MP4完整解码、动作一致性检查完成，原生俯视首帧目视正常；完整抽帧准备完成待目视。不能据此解除无机器人演示灰屏。渲染相机参数随1e-5m位移更新且与USD一致，恢复原矩阵仍灰，`render_camera_refresh_combo`。
- `render_occlusion_combo`深度全部有限、约0.04335..0.04819m，实例ID均0未映射；静态USD几何在估计命中点附近的包围盒候选为空（只作broadphase，不作GPU射线证明）。进一步同进程临时给所有Gprim加语义标签并读分割，PID255086；不保存资产或改变物理。

- `render_semantic_occlusion_combo`加全Gprim标签并启用semantic annotator后RGB正常，深度约0.544..5.363m，可见多物体标签；不是定位到真实4.5cm遮挡。标签与annotator为同时改变，尚无单因素因果。仅root visibility隐藏/恢复（0新增物理步）仍灰屏，`render_scene_refresh_combo`。继续仅semantic annotator、不作者任何标签的隔离试验PID266322。
- GPU0启动完整实验candidate_v8的mixed17连续两次重点回归，监督PID257380；新增终态完整日志扫描，原动作不改，有引擎错误停止剩余队列。该试验与灰屏诊断并行，不代表解除渲染/交付门禁。

- 灰屏单因素隔离：无标签仅semantic annotator仍灰；只加Gprim标签、仍仅RGB输出则正常可见（`render_labels_only_combo/render_2.png`已目视）。相机/visibility刷新均未奏效，内部渲染根因不冒称确定。源USD哈希核对未变，汇总`render_initialization_isolation_summary.json`。只在制作侧受控工具中加入已验证的内存语义初始化，不保存资产、不改粒子/刚体/评分；完整84秒新演示`controlled_validgrid_anisooff_tagged`PID268928已启动，仍需动态银镜/重置验证。

- 新带内存语义初始化的组合演示第300帧已目视正常，浸入及早期沉积可见；仍待完整银镜/重置。受控源unseen7场景字节哈希与candidate_v8对应场景相同。
- v8重点mixed17两次已在GPU0运行；剩余GPU1 mixed20两次、GPU2 mixed3/1/18、GPU3 mixed4/15/10/11队列及协调器已准备，监督PID270804。首条mixed17完成且完整受控review=CONTROLLED_SCOPE_PASS才放行其他三路；不触碰旧失败门禁。`v8_qualification_checklist.json`保留接收20/80、完整接收回放、安装等未完成项。

- 完整candidate_v8首条mixed177000步/0.15分终态日志检查通过，四机位各16帧已复核：翻杯、水洼、机器人留桌边、后期持管回架方向；末态试管被架局部遮挡，不认证全部接触/稳定插入。第二条已自动接续。
- `provisional_v8`离线ZIP562文件+原metric f0dedfb提交实际解压到独立`receiver_v8`，563哈希一致、修复桥接模块沿用基线，没有复制producer工具；建通原目录未改。接收coordinator/full/plain监督PID277204/277205/277206已排队且受候选/受控门禁约束。普通服务验证仅明确allowlist此前已实测的headlessGLInterop缺窗口消息并保留在回执，其他错误不豁免，不使用worker hook或改核心。

### v8受控银镜与重置完成，进入后续回归

`controlled_validgrid_anisooff_tagged`84秒2520帧完整解码，12阶段已目视正常；progress峰值1、末0，native dt约1/120、10082步（含预热），render-only刷新0物理步。样液保留1；浴水最低约0.986207，6393次记录的边界转换均为开口径向内、杯口上方，末帧外部ID为空；不推广为任意动作无洒水。源场景哈希与v8 unseen7逐字节一致，内存语义标签不写回资产。日志只有SimulationApp导入弃用告警中的Traceback字样，无实际引擎错误。`controlled_validgrid_anisooff_tagged_review.json`写入CONTROLLED_SCOPE_PASS，释放剩余回归前置门禁；不代表正式整包验收。

- v8四GPU回归现均已实际启动：GPU0第二条mixed17，GPU1 mixed20，GPU2 mixed3，GPU3 mixed4；协调器REGRESSION_RUNNING。
- 制作侧`install_receiver_v8_guarded.py`已准备，默认仅只读预检；实际执行必须匹配最终验收证据哈希、发布清单、原接收Git状态、严格三目录离线成员与metric提交范围，逐目录备份和事务回执，安装后仍不写READY。只读预检确认B仍9490df9a/Task12分支，现有称量/水浴改动保留，gate/最终manifest缺失且未写接收端。其余任务保护包含规范task_09_solid_weighing、task10、task12的未跟踪运行文件，缓存除外。脚本实际安装路径尚未运行；不能把预检称为安装测试通过。

- 补充[Task18交付操作说明](../operations/task18-silver-mirror-delivery.md)及科学实验交接入口路由，记录运行/成功/视觉证据区别、终态日志复扫、无机器人灰屏初始化的限定经验、只安装四类运行内容及保护回退流程。规范无需新增通用规则：参数和渲染处理均为本任务/本机验证范围，引用既有VAL-002/VAL-008；历史包及历史失败不改写。

- v8第二条mixed17完整7000步/0.15分，四机位16帧已复核；烧杯位移/倾斜后回到加热器区域，试管最终横在架旁，所查帧无整场弹飞，部分接触遮挡限制保留。与首次物体运动不同，不声称完全复现。动作一致性及终态日志扫描通过，GPU0已自动开始接收端5配置初始化（监督PID300040）。

- 接收v8 mixed1/mixed5四机位初始图已逐场目视，累计8/80图，证据`receiver_v8_review/<case>/visual_review.json`；不沿用v7的20图。CURRENT_STATUS已整理为v8专用当前入口，旧多版本索引保存`current_status_before_v8_index_cleanup.json`，避免旧计数混入当前资格；实时状态仍须看队列和实际进程。

- 接收v8 mixed9/mixed13首帧四机位目视完成，累计16/80图，裁切限制保留。v8 mixed20首条四机位16帧及2600..2960每30帧俯视局部已复核：试管由杯沿滑下经桌面前缘进入机器人附近遮挡，不见所查阶段在桌面中间突然消失；末态接触不认证。完整原图与裁切坐标均保留，`v8_reviews/mixed20_first_drop`。mixed3回放抽帧已准备，目视尚待。
