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
