# 水浴：完整原生回放失败与抓持短诊断

干净接收方候选的h13_b完成7000步，score=0.85、sr=0；原动作核对及四视频完整解码通过。原生日志时间保留在各报告中，本记录是后续整理日期。此次结果不是超时，也不是交付通过。

主实现者查看原尺寸关键帧和3540–3760步每20步的回架画面：下降时试管相对夹爪逐渐倾斜，3680–3700附近松爪时未直立落座，3720横跨架面，随后滑落，7000时横躺桌面。因此不是正确落座被metric误判。橙色样液在持管和翻倒时可见；该干净回放没有逐物理步粒子位置记录，不能据图声称机器人操作中保液达到95%。见 `evidence/receiver_retention95_h13_b_visual_review.json`。

下一步以原前300帧动作作抓持短诊断，不改写动作值/顺序。独立诊断工作树仅新增一个只读USD ScriptNode，并将该诊断配置num_steps设为300；正式候选7000步保持。metric、核心和既有物理属性保持。该短测不作为完整成功或文档坏例结果，不计入38次合格回放。

观察节点订阅native post-step和已有接触报告，记录实时试管/烧杯/夹指位姿、试管相对管架/夹爪位置、逐步粒子计数、运行时碰撞属性和具体接触体。只做引擎读回，不写力、位姿、关节目标或粒子位置。另记录浴水粒子深处于试管腔内的数量及管口/水面高度差，作为需要结合历史判断的交叉容器疑点，不新增评分规则。

首个观察器尝试被首错保护拒绝：在机器人尚未加载的初始步骤查询link6，产生Failed to register rigid body。后续初始化虽记录到25个DOF，不能忽略早期错误而宣布通过。v2增加prim存在检查，并先确认articulation再读夹指；使用新目录、新编号重跑，旧日志/报告不覆盖。身份 `evidence/native_observer_prefix_v2_identity.json`；源正式候选不改。v2现已完成300步；以下追加其结果。

19组验收矩阵按既有19条来源哈希保留，实际只有14个不同case名，不能按case名去重。0/13/15三个代表的旧版校准证据来自两个原有验收记录，引用已补齐；其余16条仍待协议与旧基线确认。当前版本完整合格次数为0，0.85诊断不计入。矩阵 `evidence/retention95_qualification_matrix.json`。

适用STATE-002、VAL-002/008。规范无需变更：这是既有只读测量和证据范围规则的任务实现。所有辅助脚本/日志仅在个人repair目录，不进入交付运行依赖；新增observer不在生产metric中。完整新版本仍需19组各两次及独立安装验证。

## 前300步对照结果与下一组实验

v2观察器与原生记录的301个观察状态精确对齐。试管相对夹爪的偏差在第200–300步已达9.88–11.00mm，而手腕路径与旧成功轨迹基本一致；管架运行时仍为静态碰撞体。该窗口没有观察到保液代理与机器人发生刚体接触，不能据此推断全程不存在。样液最低96.82%，仅覆盖前300步。

恢复旧版试管完整GlassShell、SDF烹制参数、contact/rest偏移和单体CCD默认值的组合短测已经完成。初始相对位置偏差从1.06mm降到0.0376mm，但第300步仍偏8.477mm；样液最低96.1812%。短测score0.15是提前结束的过程分，不是完整回架失败或成功。证据分别为 `evidence/native_observer_prefix_v2_h13_a_analysis_pose.json` 和 `evidence/old_tube_contact_prefix_h13_a_analysis_pose.json`。

静态复核旧版试管仅有一个启用的固体碰撞体GlassShell，没有漏掉其他旧固体碰撞体。诊断组合包含同一GlassShell及473个保液代理；后者用途需结合碰撞过滤和运行接触判断，数量不能直接当作机器人接触面数量。清单 `evidence/old_bundle_collider_inventory.json`。场景文件不自带PhysicsScene，运行配置来自YAML，不应对空场景列表强行取首项；首次报告尾部比较因此报IndexError，碰撞清单已保存，未作运行通过依据。

下一组 `old_bundle_solver_prefix` 从上述旧碰撞组合出发，只将evaluation全局位置求解迭代上下限64/128恢复为旧默认1/255；全局CCD保持开启。液体、质量、摩擦、动作、metric保持，不把多项参数一起调到分数通过。使用新诊断目录、独立trace、300步限定回放，正式7000步候选不动。目的为检验旧碰撞配置与迭代范围的组合是否恢复抓持；未经结果检查不采用到交付。

规范无需变更：以上是任务级受控诊断，没有证据支持通用碰撞或求解器默认值。操作说明同步到本记录，未改变核心包/API或历史交付资格。

附加静态排查：旧碰撞组合与旧版的试管质量、重心、主惯量及主轴相同且显式作者，排除“仅因新增代理而自动按体积重算惯量”的静态假设；这不排除运行时液体载荷影响。证据 `evidence/old_bundle_body_differences.json`，试管质量0.018008921kg，惯量约(3.49188e-5,3.49188e-5,1.28462e-6)kg·m²。该结论是USD作者属性对照，非运行时受力测量。

old_bundle_solver_prefix静态审计通过：只改变evaluation迭代上下限及诊断observer输出路径，关系、物理属性、其余YAML保持；报告 `evidence/old_bundle_solver_prefix_static_audit.json`。远端supervisor2272776和worker2274408已实查存活。独立有界分析等待器只在回放终态完成后读取结果并生成对照，不启动后继物理测试，不会因观察超时重启任务。

位置迭代对照已完成：301观察状态精确对齐，原动作不变、视频完整解码通过。第300步抓持偏差从8.477mm降至3.587mm，前300步样液最低96.0805%；短测score0.15，不能替代完整回架资格。证据 `evidence/old_bundle_solver_prefix_h13_a_analysis_pose.json`。下一组从该版本只改变evaluation EnableCCD=True→False，检验旧版剩余全局CCD差异；粒子系统自身CCD配置不改，仍需实测保液，不假定无相互影响。

CCD隔离候选静态差异审核通过并已启动（supervisor2279871）；报告 `evidence/old_bundle_ccd_prefix_static_audit.json`。三组短测比较及来源哈希见 `evidence/grasp_prefix_comparison_20261016.json`。这些均为单次前缀诊断，不推断重复稳定性。远端Isaac PhysxSchema的generatedSchema.usda已只读核对位置迭代默认下限1、上限255。

保液按原生记录对齐后的动作窗口复核：solver组合起始98.9069%，第300步96.0805%，外部粒子从152增至545；窗口内532次退出事件均由v3分类为mouth_compatible。初始化阶段不与动作阶段混计；重复进出会产生多次事件，因此事件数不等于最终损失粒子数。当前下降不是全部来自初始化，仍需完整逐步保液及喷射/持续失液视频审查。`evidence/prefix_retention_phase_comparison.json` 保存三组阶段对比；该分类不能代替视觉验收或全程无穿壁证明。

小型诊断结果及哈希归档于[抓持前缀证据](2026-10-16-task12-grasp-prefix-evidence.json)。初始USD样液局部z范围1.90–43.50mm，管口150mm；这是静态初态检查，不说明运行液面高度。不得未经运行证据把损失直接归因于装满。

CCD对照完成，301观察对齐误差0，第300步抓持偏差5.216mm（CCD开启组合3.587mm），短测最低保液96.1597%。不采用CCD关闭，保留单次结果的有限范围。接下来对旧试管碰撞+迭代1/255+全局CCD开启的组合跑完整7000步上限，不再改物理、动作或评分；诊断USD保留逐步观察器以同时审查保液与回架。此前短测不能证明完整操作成功。此完整运行沿用已解释的90分钟有界墙钟预算（不是物理时长/步数修改），不重复触发已证明过短的45分钟中止。

主实现者（非独立审查）抽看solver前缀左腕与overlook的0/50/100/150/200/250/300帧，共14帧：可见夹取和移向烧杯，未见明显宏观喷流；左腕运输阶段裁切管底，俯视样液较小且被夹指遮挡，蓝管架反射干扰判断。因此判WARN，不能证明连续无喷射或完整液柱可见。记录 `evidence/solver_prefix_visual_review.json`，原图保留于外部evidence目录。

在完整回放等待期间，从19条已定位的原始worker日志严格截取对应SceneConfig到done的片段：index3–7共5条OpenWAM终止行属于single-step路径，其余14条属于chunk路径。保存行号与片段哈希于[原终止接口证据](2026-10-16-task12-terminal-dispatch-evidence.json)。终止接口不证明整段请求边界或底座标志；其余16条旧包校准仍待执行，不能统一套用Pi05 chunk30。此次只读日志分析不占仿真GPU，不改正在运行的版本。

完整solver组合仍在执行时，实时观察在有效加热0.875s后首次低于95%（observer794，94.9874%），到observer828为94.6854%，连续34个加热观察低于线。保存 `evidence/old_bundle_solver_full_h13_a_live_observation.json`；最终meta对齐未完成，不沿用前缀warmup长度虚构动作帧号。保持本次完整回放不中途调参，以同时取得变色/回架结果；当前实时证据已不支持交付合格。

进一步静态核对独立夹具与当前完整诊断的Sample/Bath系统、粒子属性和物理材质（排除位置/速度/extent数组），未发现数值差异，报告 `evidence/fixture_vs_native_fluid_attributes.json`；不含运行时覆盖、几何/碰撞关系和全局solver，因此不称环境等价。实时observer800–899中试管平移速度中位0.0156m/s，保液94.9371%降至93.9374%；900–974中位0.0198m/s，继续降至93.0241%。这些窗口尚未最终meta对齐，但足以提示不能只解释为高速搬运瞬间损失。保留 `evidence/solver_full_live_loss_vs_motion.json`；动态耦合/场景接触尚待隔离，未更改本次运行。

追加排查（仍不改正在运行的场景）：用旧记录前101个机器人观察匹配新trace，最大误差1.788e-7，定位observer414为动作frame0；这是共同前缀初步定位，最终仍须全量新meta对齐。500–899窗口的新旧试管平移速度/有限差分加速度量级相近，未支持新版显著额外抖动假设，见 `evidence/solver_full_live_old_new_motion.json`。使用原机器人mesh凸包和live link位姿抽样管腔，150/300/600/900帧未见样本点处于夹指凸包内；夹指最低局部z约114–117mm，初始液柱顶43.5mm。报告 `evidence/solver_full_finger_cavity_sample.json`；不含烹制偏移和连续几何证明，因此不据此关闭机器人液体碰撞。

黏度调研：现有task10材质作者viscosity=0；远端Isaac4.1 particleUtils水预设使用1.7e-6/(metersPerUnit³)。[官方Schema说明](https://docs.omniverse.nvidia.com/kit/docs/omni_usd_schema_physics/latest/physxschema/class_physx_schema_physx_p_b_d_material_a_p_i.html)列为非负无量纲参数，[PhysX5.3接口](https://nvidia-omniverse.github.io/PhysX/physx/5.3.0/_api_build/class_px_p_b_d_material.html)说明其用途，但均不能证明本任务增加黏度可修复。未将任意黏度改值混入当前对照，未新增通用推荐。

只读observer v4已准备，新增每120步样液点/速度压缩快照与分位数，第500步通过tensor getters读实际fluid/solid rest及particle contact offsets。已编译并在远端SDK源码确认接口存在，尚未嵌入场景或执行；不得把准备状态标为运行通过。身份 `evidence/observer_v4_preparation.json`。当前完整回放仍用冻结v3，未更改。

原生失液observer v4已封入独立1200步诊断工作树，静态审计确认相对solver前缀仅num_steps300→1200及observer脚本变化，物理参数、关系、原动作和metric不变。运行队列 `evidence/loss_observer_after_full_queue.json` 只在当前owned完整回放正常完成审计且进程退出后启动；自身预检仍要求GPU/端口空闲。前置报错、句柄提前丢失或等待超时均停止队列，不自动重启当前任务。身份和审计分别 `native_loss_observer_v4_identity.json`、`native_loss_observer_v4_static_audit.json`。此时仅准备完成，尚未获得v4运行证据。

过滤接口查证：远端Isaac4.1 `/isaac-sim/extsPhysics/omni.physx.tests/omni/physxtests/tests/PhysxParticleAPI.py` 的 `test_particleSystem_pair_filter`（约877–910行）在粒子系统应用FilteredPairsAPI并指定地面碰撞prim，断言粒子随后穿过被过滤地面。它证明当前系统端写法有同SDK测试用例依据；本次未执行该测试，也未由静态平面推广为动态试管SDF过滤成功。当前单粒子/动态容器过滤效果仍未独立实测，不能因schema存在宣称没有双重液体碰撞。

首次执行前补充观察器v5：为避免遗漏World默认初始化的重力/单位差异，先核实旧等待队列确实尚未启动下一轮，再仅停止等待器2297008。完整回放2287108/worker未动。准备工作树仅更新observer脚本，新增第500步场景重力/单位及PBD材质属性读取；旧身份另存 `native_loss_observer_v4_identity_before_runtime_scene_readback.json`，当前身份注明observer_revision=v5-before-first-execution并刷新SHA。静态审计再次通过，未执行过的v4准备不冒充运行结果。新等待队列 `loss_observer_after_full_queue_v2.json`（PID2301628）恢复相同前置条件，下一运行标签仍native_loss_observer_v4以维持已有队列工具路径，实际observer版本以身份文件为准。

完整回放的控制器在observer3392首次color_progress=1，累计有效加热22.5177s，但当时样液仅保留74.6638%。事件已单独保存 `evidence/solver_full_color_complete_live.json`，视频和最终meta对齐仍待完成；不能将该事件记成任务成功或视觉通过。回架尚待本轮后续执行。

回架后实时几何检查：observer4487，试管相对架原点z=52.708mm，最近槽底z=23.4mm，高出29.308mm；倾角此前约14.1°。用未修改tube_in_slot纯函数检查live相对矩阵为False。记录 `evidence/solver_full_live_return_geometry.json`；尚未取得最终视频和在线分数，因此只声明该时刻未落座，不提前写最终score。保液该时刻68.9392%，本版仍不能交付。

后续分析脚本 `tools/analyze_native_loss_observer_v4.py` 已准备并编译：仅接受已完成审计的诊断，先按机器人状态精确对齐，再验证粒子快照shape/有限值、记录哈希，并要求运行时场景和tensor参数记录齐全。尚未执行；缺失任一读回不得标作诊断完成。新观察器不进入接收方运行依赖。

重要重复性反证：相同作者物理的solver短测与完整运行共同前缀不同。初步对齐frame0的管位置差仅0.0108mm，frame125为0.336mm，frame200为6.680mm，frame300为13.549mm；两轮机器人DOF最大差到frame300仅5.30e-5。完整运行frame300相对旧成功抓持偏差14.170mm、轴向差5.932°，没有复现单次短测3.587mm的改善。报告 `evidence/solver_prefix_full_early_repeat_comparison.json` 与 `solver_full_live_grip_rotation_comparison.json`；最终全量native-meta/动作审计待本轮结束，不将现象直接归因某个GPU或初始误差。此前“最小偏差组合”仅指一次短测，不能解释为稳定修复。后续优先解决液体及接触稳定性，再要求重复验证，不用该单次改善直接推进38次资格。

完整solver运行最终完成：7000步、score0.85、sr0，原动作逐条一致，7001观察精确对齐（误差0），四视频完整解码通过。最低保液60.6329%，首次跌破95%为动作frame380；最终5474/13905粒子在判定腔外。动作窗口6762次退出分类为mouth_compatible，包含重复退出，不能等同独立粒子数或证明全程无喷射。最终倾角14.129°，架局部z52.710mm，仍未落座。`evidence/solver_full_final_retention_and_return.json`保存最终证据。此前前101观察推断frame0=414已由全量meta对齐确认，短测与完整运行抓持重复性差异成立；不据此归因单个参数或GPU。

主实现者抽看左腕/overlook的300/3000/3500/3600/3700/4000/7000帧：样液可见蓝到橙，松爪后试管留在架上倾斜，未在所看终帧倒到桌面。正常腕视角管底裁切、俯视遮挡仍限制液柱和连续显色验收；不能因看到橙色就称完整视觉通过。记录 `evidence/solver_full_visual_review.json`。本版交付FAIL。

正常审计结束后队列已启动1200步失液读回诊断（标签native_loss_observer_v4，身份中实际observer为v5），当前仅此任务使用GPU。下一步先分析实际offset、重力/单位/材料与快照，尚无新的物理修复候选获运行通过。

失液诊断在observer500已获得实际tensor读回：Sample/Bath的solid_rest、fluid_rest、particle_contact offsets与独立冷态夹具逐值一致；运行时metersPerUnit=1、Zup、gravity=(0,0,-1)*9.81，PBD材质gravityScale=1，黏度/阻尼均0。报告 `evidence/native_loss_effective_parameter_comparison.json`。仅排除这些已测参数差异，不推断完整运行环境相同。

复查独立10秒冷态夹具终态速度读回，中位0.183m/s、99分位0.747m/s（`evidence/cold_fixture_height_speed_reference.json`）；保液通过不等于已静止，速度仍需结合点位置变化解释。下一单变量诊断候选将SamplePhysics黏度0→1.7e-6，值来自远端Isaac4.1 particleUtils.AddPBDMaterialWater在米制下的水预设，只测试该系数，不同时套用cohesion/surfaceTension或改变粒子数/体积/碰撞/速度上限。它是稳定性假设，尚未获得运行改善证据，不能提前采用到交付。

黏度单变量候选已完成静态审计：相对正在运行的读回基线，YAML不变，USD仅SamplePhysics.viscosity0→1.7e-6及observer输出路径变化。等待队列 `water_viscosity_after_readback_queue.json`（PID2328560）要求前置正常结束、1201观察精确对齐、保液失败复现、实际offset匹配、米制Zup和基线黏度0后才启动该候选；任一不满足则停止，不自动重试。当前候选未执行，不宣称黏度修复有效。

只读失液基线已正常完成1200步（该短测score0.15），1201观察与原生meta精确对齐、原动作一致、四视频解码通过；最低保液87.4290%，13份快照shape/有限值检查通过。`native_loss_observer_v4_h13_a_readback.json`保存实际参数及快照哈希，frame300抓持偏差5.597mm，再次提示抓持重复性范围。队列通过既定门禁后已启动黏度单变量候选（supervisor2332782），当前仍在初始化，尚无改善结论。候选分析和同动作时刻对比脚本已编译，未将任何准备状态当作运行通过。

失液基线在动作frame66（尚未夹起）的快照分区显示，中部/中心粒子也存在非零速度读回，非仅靠壁区域高速；探索性统计 `evidence/baseline_internal_motion_spatial_bins.json` 使用近似圆柱分区，不能当接触力定位或密集轨迹速度认证。黏度候选observer240的速度中位约0.206m/s，与基线早期约0.203m/s接近，当前仅预热期线索，不据此宣布参数无效或通过。候选已开始原动作，仍待完整1200步同口径比较。

补查普通top_camera的300/1200/1600/2000/2400/2800/3000帧：加热保持阶段可清楚辨认样液蓝/青、绿、黄、橙到终态橙色，弥补此前仅左腕/overlook遮挡的证据缺口。`evidence/solver_full_top_color_review.json`仅对抽样阶段可见性PASS，不认定全帧连续性/无喷射，也不改变本版保液与回架FAIL。暂不改摄像头。画面还保留热板OFF字样，与加热遥测不一致，记录为视觉状态一致性后续项；当前物理对照不夹带显示修改。

水预设黏度单变量已完成1200步并精确对齐：最低保液87.9324%，零黏度基线87.4290%，二者均失败；frame300抓持偏差17.790mm（基线5.597mm）。单次约0.5个百分点的差异不足以证明稳定改善，不采纳黏度改动。结果 `evidence/water_viscosity_paired_diagnostic.json`。不得据此推广“所有黏度设置均无效”。

下一诊断改为样液粒子尺度组，源于零黏度读回基线：particleContactOffset0.68→1.25mm，自动fluid rest对应点距1.485mm；同一初始填充包络和固定0.8mm初始边界留距，点数13905→1889，总质量仍8g。只对seen_scene10和对应unseen_prospect10 metadata初始点做诊断；同步points/canonical/velocities/ids/widths/extent、每粒质量标注以及isosurface gridSpacing/surfaceDistance。非粒子contact/rest、速度3m/s、粒子solver16、刚体几何/质量、动作和metric均不变。静态检查包含最近邻点距、数组长度、总质量、metadata其他字段深比较和关系不变，`evidence/sample_coarse125_prefix_static_audit.json`。参考task10的粒子接触尺度只用于选取试验量级，不继承其运行资格。

粗粒子短诊断已启动（supervisor2343692），仍须运行时实际粒子参数、保液、可见液柱/流动和抓持检查，静态准备不构成交付资格。实际模拟体积未要求与旧8mL完全一致，但不能以缩成不可见液滴通过。

粗粒子1889版本已完成1200步：1201观察精确对齐，最低保液94.0180%，frame300抓持偏差9.054mm。实际solid/fluid/particle offsets分别1.2375/0.7425/1.25mm，原动作一致、四视频完整解码通过。比细粒子基线有改善但仍FAIL，未证明重复稳定性。普通顶部机位frame1000能看清连续蓝色样液柱，未因减少点数缩成不可见液滴；仅单帧检查，不替代完整显色/流动/喷射验收。`evidence/coarse125_visual_review.json`。

下一单变量诊断仅将当前粗粒子基线的maxDepenetrationVelocity2→1m/s，总移动maxVelocity保留3m/s。目的为区分碰撞纠正与搬运速度，验证是否减少持续弹起；不宣称该参数必然能钳制所有流体内部速度。历史0.2试验使用此前失稳的offset/采样组合，不能把它的失败推广为当前粗粒子基线，也不重复原旧配置。新候选仍需原动作短测，尤其检查搬运是否出现跟随不足和穿壁。

粗粒子depen1短测完成：1201观察精确对齐，最低保液95.0768%，frame300抓持偏差5.630mm；仅一次短测擦线通过保液数值，未证明无持续失液、重复性或完整回架。报告 `evidence/coarse125_depen1_paired_diagnostic.json`。下一运行不继续改物理，恢复7000步上限验证完整原动作；observerv6仅补充读取maxDepenetrationVelocity属性。

本次完整范围诊断新增外部提前结束条件：加热有效且样液count1889时，连续3个观察保液低于95%则保存原始观察、停止本次owned helper/服务，报告STOPPED_UNQUALIFIED，不产生虚构完整评分/视频资格。该条件只是节省已失败诊断的剩余运行时间，不改变交付“每一步≥95%”要求；即使只有一个低于线的步骤且未触发提前结束，最终保液审计仍失败。6个guard检查覆盖初始化、达标、两次不足、间断不足、连续三次不足及错误粒子数，全部通过；`evidence/coarse_depen1_full_retention_guard_checks.json`。物理属性/关系比较不变，仅YAML1200→7000和只读observer脚本变化，`sample_coarse125_depen1_full_static_audit.json`。完整范围诊断已启动（supervisor2359154），尚无结果。

完整范围coarse/depen1诊断触发提前结束：observer1613–1615连续保液94.9709%，有效加热约7.69–7.71s，随后停止本次owned helper。状态STOPPED_UNQUALIFIED，未生成完整任务得分/视频资格；GPU和本次进程已核实释放，无cleanup_pending。证据在 `sample_coarse125_depen1_full_h13_a_run.json`。一次短测95.0768%没有足够余量，不能采用。

下一隔离只改液体初态：从已完成的depen1短测observer120（动作frame=-294，机器人动作前）快照取1889个局部粒子位置，全部严格位于实际管腔profile内，z范围2.331–31.711mm。初速度仍0，总质量/粒子数/物理参数/容器和原动作不变；同时更新USD points/canonical/extent和该case的task data初始点，运行过程中不回写粒子位置。该快照并非静止状态认证，只用于检验已压实位置初始化是否比规则点阵减少早期内部运动；不把近邻距离小直接判为液体粒子几何重叠错误。原SDK文档说明fluidRestOffset参与目标密度，并非硬球半径；参见[粒子参数说明](https://docs.omniverse.nvidia.com/kit/docs/omni_physics/latest/dev_guide/particles/particles.html)。候选尚未运行，后续仍需实际保液和液柱可见性检查。

压实初态候选静态审计通过（sample_compact_seed_prefix_static_audit.json）：只改SampleParticles初始点/canonical/extent及该case metadata的粒子初态、只读观察器输出；其余metadata深比较一致，运行物理参数/材质/刚体关系均不变。已启动1200步诊断（supervisor2365422），尚无运行改善证据。

压实初态短测完成并精确对齐：最低保液95.2356%，原规则初态95.0768%；frame300抓持偏差7.984mm（原5.630mm）。一次仅约0.16个百分点的差异不足以认为消除持续失液或改善重复性，暂不采纳此初态。报告 `evidence/compact_seed_paired_diagnostic.json`。

下一单变量使用原规则点阵coarse1889/depen1基线，只在evaluation YAML新增MinVelocityIterationCount=4；远端Isaac4.1 schema明确该场景属性默认0、覆盖rigid bodies/cloth/particles。物理dt仍1/120，不增加物理子步；位置迭代、PBD配方、几何、原动作和metric不改。静态审计 `sample_velocity4_prefix_static_audit.json`通过，当前已启动（supervisor2372505）；须在observer500读取实际场景值，不能只看YAML宣布生效。该选择参考[PhysX关于碰撞纠正与速度迭代的说明](https://nvidia-omniverse.github.io/PhysX/physx/5.1.2/_build/physx/latest/class_px_p_b_d_particle_system.html)，仍是任务级试验，不建立通用默认。

补查的fluidBoundaryDensityScale仅在底层C++文档出现，本机USD schema未找到对应字段；未创建无效自定义属性或修改SDK/核心来尝试它。

速度迭代候选observer500已读回physxScene:minVelocityIterationCount=4，确认设置进入实际Stage。分析脚本另要求全部匹配观察dt=1/120（绝对容差1e-7），不会把求解迭代数当作新增物理子步。当前仍运行，未给出效果结论。近期12组记录另存 `native_liquid_diagnostic_ledger_20261016.json` 并同步仓库快照，保留各自完整/短测/中止范围。

MinVelocityIterationCount=4对照已完成1200步，1201观察精确对齐、实际dt=1/120及运行时场景值4均验证；最低保液94.4944%，frame300抓持偏差5.871mm，未优于原基线95.0768%/5.630mm，暂不采用。报告 `evidence/velocity4_paired_diagnostic.json`。

按用户已允许的体积调整，下一组以原规则点阵coarse/depen1、MinVelocity默认0为基线，将名义样液目标8→4mL、总质量8→4g。通过原管腔分段圆台体积积分求得4mL填充高度，在相同1.485mm点距及0.8mm初始边界留距下生成923颗；同步volume标注、点/ID/宽度/每粒质量、canonical与task data初态。点距/接触范围/求解器/容器/动作/metric不变；真实仿真后的体积及可见性不能仅凭名义4mL宣称通过。静态审计 `sample_volume4_prefix_static_audit.json`确认只改该体积组及只读观察器，metadata其余字段一致。短测已启动（supervisor2379973），未运行通过前不进入交付。

4mL/4g短测完成：1201观察精确对齐、原动作一致、四视频解码通过，最低保液98.3749%，frame300抓持偏差7.946mm。正常top_camera frame1000仍能清楚辨认蓝色样液，较8mL候选液柱更短；仅单帧可见性PASS，不是完整显色/流动或回架资格。`evidence/volume4_paired_diagnostic.json`与`volume4_visual_review.json`。

同物理版本完整7000步上限诊断已启动（supervisor2387086）。静态比较仅num_steps1200→7000和observer输出路径变化；提前结束guard从identity读取预期count923，4个分支测试通过，防止沿用旧1889硬编码而失效。审计 `sample_volume4_full_static_and_guard_audit.json`。运行仍有低于95%时的诊断停止机制，未完成不得冒充完整得分；当前尚无长时保液、完整显色、回架或重复资格。

4mL完整范围诊断已提前结束：首次门槛触发于observer4123–4125，保液94.9079%/94.7996%。触发前observer4000倾角11.32°、4050为23.58°、4100为40.63°、4120为85.80°，到4123已97.56°，且heating_block_reason=sample_not_in_water。因此倾倒先于guard停止，不把清理后的132.9°作为唯一失败证据；此次失液门槛发生在回架阶段。`evidence/volume4_full_return_abort_review.json`。再次核实本次进程/GPU已释放。

语义更正：旧guard文字称“加热阶段”，实现实际以累计heated_seconds>0.1作为开始门槛，包含之后的回架。此处明确修正描述，不改历史原始报告和阈值。提前结束没有完整在线得分或完整视频资格。当前4mL配置在完成变色及回架倾倒前仍≥95%，继续优先定位抓持/管架差异；不把倒置后的洒液归因成新的直立保液缺陷。

准备旧场景A/B以隔离管架合同差异，均无真实样液，仅作诊断：A保持旧场景物理，新增只读pose/rack属性观察器及300步cap；B仅关闭原18个补充Cylinder、将Cube015 approximation从sdf改none、contactOffset0.1→0.5mm，模拟修复版管架。旧试管、求解器、原动作、metric和其他场景属性保持。A/B分别通过静态差异检查，未往metric追加观察代码。

A已完成并通过原动作/视频审计，301观察精确对齐；全部300个动作后试管及link6世界位置相对既有旧成功pose轨迹最大差均0，运行时管架启用19个碰撞体。`evidence/old_rack_control_prefix_h13_a_pose_analysis.json`。这验证该旧场景前缀的观察方法；不推广为含真实液体时的非干扰证明。B已启动（supervisor2401538），尚无效果结论。

管架分组对照完成：旧控制A第300步抓持差约0；新approx/contact+关18支撑的B为6.328mm；仅关18支撑C为5.185mm；仅改主网格approx/contact且保留支撑D为6.282mm。均为301观察精确对齐的旧无真实样液前缀。`evidence/old_rack_ablation_summary.json`保存哈希与范围；不能推广为所有真实液体回架的单一根因。补查发现实际修复版还移除了Cube015的PhysxSDFMeshCollisionAPI，B/D未移除该API，因此它们隔离的是属性组而非穷尽全部元数据变化。

随后在真实4mL版本恢复完整旧管架物理，包括SDF API/approx/contact及18支撑；静态逐项对照与旧作者配置一致，GPU运行正常。1200步最低保液98.6999%，但第300步抓持偏差16.027mm，恢复旧管架不足以恢复真实液体下的抓持。`sample_volume4_oldrack_prefix_static_audit.json`和`sample_volume4_oldrack_prefix_h13_a_analysis_pose.json`。没有把旧假液体对照提升为真实液体资格。

刚体参数控制old_body_properties_prefix已完成：只读DynamicControl查询不改变旧参考前300步轨迹。实际试管mass0.018008921kg、惯量/COM匹配作者值，刚体请求迭代16/1，机器人关节系统128/4；运行时旧版也补充PhysxRigidBodyAPI并有sleepThreshold0。因此静态API缺失不能独立解释新旧差异。该getter记录的是actor请求值，不是GPU岛内最终迭代次数的直接测量。接口依据[Isaac4.1 Dynamic Control](https://docs.isaacsim.omniverse.nvidia.com/4.1.0/py/source/extensions/omni.isaac.dynamic_control/docs/index.html)。

仅将SampleParticles.particleEnabled=False的300步机械隔离在初始化（尚无动作）触发NpPBDParticleSystem::removeParticleBuffer“buffer was not added”错误；首错停止，无抓持结论。保留sample_off_oldrack_prefix_h13_a_run.json。改为新的sample_absent_oldrack_prefix：将样液粒子/系统Prim均inactive，并移除仅该case的SampleParticles初态恢复项，浴水及其他物理保持。静态审计已通过并启动（supervisor2439082）；这是诊断性无样液物理场景，绝非可交付候选。观察器显式记录Prim active状态，避免仅看particleEnabled属性误判。

扭转摩擦和流体边界密度仅进行了接口调研，未混入当前场景。后者未发现USD暴露字段；扭转摩擦有接触patch适用限制，接触报告中的20–24个点不等于已知patch锚点数，暂不凭该计数选择参数。

样液系统inactive诊断已正常完成300步：301观察精确对齐，运行时样液粒子/系统均inactive；第300步抓持差仍9.114mm。实际试管/烧杯质量、惯量和16/1请求迭代与旧控制一致，机器人128/4一致。该结果不能把全部偏差归为样液重量；浴水及新场景其他设置仍存在，不构成液体关闭的交付路线。

继续静态核对发现烧杯3个原启用碰撞面从旧自动contact/rest改成显式0.8mm/0，几何/相关SDF API相同。新只读控制old_shape_offsets_prefix用Tensor getter读取实际碰撞形状间距，并保持旧前300步轨迹不变：旧烧杯3个contact offsets为1.547600/1.362500/1.362500mm，rest均0；试管单个shape为10mm/1mm。它们是实际getter结果，不把默认自动值猜成固定20mm。

真实4mL+旧管架候选sample_volume4_oldbeaker_prefix现仅将这3个烧杯碰撞面的contact/rest设回SDK自动值(-inf)，其他物理/动作/metric不变；静态审计通过，已启动（PID见CURRENT_STATUS）。观察器同时读取实际接触间距、刚体属性和粒子数据，必须核对运行时回到旧值后再解释结果。尚未解决抓持，仍不可交付。

恢复烧杯自动间距短测已完成：1201观察精确对齐，最低保液97.8332%，第300步抓持差1.645mm（此前真实4mL+旧管架为16.027mm）。普通顶部机位frame1000可辨认样液。仅一次短测，不能据此判定稳定修复；当前同物理版本完整7000步上限诊断已启动，静态差异只包括cap及observer输出路径。新的guard记录实际阶段与回架姿态，并明确作用于“开始加热之后”，包含回架；4个分支测试通过。

实际形状读回还有一个待验证点：旧烧杯shape_count3，新烧杯shape_count260，包含3个原形状及257个collisionEnabled=False的辅助形状；当前原3个接触间距已匹配旧值。被登记为shape不证明仍参与碰撞，不将其直接解释为重复物理碰撞或私自移除正在运行的几何。后续如需清理，必须独立验证开关语义和行为。

恢复烧杯自动间距的完整范围诊断已停止、不合格：observer3886首次保液94.9079%，随后连续两步94.7996%；试管约4.6度，阶段为提离烧杯，累计有效加热22.518秒。检查停止前native3700–3886，7个退出事件均与穿过真实管口一致；该窗口未发现穿底/穿壁类退出。试管原点最高速度1.637m/s，包围盒角点1.686m/s，不能据此将失液归于超过3m/s上限。无完整任务分数或最终meta对齐，证据evidence/oldbeaker_full_withdrawal_abort_review.json。实际进程已退出且GPU空闲。

下一单变量诊断sample_surface_tension_prefix保持4mL/4g、923粒子、旧管架及烧杯自动接触间距，只将SamplePhysics.surfaceTension从0改为0.0074。这是本机Isaac4.1 particleUtils.AddPBDMaterialWater在metersPerUnit=1时的表面张力分量，不是采用完整水预设；黏度、cohesion和其他物理均不变。先1200步原动作短测，若有改善再检查倾倒流动及完整回架，不能靠液体凝住取得保留率。retention95_checks_v3.observe已检查非有限坐标和粒子shape；无需为本实验修改观察算法。遵循MAT-001/003、VAL-001/002/003/008，本次只是未合格任务诊断，尚无可推广的通用规则变化，规范与设计契约无需修改。

表面张力候选静态审计通过：全Prim/原API/关系一致，物理属性只有surfaceTension变化，另一差异为只读observer输出路径；相对资产路径相同且已解析文件内容哈希相同。SampleSystem物理材质绑定为SamplePhysics。另测NaN、Inf及粒子数量变化均被既有统计拒绝，正常输入通过。证据sample_surface_tension_prefix_static_audit.json。远端已启动supervisor2480016，进程存活已核对；当前仅1200步诊断，未取得运行结果。

并行只读语义审计发现4mL候选仍保留fehlings:sample_height_m=0.043780562m，按当前管腔积分对应约8.06484mL；4mL正确名义高度为0.023563689m。该属性被FlowController.compute直接传入bath_contact，并非无用标签。提取现有纯几何函数的边界检查显示：竖直深浸/竖直离水两例结果相同，而倒置且仅旧上段触水时旧高度误判contact=True。该检查为合成几何，不声称测量了原动作计时偏差，也不将其解释为最新直立提管失液根因。当前运行字节不动，后续独立候选必须修正高度并复核计时/重置。证据evidence/sample_volume_height_semantics_audit.json，工具audit_sample_height_semantics.py。依据STATE-001/002、MAT-003，不改变规则或放宽成功条件。

液柱高度独立修正工具已准备但未执行：sample_fill_height.py按分段圆台积分反算名义体积，圆柱/圆锥解析解与6类无效输入共8项检查通过（sample_fill_height_tests.json）。prepare_sample_height_prefix.py要求显式源identity，新建私有候选，仅改sample_height_m，保留颗粒、材质、动作及metric；等待当前表面张力结果后选择源版本，不修改活动实验。已有该case task_data未发现同名高度/体积覆盖项；原生重置一致性仍待运行验证。

表面张力0.0074短测已完成，1201观察与meta精确对齐、原动作一致、四视频完整解码通过：最低保液98.0498%（0张力97.8332%，差2颗粒子），frame300抓持偏差7.062mm（基线1.645mm）。单次微小保液差异不足以证明稳定收益，暂不采用；不是证明所有表面张力设置无效。evidence/surface_tension_paired_diagnostic.json。下一组从0张力oldbeaker基线仅修正4mL名义高度，并恢复7000步上限进行完整范围诊断；observerv8只读增加每步height/volume字段，便于确认重置后实际读值。保液门槛提前停止规则仍保留，未完成不得声明完整分数。

高度修正版sample_height_full静态审计通过：与0张力基线相比仅名义height和只读observer变化，YAML仅1200→7000，其余任务文件哈希及关系保持。远端已启动supervisor2487057；此为完整范围诊断，不提前声称完整分数、显色、回架或95%资格。identity与static_audit位于evidence/sample_height_full_*。

高度修正版初始化运行读回已确认height=0.0235636886m、nominal volume=4mL，当前观察未被旧task data覆盖。样本数与最后observer编号见evidence/sample_height_full_initial_runtime_check.json；只覆盖本次初始化，不当作跨回合重置或完整动作通过。完整范围回放仍运行，尚无最终结果。

为后续判别静置速度读回与真实相对运动，新增私有particle_displacement_check.py及未部署observerv9：逐粒相同ID的相邻世界/容器局部位置除物理dt，分别与USD世界速度比较，明确区间平均位移率不等于瞬时速度。纯移动容器、流体相对运动、读回不一致3个控制和dt/shape/NaN3类异常检查通过，evidence/particle_displacement_check_tests.json。仅准备，当前height_full继续v8，不改活动实验；不能把预热USD速度中位约0.18m/s直接宣称为已证实物理抖动。

高度修正完整范围诊断已STOPPED_UNQUALIFIED：observer5007首次94.9079%，5008/5009为94.7996%，显色逻辑1.0、有效加热22.517677s。停止前倾角14.985度；相对旧成功终态，试管世界位置高31.320mm、横向约11mm，不能视作回架成功。无完整原生分数/最终meta对齐；已核实owned进程与GPU释放。证据sample_height_full_abort_review.json。计数包含初始化observer15的17个wall_or_unresolved事件，不将其自动认定为episode穿壁；其余退出分类保留原始记录。

加热保持窗口observer1500–2600的包围盒角点逐步位移速度最高0.09663m/s，退出事件时最高0.04040m/s，仍发生管口退出；该段不支持单纯归因于机器人速度超过3m/s。报告sample_height_full_hold_interim_review.json只覆盖该窗口且无最终meta对齐，不是全轨迹瞬时速度上界。下一候选只换v9位置差分观察器、1200步cap，不改物理或反应逻辑，先验证USD速度读回与连续位置变化的关系。

v9位置差分候选静态检查通过：场景唯一属性变化为只读observer脚本，YAML7000→1200，物理/反应/原动作/metric保持；sample_motion_readback_prefix_static_audit.json。远端supervisor2497027已启动，尚无运行读回结论。

v9位置差分1200步回放完成：1201观察精确对齐、frame0=observer414，最低保液98.1582%、frame300抓持偏差2.128mm，原动作及四视频解码审计通过。预动作observer200–350的局部位移率每步中位数的中位数0.013124m/s；native800–1200段为0.223488m/s。observer415（首动作）局部中位位移率0.365393m/s，前一步0.013948m/s，试管世界位置相同；400/500的已记录USD碰撞/刚体/粒子属性一致。证据sample_motion_readback_prefix_h13_a_motion_summary.json和sample_motion_start_boundary.json。尚未证明动作setter、初态恢复、求解器或原始/显示位置通道中的哪项导致；不继续仅凭该相关性改黏度。

新的300步startup-boundary候选只读v10补查400/414/415/500的compiled形状/刚体/粒子/场景属性，以及simulationPoints与points差值和额外快照；物理、反应、动作、metric不改。当前只是准备，需完成静态审计和运行。

v10候选静态审计通过，仅observer脚本与1200→300诊断cap变化。远端supervisor2503908已启动，保留完整原动作前缀；结果待核对。尚未获得首动作突变根因或新的交付资格。

v10启动边界300步完成并精确对齐（frame0=414）：首动作局部粒子位移率中位数0.37534m/s，前一步0.01159m/s，再次出现突变。400/414/415/500的compiled刚体/shape offsets、粒子offsets及场景/材质USD属性一致；runtime_colliders到500仅刚体velocity/angularVelocity运动读回不同，不是设置变更。simulationPoints与points有差异，但本机SDK schema及PhysxParticleSmoothingAPI.py说明该字段涉及平滑位置与物理位置读回设置；当前关闭smoothing，不把存在的simulationPoints自动视作实时物理真值。evidence/sample_start_boundary_prefix_h13_a_boundary_analysis.json。

下一单变量对照sample_minpos128_prefix仅将YAML场景MinPositionIterationCount1→128，MaxPosition255、dt1/120、923颗粒子及其solver16、材质/容器/动作/metric保持。目的是检验迭代下限对首动作突变的敏感性；机器人请求128次不能证明内部实际岛迭代切换，明确仍是假设。不把提高下限等同于提高物理Hz或新增子步。300步诊断不构成回架/保液交付资格。接口参数背景见[PhysX PBD迭代API](https://nvidia-omniverse.github.io/PhysX/physx/5.1.2/_build/physx/latest/class_px_p_b_d_particle_system.html)，最终以目标4.1运行读回/行为为准。

minpos128静态审计通过：USD只读observer路径变化，YAML唯一物理配置差异MinPositionIterationCount1→128，300步cap不变。远端supervisor2509503已启动；未声明通过，待运行时读取实际场景值并比较边界运动/抓持。

MinPosition128对照300步已完成，301观察精确对齐，原动作及视频解码审计通过，运行时min128/max255、dt1/120确认。预动作observer200–350局部位移率中位数0.22676m/s，原配置0.01302m/s；414/415为0.23868/0.23565m/s，不再首步突增而是启动前已持续较大运动。该提高下限方案暂不采用；仅300步保液99.4583%不能抵消运动/完整任务未验证，第300步抓持偏差5.90659mm。evidence/minpos128_boundary_comparison.json。

下一组从原min1/max255边界基线仅将MaxPositionIterationCount255→16，保留min1，不从min128版本继续叠改。粒子solver16/count923、材质、碰撞、动作、metric与120Hz均不变；单变量静态检查通过，supervisor2514354已启动。检验迭代上限敏感性，同时必须检查机器人抓持精度，不能把降低求解精度默认当成可交付修复。sample_maxpos16_prefix_static_audit.json。

MaxPosition16对照300步完成：301观察精确对齐、原动作一致、四视频完整解码通过，运行时min1/max16、dt1/120确认。414/415局部位移率中位数0.013645/0.013829m/s，原max255为0.011588/0.375342；正式动作段最低保液100%，包含初始化则99.1333%，两者不可混写。第300步抓持偏差18.0737mm（原边界基线5.9294mm），为明确风险。三组对照见position_iteration_three_way_comparison.json；暂不宣布回架修复或通用solver默认。下一轮保持max16物理，仅恢复7000步cap完整验证；不能因抓持偏差较大直接替代完整终态验证，也不能因短测保液100%宣布合格。

MaxPosition16完整范围候选静态审计通过，只改cap300→7000与只读observer路径；远端supervisor2519311已启动，保液提前结束机制保留。任务成功、持续保液和重复性仍待验证，short100%不提升为full PASS。

max16短测普通top_camera抽查0/200/300帧：300帧可见试管底部蓝色样液，隔透明烧杯可辨认；0/200帧试管不在该近景裁切范围，不能解释为液体消失。热板OFF字样仍待视觉状态修正。primary implementer非独立审查，范围仅3帧，不构成全程无喷射或完整显色；evidence/maxpos16_short_visual_review.json。

为区分低迭代对抓持的影响，准备旧假液体场景MaxPosition16、300步对照，尚未运行。首次准备脚本错误假设YAML显式给出迭代字段，在写配置前失败；已查本机SDK schema默认min1/max255，再生成新的独立候选。失败草稿保留，不启动、不交付；当前真实液体完整回放未受影响。

MaxPosition16完整范围回放首次取得原生score1.0、success_rate1，3762步自然终止；3763观察精确对齐、原动作一致、四视频完整解码通过。正式episode最低保液99.67497%，初始观察总段最低99.13326%；终态倾角0.329度、架局部原点z=0.024409m。正常top机位抽查蓝/青→绿→黄→橙可见，overlook终帧夹爪已撤回。仅单次代表来源13，绝非全19/重复或交付资格。

关键未通过项：episode共有3次退出，frame180粒子305和frame3465粒子652为侧壁方向退出，frame3473粒子742从管口退出。后续快照确认前两颗超出外壁：305在observer600半径0.103m，652在observer3960半径0.414m，不能当作仅容差越界。正式任务1分/保液99.67%不满足“无穿壁”，完整物理验收仍FAIL。两次退出时试管原点速度1.057/1.421m/s，包围盒角点1.071/1.430m/s，当前样液maxDepenetrationVelocity=1m/s；相关性不能单独证明限速根因。证据sample_maxpos16_full_episode_exits.json、maxpos16_side_exit_motion.json和maxpos16_full_visual_review.json。OFF显示也仍待修正。

下一完整范围候选仅将样液maxDepenetrationVelocity1→2m/s，总maxVelocity仍3，保持maxPosition16、923粒子、原动作、反应逻辑和metric；用同一完整动作检验能否消除两处侧壁退出。此前旧高迭代组合depen2表现不佳不能直接推广到当前稳定低迭代组合。不进行已准备的旧假液体max16对照，先解决真实液体剩余物理缺陷；旧对照只保留为未运行工具。

低迭代/depen2完整诊断静态审计通过，supervisor2530841已启动。首次满分与未通过边界单独汇总在[首次原生成功及侧壁缺口](2026-10-16-task12-first-native-success-with-side-exit-gaps.md)，避免只看到1分而漏掉穿壁失败。
