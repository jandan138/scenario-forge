# 水浴显色提前0.75秒与浴液作用隔离

状态：候选制作、静态验证和离线复算完成；5条完整回放与4条短诊断已启动。未通过运行/视觉验收，未交付。本轮没有新的全量76次重评。

## 已确认的产品决定

用户选择最终显色时限统一提前0.75秒，而非所有阶段缩短3%。开始时间保持不变，中间阶段按比例压缩，50%/95%评分门槛不改。原有效阶段t0..t4映射为t0+(ti-t0)*(t4-t0-0.75)/(t4-t0)；95%有效加热门槛因此提前0.7125秒。原始失败结果保留，不能按新规则改写历史得分。

物理路线先隔离浴液作用。此次不提高夹力/摩擦、不继续扩孔，不将诊断中的浴液关闭当作交付方案。

## 显色候选

个人repair根R为`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/task12_liquid_color_20261012`。候选身份R/evidence/completion_advance075_identity.json，运行副本completion_advance075_20261020T035746Z；来源为冻结contact_correlation2参考，不包含居中或扩孔。

自包含USD追加任务级timing_version=3与completion_advance_seconds=0.75；从原reference_timing_seconds及reaction_time_scale派生有效时间，不累减旧timing_seconds。版本2委托原读取函数，保持其原检查行为。更新全部41份初始化数据及41个场景文件（20个usd、21个usda，包含辅助入口），不修改metric或YAML物理参数。构建工具仅在个人tools内，运行所需函数全文嵌入USD，无接收方辅助依赖。

8项测试通过：端点/开始时间、严格顺序、原版本映射、幂等/原参考不变、非法时间拒绝、100组固定随机样本、运行读取/重置、重新随机化及旧读取委托（按8个测试方法统计）。静态逐Prim/属性/关系检查和初始化数据深比较确认只改计时字段及脚本，源文件哈希不变。源码、机器人、SDK、metric未改动。

离线用已有12条失败的有效加热记录复算，8条近阈值跨过95%、4条明显欠加热仍不过；证据completion_advance075_offline_check.json。不代表新回放必定重复相同物理过程，也未代替metric采样或完整任务验收。

四卡机10.150.164.127：GPU2运行来源9/12/15，GPU3运行11/0，共5条完整原动作。监督初始PID3323351/3323352，权威状态`/tmp/task12_four4090_20261019/completion075_gpu{2,3}/queue.json`。输入哈希检查、原生120Hz、逐来源chunk/底座语义及旧动作保持；普通失败保留并继续，基础设施异常停止。后处理初始PID3333231，在R/evidence/completion075_runtime_summary.json分别记录显色50/95、回架条件、运行时版本/提前量及待目视状态，不自动批准交付。

## 浴液隔离

GPU0固定A→B→B→A，各独立冷启动，mixed5原动作前1200步。A保留浴液参与，B仅在私有USD增加BathSystem.particleSystemEnabled=false覆盖；样液系统仍启用，固体碰撞、质量、夹爪设置、metric及原动作不变。未删除或停用整个Prim树，未改生产候选。因关闭浴液改变了环境，本实验只比较机械过程，不按颜色或任务分数决定修复成功。

四份身份为R/evidence/bath_isolation_{0_A,1_B,2_B,3_A}_identity.json。静态对照确认去除trace目标路径差异后A两份相同、B两份相同；A/B文本唯一差异为新增particleSystemEnabled=0，组合后的浴液/样液开关依次[true,true]/[false,true]/[false,true]/[true,true]。A从引用层继承true，因此初版静态检查预期两行替换不成立，改为核对真实单行覆盖和组合值；未放宽物理差异边界。

监督初始PID3318316，权威状态`/tmp/task12_four4090_20261019/bath_isolation/queue.json`。已看到A第一条的tube/bath/夹爪及25DOF记录，bath/sample运行时USD开关均true。B运行生效及配对结果尚待验证。

自动归档/分析初始PID3323353，状态R/evidence/bath_isolation_analysis/status.json。沿用已测试的精确关节+底座匹配及等价物体位姿组方法；不采用旧的一行对应一帧假设。核对记录中的浴液/样液开关，不将USD属性读回冒充直接粒子作用力测量。两次B与两次A的入杯运动变化须分别复核；即使B改善，也不据单次结果宣称浮力或唯一PBD参数根因。

## 待完成与维护

下一步是运行收尾、日志/动作/时钟审计、关键画面复核与ABBA运动对比；5条显色回放中回架失败仍保留。已有128条共同语义逐例复核也尚未全部完成，不混淆证据提取和审核通过。

交付范围仍限YAML、USD及依赖、task data、指定metric与延期的水浴LeRobot。此次改变任务内部时间版本，不改变Scenario Forge公共API/schema；辅助运行器未进入核心库。遵循STATE-001..004、MAT-003、VAL-001..005/008与维护流程。0.75秒是用户确认的任务标准调整，不是通用规则，规范无需变更。未运行核心make check；上述测试为外部任务工具验证。
