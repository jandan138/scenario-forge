# EBench 既有场景初始位姿同步

日期：2026-09-12。适用 EBench scene-variants/GenManip Isaac Sim 4.1，普通既有对象，不含动态加载资产与 articulation parts。按 ASSET-001/002、USD-001/007、VAL-001/002/003/006 执行；源资产和历史任务不改写。

EEOS 冻结齿轮池的 i01 lead-in 在原生 reset-only 检查中，02/03 偏离计划位置约 37.51/210.14 mm。此前编译器仅改 initial_layout，USD 仍保留旧位姿。局部版本将四个对象的 USD 初始世界位姿与原 metadata 对齐后，同一 i01 冷启动的误差降至约 0.052/0.021 mm，装配关系恢复；04 的质量、COM/I 不变。此对照未执行任何模型，不证明唯一内部缓存原因。

新增可选 `initial_scene_pose_objects`。纯 Python 适配器为指定对象写入 world-frame TRS 覆盖和 resetXformStack；保留内部几何、物理属性及原始 task_data。拒绝外部动态资产路径、articulation part、非法 pose 或非正尺度。旧配置默认不启用，历史输出不重建。

新增 USD 组合回归先证明旧实现把父坐标 (9,8,7) 留在输出，修复后验证 metadata 世界位姿及子几何位置、源字节和物理属性保留。完整 make check：1012 passed、1 skipped，311.65 s；lint、package/phase10x smoke、diff check 通过。

修正版 40 个任务位于 outputs/ebench_gear_layout_aligned_v2_20260912，均已安装至原生任务目录，task_data 与各自 v1 完全相同，CPU 世界位置匹配。此前运行验证针对局部矩阵覆盖原型；正式编译器使用等价 TRS 覆盖，仍须对正式编译产物进行冷启动资格检查，不能把 CPU 结果推广成 40 个任务已运行通过。

同步设计接口与 USD-007 的 EBench 范围说明。未新增跨运行时通用稳定性保证。EEOS 证据目录：outputs/ebench_evolution/gear_layout_i01_{leadin_reset_20260912_r1,aligned_reset_20260912_v1}/；大型产物留外部目录，不提交源 USD/视频树。
