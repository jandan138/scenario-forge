# task12／task18固定浴槽保底版本

状态：正常操作受限版已在个人目录交付；完整物理修复与扩展验收继续，尚未覆盖生产目录。
外部根目录F为
`/cpfs/user/zhuzihou/dev/scientific-round2-repair-20261026/bath/repair_20261028/fixed_bath_fallback_20261030_v1`。

## 用户确认的范围

两任务都使用固定烧杯和透明视觉假浴水，试管与管内真实PBD样液保留。
保底交付优先，先前真浴水参数探索只保留证据，不继续追加扫描。
首轮要求8次完整正常成功、14个原坏例各一次、40个场景初始化、任务切换和
两任务独立原装接收。正常成功是两任务各三个布局一次，另各一布局独立重复一次。
原坏例保留实际得分，普通操作失败不要求变成SR1。30个原任务映射与10个库存
源场景分别计资格，库存场景不借用任务元数据。见F/control/user_scope_and_acceptance.json。

## 生产改动与来源

USD使用运动学刚体固定烧杯，保留其杯壁／杯底碰撞和原生刚体句柄；不逐帧
回写位姿。旧VisualWater几何与透明材质复用，明确关闭其碰撞。BathSystem与
BathParticles去激活，不删除共用父节点或Sample系统／材质。实际active遍历与
运行状态用于确认浴水PBD缺席，不把原始inactive定义仍存在混写成文件内完全删除。

反应图读取真实静态水几何profile，保留原有效反应日程、阶段、原生步计时去重、
颜色／银镜、观察与回架规则。新任务局部字段repair:bath_representation=static_visual，
repair:bath_valid初态false，只在实际几何／材质／profile检查通过后true，错误与
重置清false；legacy的pbd_valid保持false。metric只在显式新表示下读取新有效标记，
旧PBD模式行为保持原样，不控制物理或读取轨迹。

离线转换保留原layout、目标、动作、Sample及LMDB命令，仅移除浴水恢复数据并
保证固定状态不会被初始化覆盖。YAML和meta操作说明一致。6个正常示范使用已有
冻结数据；Silver5的真实hold360源为5522命令，继承draft字段5162已用独立出处
侧车说明，不能据该陈旧描述截短命令。全66份元数据和原文件SHA／逐键差异由
F/reports/data/conversion_manifest.json定位。

可移植资产根F/assets_portable_v1含40入口，474个文件、约1.25GB，无symlink，
依赖相对化且没有flatten或资产转码。40个组合等价、静态和目标4.1读取检查通过。
两项metric与新表示helper的7组专项测试通过；仓库make check为1255 passed、
1 skipped，日志在F/reports/data/make_check.log。仓库检查不是仿真验收。

## 运行与已知边界

本轮使用四卡主机10.150.164.127、Isaac4.1；GPU0/1负责正常示范，GPU2原坏例，
GPU3初始化。每卡单Kit、独立端口／cache／mesh_data，按真实NVML和退出记录判定，
不凭文档PID或外层完成标记续接。首接收副本因未接公共robot_usds而在0任务动作时
失败，已恢复基线只读资源wrapper，原失败日志保留，未修改公共机器人／核心。
外部坏例／初始化客户端的环境传递缺项也只修在助手工具，0动作失败不计任务得分。

水浴及银镜首样例均已取得原生1分／SR1和完整实际回架证据；后续全部验收仍在
进行。每次资格绑定实际原包、120Hz、完整启动到关闭日志、原生视频及实际Sample
源几何。正常Sample保留率至少95%，真实闭壁／外底逃逸与异常跳变阻止交付；
口出、有限内压入及回腔分别记录，不把任意实体压入等同于完整穿出。

烧杯和假水固定；浴水不提供真实流动、浮力或倒水能力。此版本不等于全真液体
问题已解决。旧T1、CCD失败和PBD32有限诊断的原报告及停止标记均保留。
自包含证据HTML、最终ZIP／SHA／回退与原装接收报告只在相应检查完成后封存。

规范依据ASSET-002/003、USD-001/002/008/009、MAT-001/003、STATE-001/002/003/005
及VAL-001..006/008。规范无需变更：这是用户明确要求的受限hybrid任务版本，
没有提出通用PBD参数、固定物体策略或核心包接口变更。运行交付只含任务YAML、
USD、task data及必要scientific metric；辅助工具／大型证据保持仓库外。
本轮不改GenManip核心、SDK、公共机器人、建通目录、飞书、LeRobot，也不push。

## 2026-10-30 07:22 UTC检查点

8次独立正常回放均已1分／SR1，两任务独立交付副本的原装入口也均已1分／SR1。
根复核分别记录在F/reports/normal8_root_review.json及validation/accepted_staged_task12.json、
accepted_staged_task18.json。原坏例当前3／14完成原问题、实际画面和全Sample源边界审查，
均保留0.85分／SR0，试管留杯不回架属于仍存在的操作失败。

同worker连续切换尚未验收。第二次尝试进入reset2时出现原Camera删除和SDK
ScriptNode.release错误，实际HOLD日志和资源退出保留在
F/reports/runtime_silver/hot_preflight/hot_attempt2_incident.json。追溯10月28日
integration/c1_final_queue_v1/reviews/cleanup_trace_cause_review.json，实际异常trace
已定位SDK在用户cleanup之前访问db=None；未据generic报错推断任务USD失效。
继续按已明确的平台诊断边界做热功能验收：仅三条精确已诊断消息可保留继续，
还须本轮只读异常trace印证；其他SDK／CUDA／任务错误、过期根访问、错帧仍停止。
不改SDK或核心、不为删除日志新增假Camera、不声称平台已修复。

四个实际overlook视频已内嵌成F/reports/fallback_evidence_preview.html，仅作NOT_READY
预览。桌面、平板、手机的离线浏览器检查已验证4视频可解码、播放和跳转，无页面
错误、网络请求或横向溢出；实际截图人工检查通过，记录在reports/html_browser_preview。
最终状态更新后还须重新核对最终HTML及清单。

## 07:46 UTC：快动作管内样液闭壁外穿

Silver mixed_4（bad9）前缀发生真实GlassShell闭壁外穿。root从实际世界粒子位置和
原生试管姿态独立重建粒子643的0..456轨迹，455→456穿过原网格三角12453，
此前最高局部z32.96mm、管口150mm、无口出记录。复核报告为
F/reports/runtime_silver/bad_prefix/bad9_root_particle643_counterexample.json，
全点前缀actual_outer_transitions另确认45个粒子ID。当前不能通过保液验收，
已在个人包KNOWN_ISSUES及NOT_READY明确说明，原包字节未改。

粒子643在454／455步的实际差分速度约1.83／2.00m/s，未直接达到3m/s限速；
对应材料点的刚性跟随速度约1.36／2.80m/s。因此“仅由3m/s限速造成”仍是
未证实解释，不能把提高maxVelocity当作既定修复。将另建独立前600命令探针，
只检查maxDepenetrationVelocity从1到3的单项变化，不修改冻结F或运行中工具。
管内实际physics:mass为6g，923粒，保留此前已允许工程标定；旧
repair:mass_per_particle的4g推导值不当作当前引擎总质量。

## 正常操作受限版交付

用户在看到bad9实证后明确选择“先交正常操作保底版，明确列出快动作漏液未解决；
继续单独修复”。因此本轮资格为normal8及两项独立原装安装；14坏例、40初始化、
完整同worker热切换仍分别记录进度和缺陷，不写成通过。穿壁仍是未解决问题，
不是被豁免成成功。bad9还保留任务自定义contact report无有效点错误。

交付目录H：
`/mnt/data/zhuzihou/GenManip-Sim/tmp/deliveries/task12-task18-fixed-bath-normal-operation-v1`。
同名外层ZIP为613,196,103字节，SHA256：
`fbbb3c6d36c5a92802ea730a19051721143bcde84a51ad85090aac770bef1505`。
36个外层文件内含634文件runtime payload；外层CRC、实际解压逐文件SHA均通过。
inner payload SHA为
`167b26305850c5e3be7b68439accd7ace29ace1bb98ad59ed8cdc64d3bf96fb4`。
包中README、RELEASE_SCOPE、KNOWN_ISSUES与physical_changes明确独立冷启动范围、
快动作漏液／接触错误、SDK热切换限制、offset前后不变项、安装与实际接收方备份回退。
无验证助手运行依赖，未更新建通、飞书、LeRobot或push。

H/fallback_evidence.html内嵌4个实际overlook视频，银镜失败卡使用本次bad9并明确
未解决状态；按钮跳到455步之前。最终离线桌面／平板／手机浏览器实际播放、seek、
问题按钮、无外部请求／页面错误／溢出均验证，root检查最终截图，
证据H/evidence/final_HTML_QA.json。最小metric补丁在隔离基线实际check／apply后
与payload4文件逐字节一致；不覆盖同事当前目录。

payload已做OSS完整读回及实际下载恢复634文件；外层正式包归档结果记录在
F/reports/archive_normal_handoff/verified.json（以文件实际存在和状态为准）。
后续纠正速度1→3的研究在R/sample_depen3_prefix600_probe_20261030_v1独立进行。
root重新逐prim比较其Stage，仅一项参数差；冻结F和H都不改，不继承新试验资格。
规范仍无通用变更，本轮只更新任务资格范围和可复核事实。
