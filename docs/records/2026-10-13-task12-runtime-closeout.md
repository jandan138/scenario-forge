# 水浴四项运行交付收尾：2026-10-13

状态：执行中，未发布。称量训练集保持后台渲染；水浴LeRobot本轮暂缓。

## 已知证据与计划

工作根为`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/task12_liquid_color_20261012`。
128MiB YAML候选的background3完整7000步通过运行检查，mixed5随后约3060步引擎失败，
首错为GPU articulation求解kernel launch失败。此前64MiB同案例一次完整通过，不能因此认定稳定。
原队列证据`evidence/stack128_native_cases.json`状态为STOPPED_UNQUALIFIED。

保持同一安装、原动作、120Hz及7000步上限，启动新进程独立复查。
辅助监督脚本`tools/run_recheck_native_case.py`从既有监督器派生，使用独立attempt/run ID，
不覆盖旧报告、不修改接收方代码。单次首错即停，既有45分钟上限保留。
复查状态由`evidence/recheck_current.json`指向。

随后按观测证据优先定位碰撞，再考虑液体负载。用户明确允许在控制实验支持后降低粒子分辨率，
前提是真液体、液量、液面、合理质量和变色效果保持，并重新验证保液及外观。
诊断隔离设置不能进入交付，所有资产修复按生产者职责在ConvertAsset侧产生。
最终同版本mixed5两次完整独立运行通过后，完成另四例、受影响功能测试及独立安装验收。

## 交付边界

只交付YAML、USD及依赖、task data和指定scientific metric；不改核心、SDK或机器人资产。
水浴成功机器人示范允许待重采，7000步时间预算限制保留；引擎崩溃不能算普通任务失败。
称量生产不停止、不重启，其他任务不在本轮修改范围。

## 规范与证据范围

遵循ASSET-001/003/005、MAT-001/003、VAL-001/002/003/004及维护流程。
规范无需变更：本轮是单任务故障定位和最终内容验收，不将未经证实的参数提升为通用规则。
现阶段未作新的资产修复或完成新的运行资格；后续结果在此追加并绑定实际run ID。

## 静态碰撞审计与未验证诊断

只读复核确认机器人处于RigidScene过滤范围内；试管120个直壁代理与353个底部代理互补，
不能盲目恢复旧粒子过滤列表（可能排除必要保液边界）。烧杯则同时存在两个原始SDF和257个保液凸包。
`current_collision_inventory.json`记录实际组合结果。

准备了ConvertAsset输出`task12_bath_sdf_filter_diagnostic_20261013`：
只给两套粒子系统追加过滤烧杯原始Torus和Beaker_Hollow_Body_Mesh，保留所有刚体碰撞、
粒子位置/速度、质量及其余属性。静态逐属性/关系比较只发现这两个关系变化。
本候选尚未运行、不是交付资产；当前PBD后端是否实际处理这些SDF仍未证实。
诊断夹具显式将两套粒子simulationOwner绑定到自身PhysicsScene，128MiB、120Hz。

旧128MiB失败server.log有64341条faceIndex警告；旧64MiB完成7000步的运行有482563条。
两者均从初始化出现，不能把警告数量当作崩溃原因。此前凸分解的内腔误差及shrinkWrap初始化
失败仍保留，不重复无新证据的候选。下一步依据同条件复查结果安排短保液与单变量对照。

## 用户纠正后的优先路线：标准SDF与已有粗粒子配方

用户指出烧杯已有统一液体/刚体碰撞的SDF版，并要求减少水浴专门增加的粒子参数与数量。
因此上述“保留补充凸包、过滤SDF”诊断只保留静态产物，不启动或推广。
改为先测试去掉257块额外保液凸包的烧杯，再测试已有粗配方；称量生产仍独立继续。

`standard_beaker_geometry_comparison.json`证明当前杯身、杯沿、壶嘴网格顶点/拓扑，
SDF或convexHull类型及SDF256分辨率与标准325mL烧杯一致。差异来自本次水浴后加的边界，
不需要重新制作烧杯模型。原标准969粒证据的目标液量为186.908mL，资格是一次quick/provisional，
不能转述为当前349.095mL或完整机器人资格；报告6.5368秒是观察耗时，不是仿真时长。

建通源USD静态对照：task01有1531粒（contact/rest5/5mm），task02有244+189粒（5/9mm），
task03有465粒（5/6mm）；它们的maxVelocity均0.6m/s，未显式作者粒子solver迭代数。
结果保存在`colleague_pbd_existing_configuration.json`，不增加这些任务的动态资格。

新浴液候选复用`ConvertAsset.convert_asset.liquid_autofill.recipe_payload()`的Task02 r10.3配方：
粒距5.82mm、particleContactOffset5mm、restOffset9mm、maxVelocity0.3m/s。
浴液96649→1670粒；样液13905粒保持原样，避免同时修改窄管参数。
保留浴液总质量349.095g与原目标液量，不能盲抄旧recipe的ParticleSet总质量0.00045kg。
粒子auto offsets、solver16、CCDfalse取自目标Isaac4.1的已安装schema默认；保留原透明材质，
按粗粒距更新isosurface采样尺度。更新canonical reset arrays、spacing、质量换算及bath_count，
不改反应计时和判定逻辑。实际沉降液量/液面、保液和视觉仍待测，粒子数下降不等于合格。

产物`task12_bath_coarse_recipe_diagnostic_20261013_v3`是待验证候选；早期authoring类型失败目录
及未补reset metadata的v2保留，不交付。`sdf_only_bounded.json`与`coarse_bounded.json`顺序等待
当前完整复查释放单卡后执行短冷态/升降测试，不自动发布、不启动后续机器人队列。

## 同版本独立复查结果

`task12_recheck_20261013T013309Z_bad08_20261013T013309_323568Z`完成7000步，0.15分、success0。
6542条源目标逐条一致，随后458步保持末动作；588个受保护文件一致，实际loader128MiB。
完整启动/worker日志无引擎错误或碰撞降级，保留82339条server警告；原生时钟120Hz，
四路视频各7001帧完整解码。机器人状态有限，关节最大单帧变化0.14496rad。
该结果说明失败未在这次重复中再现，不证明旧配置已修好；原失败仍是交付阻塞证据。
人工查看四路0/3500/6999/7000帧，机器人留在桌边，但玻璃对象在后方桌面、腕部视角有遮挡，
仅作为坏例运行的WARN记录，不认证成功回架或逐帧碰撞。证据为`recheck_20261013T013309Z_mixed_5.json`
与对应`visual_review.json`。独立SDF-only烧杯冷态对照已在释放GPU后启动。

## 简化烧杯与粒子测试、体积复核

SDF-only烧杯保留96649浴液：冷态1202步、升降2042步均PASS，两套粒子全程0越界、数量不变，
完整日志无引擎错误或碰撞降级。仅支持这两种范围，不替代机器人回放。
1670浴液候选完成三次独立10秒冷态和一次17秒升降，均PASS，样液13905不变。
预览透明且无明显粒子球，但仅凭图片难以确认水面，因此未放行。

SDK4.1自带`PhysxParticleIsosurfaceAPI.py`测试提供真实网格读取路径`<ParticleSystem>/Isosurface`。
额外只读采集在1202个物理步后导出网格；用现有isaac41 Python环境中的trimesh离线测量，
未修补、裁切或缩放网格。浴液是闭合、定向一致的单分量，包络体积252.971mL，中央水面中位94.297mm；
原目标349.095mL、原可视液面90.132mm。**1670版本体积偏小，不准入**，粒子q95接近原液面不能代替体积检查。
样液总有向包络体积7.669mL，主分量7.686mL，另有小的反向闭合内部表面，保留明细而非绝对值求和。
这些量是渲染包络，不宣称PhysX严格不可压缩体积。

据实测体积比例估计约2305粒，选择原始液体轮廓内5.25mm采样得到2320粒；
容器restOffset改用已有task01的5mm以减小空隙，其他浴液物理配方、材质和isosurface参数不变，
样液/刚体/反应逻辑不变。新候选`task12_bath_coarse_volume_fit_20261013`正在独立冷态/渲染测量，
不能复用1670版运行资格。总浴液质量仍349.095g，不用删粒或网格缩放伪造体积。

本轮`make check`退出0：1255 passed、1 skipped（653秒），lint和smoke通过；
日志`evidence/closeout_make_check_20261013.log`。这是仓库检查，不增加资产物理资格。

## 2320候选的限定准入与独立安装

2320候选闭合、定向一致的浴液包络350.1096mL，中央液面97.519mm，比原静态90.132mm高7.387mm；
三次独立冷态1202步和升降2042步均通过、两相全程0越界。自然预览透明且无明显颗粒球，
水面与透明玻璃的界面仍较微弱，标为WARN。该约7mm差异已向用户提出可选偏好问题；
给出充分回答时间后按推荐口径继续验证，未伪称用户已回复。

新候选20场景完成闭包及相同物理配置检查；41份task data只重建BathParticles初态点阵，
逐项恢复该数组后与原metadata内容相同，样液、布局、动作、指令及计分数据均未改。
YAML/metric沿用；仅USD和task data产生本轮新差异。新归档703个离线成员，向原版base工作树
`receiver_archive_install_20261013T024107Z`安装，离线与metric所有文件哈希一致。
身份保存在`rack_candidate_install_identity.json`，旧身份已留在`history/stack128_before_coarse_20261013`。

首例`task12_recheck_coarse2320_a_bad08_20261013T024413_499989Z`已启动，尚待完整结果。
后续工具`run_coarse_after_first.py`必须等首例完整及人工画面审查，再执行安装版normal/tilt/offcenter/wall，
wall沿用明确测试专用夹持；然后第二次mixed5及其余四个文档坏例。每次首错即停，不自动发布。


## 最终规则版本与夹具排障（04:24 UTC 更新）

用户已明确接受350.1mL包络及中央液面约高7mm，要求保持已有PBD设置继续。
此前粗粒子v1首例`task12_recheck_coarse2320_a_bad08_20261013T024413_499989Z`
完整7000步、0.15分/success0，无引擎错误；它不是最终规则版本的完整验收。

发现本轮把渲染isosurface的8mm距离误填到触水判定补偿中：实际控制器用粒子高度q99.5加补偿，
8mm会预测104.978mm，实际中央网格97–98mm。先运行真实嵌入函数的失败回归，恢复原1.2mm后
估计98.178mm并通过；20场景仅`repair:waterbath_config.bath_surface_distance`这一字段变化。
物理/材质/初态不变的比较允许复用冷态和升降证据，最终任务运行仍须重做。
最终归档独立安装为`receiver_archive_install_20261013T031857Z`，703个离线成员、两个metric项，
20闭包/51配置通过。依据`coarse_surface_rule_fix.json`和`surface_estimate_installed_pass.json`。

最终版normal夹具最初把试管预放入已生成水粒子中，形成126颗直接重叠，导致PBD有效性守卫拒绝加热。
改为测试脚本从水面上方缓慢下降6秒，未在Play后回写粒子，液体有效、浴液0越界、全反应/重置数值通过。
41份正式task data的试管均在烧杯外（XY最短间隔0.2112m），该初始重叠不属于交付初态。
证据`normal_fixture_initial_overlap.json`、`initial_layout_no_tube_bath_overlap.json`。

但人工查看新夹具发现玻璃外壳画面停在初始上方，实际物理试管和液体已在杯内。
即使USD根变换与DC物理位姿相差小于3e-8m，仍不能据数值宣布视频合格。
PhysX Fabric扩展原本关闭，关闭对照未解决；暂未唯一定位原因，也未证明正式动态任务受同样影响。
当前只在独立辅助脚本核对显示时间码、渲染delegate及非碰撞玻璃的重新注册/不透明材质对照。
这些是诊断，不修改接收方USD、GenManip核心、SDK或机器人。错误画面视频不交付。

`coarse_final_v2_queue.json`已因首个夹具失败停止；不要原样重启，也不要把旧版normal/guard报告
写成最终版通过。下一步先通过短画面对齐，再做最终版反应/守卫、同版本mixed5两次及另四例。
规范无需变更：上述是本任务夹具及字段误用修正，按MAT-002和VAL-001/003保留失败与视觉边界。
称量600条持续在独立机器渲染，04:18 UTC已完成212条；未停止或改动其生产版本。


### 短画面对照推进与后台验证（04:30 UTC）

`coarse_v2_render_sync_20261013T042429Z`确认PhysX Fabric和Hydra Fabric delegate都关闭；
Default/0/当前显示时间码的USD变换一致且无时间样本。禁用GlassShell后悬空玻璃消失，重新启用仍在旧位置；
绑定不透明材质则显示在正确杯内位置。不能唯一定位内部原因，也不能归咎于透明度数值本身。
`coarse_v2_glass_restore_20261013T042658Z`随后恢复原透明材质，试管正确包住杯内蓝色液体，
继续120个原生物理步后仍对齐，已人工查看两张图片；仅限短时静止夹具资格。

完整夹具`probe_task12_inserted_final.py`在物理下降完成后暂停物理，做一次测试专用材质重绑定刷新，
再恢复原始binding targets/strength，移除临时材质，确认刷新不增加物理步；之后才录制完整演示。
未改原材质参数、粒子、碰撞或接收方文件。该措施不是正式动态任务的修复证明，后续原版机器人回放
须独立核对运动玻璃。不能把测试工具作为交付依赖。

后台`inserted_final_fixture_queue.json`等待完整normal报告后顺序执行tilt/offcenter/wall，首错停止，
不自动发布或提升原生资格。完整视频人工检查和六次最终原生回放仍待做。
最终安装版真实控制器十项测试通过，日志`coarse_v2_contract_tests.log`；它不代替渲染/原生验收。


## 最终版功能通过与原版回放启动（05:05 UTC）

完整normal及tilt/offcenter/wall已完成，状态`inserted_final_fixture_queue.json`。
normal在原生120Hz下总6127步，本次随机反应终点约43.004秒有效加热；演示1311帧/30fps/43.7秒。
已人工看初始、10秒、25秒、终点与重置图片：蓝→绿→黄橙→橙红→蓝，玻璃在杯内正确包住样液。
完整视频解码通过；不是逐帧物理认证，也不把这次43秒写成所有配置的固定时长。
三个负例分别由倾斜、偏心、实际贴壁11接触点触发停止计时，液体有效；四份完整SDK日志均无引擎error或碰撞降级，
警告分别42/34/31/34条。`coarse_normal_visual_review.json`与`inserted_final_fixture_acceptance.json`绑定输出。

用户确认保持当前外观，优先证明同事原版程序无需测试刷新步骤。已启动最终安装版
`task12_recheck_coarse2320_v2_a_bad08_20261013T050511_085099Z`，原始mixed5目标逐帧回放，
不增加材质刷新，不修改核心或机器人；原生120Hz/7000步。其运行/视觉尚未完成。
续跑协调器`coarse_final_v2_resume_queue.json`必须等本条完整验收及实际移动玻璃人工审查，
才执行第二次mixed5与四个文档坏例。旧`coarse_final_v2_queue.json`保持失败历史，不覆盖。
最终封包工具已改用续跑队列，并要求首条原版玻璃审查；演示中的测试刷新在说明和manifest中明示，
没有生成release或READY。规范无需变更，继续按VAL-001/003区分演示和原版执行证据。
