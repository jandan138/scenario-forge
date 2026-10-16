# 水浴120Hz候选：完整诊断通过，进入接收包重复验收

日期：2026-10-16。状态：RC1静态通过，尚不可宣称完成交付。

来源13 `unseen_prospect_10` 的位置迭代上限32诊断在120Hz、7000步上限下自然结束：score=1、success_rate=1、3782步。3783个原生观察与只读记录精确对齐（误差0）；正式episode样液和浴水最低保留率均100%，无退出事件，浴水粒子深入试管计数0，终态显色进度1、试管倾角约1.039度。四路视频完整解码通过，当前版本的显色/回架目视复查仍待完成。

这些结果只覆盖一次诊断运行。初始化阶段曾出现99.1333%的最低计数及待复核事件，不能把正式episode的100%推广到初始化/重置。原动作未修改；场景迭代上限32尚未成为通用推荐。

外部根目录：`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/task12_liquid_color_20261012`。完整运行与分析为 `evidence/sample_maxpos32_full_h13_a_run.json`、`sample_maxpos32_full_h13_a_analysis_pose.json`、`sample_maxpos32_full_h13_a_readback.json`。运行ID为 `task12_sample_maxpos32_full_h13_a_20261016T021953_051350Z`。此前max16满分但侧壁退出的证据保持原样，不能与本轮混用。

## RC1已完成内容

接收候选由 `evidence/receiver_maxpos32_rc1_identity.json` 唯一定位，目录为 `receiver_maxpos32_rc1_20261016T033644Z`，GenManip基线提交 `9c7461326b46db7a1db7ef22ca0146d4e13a3433`。

- 20个场景、41份初始化metadata、51个YAML的102组配置统一120Hz及场景位置迭代上限32。
- 样液923粒、4mL/4g、名义高度0.023563688618146943m；浴水2320粒。各布局按原容器位姿生成粒子初态，82个非metadata任务文件保持原字节。
- 各背景与原始布局保留；恢复已验证的试管、管架、烧杯碰撞组合。未加入未经验证的桌面2mm修改。
- 20个场景集成ON文字网格，复用ConvertAsset已有制作函数；物理属性不受文字修改影响。实际渲染尚待验证。
- 删除私有ValidationObserver；metric文件保持原样，仅负责评分。USD与贴图依赖闭包静态无缺失，MDL运行时编译待验。

静态报告：`evidence/receiver_maxpos32_rc1_static_audit.json`，状态 `PASS_STATIC_RECEIVER_CANDIDATE`。该状态不代表原生任务、重置或视觉合格。

## 验证安排与资源

先做无观察器原生对照，再做来源0/13/15各两次冷启动及独立安装验收；满足后可给同事第一轮评估包。正式资格仍需19个不同来源记录各两次，共38次，重名case不合并。矩阵 `evidence/receiver_maxpos32_rc1_qualification_matrix.json` 将新候选全部初始化为NOT_RUN，不继承历史诊断的成功计数。其余16条来源仍须先校准原包执行协议。

2026-10-16 04:16 UTC左右，GPU由称量独立队列占用；水浴原生RC1没有启动。私有等待器PID3912873已核实存活，`receiver_maxpos32_rc1_gpu_wait.json`记录资源状态。它等待称量整个队列成功收尾且GPU/8087持续空闲30秒后才启动水浴，不抢占任务间隙、不停止称量；等待上限3小时。等待器存活不等于水浴回放正在运行，启动与结果必须查对应run记录。

私有重复验收使用独立工作树中的USD观察层，引用冻结的RC1，交付内容不包含该层。静态准备发现顶层metersPerUnit/upAxis等元数据不会由子层按预期带入；现显式复制顶层元数据并核对单位、上轴及prim集合，错误在运行前被拦截。另一个构建问题是已有引用prim不能仅靠OverridePrim取得可复制属性的本地spec，现用Sdf.CreatePrimInLayer创建spec后复制ON网格；失败临时目录保留，不选作候选。

仍以120Hz为首选；180Hz仅为已获授权的后备，需要等时长动作映射、增量底座语义、计时和步数预算一起验证。目前未切换180Hz。

交付仅任务YAML、USD及依赖、task data、指定scientific metric。水浴LeRobot本轮延期；称量任务独立继续。独立工具只在个人修复目录使用，不增加接收方依赖、不修改GenManip核心或SDK。

规范依据：MAT-001/003、STATE-001/002、VAL-001/002/003/004/008及维护流程。规范无需变更：当前只是任务特定候选和未完成的重复验收，没有新的通用物理默认；核心包/API契约不变。操作说明同步本记录，历史包不回写。
