# 水浴：首次完整满分，但仍有侧壁穿出

日期：2026-10-16。状态：不可交付，目标继续进行。

采用原动作、120Hz、7000步上限的来源13代表案例，得到原生score=1.0、success_rate=1，3762步自然结束。3763个观察精确对齐，原动作一致，四路视频完整解码通过。正式episode样液最低保留率99.67497%，终态试管倾角0.329度。正常顶部机位能辨认蓝/青、绿、黄、橙显色阶段。

关键改动是把场景位置迭代上限从255降为16；粒子仍923颗、名义样液4mL/4g。提高迭代下限到128没有解决问题，而是让较大的管内粒子运动提前出现。完整成功证明旧动作在当前候选上有可行路径，不是全包交付资格。

| 要求 | 本轮证据与缺口 |
| --- | --- |
| 完整任务与回架 | 单条来源首次1分；尚未冷启动重复或覆盖其他来源 |
| 全程保液至少95% | 正式episode最低99.67497%，通过数值门槛 |
| 无穿壁 | **未通过**：frame180粒子305、frame3465粒子652侧壁退出，后续快照确认越过外壁 |
| 变色可见 | 正常机位抽样可见完整阶段；非独立审查，非逐帧认证 |
| 显示一致 | 热板仍显示OFF，待修正 |
| 最终交付 | 未冻结最终包，未完成19来源×2冷启动及独立安装；水浴LeRobot本轮不做 |

下一完整回放只将样液maxDepenetrationVelocity从1改为2m/s，总maxVelocity仍3，保留位置迭代上限16。两次侧壁退出时容器角点逐步运动速度约1.071/1.430m/s，因此用该单变量对照检验碰撞纠正速度是否不足；它还不是因果结论。新运行监督进程2530841，实际状态以外部运行记录和进程为准。

交付边界保持：同事只接收任务YAML、USD及依赖、task data、指定scientific metric；不改GenManip核心/SDK/机器人源文件，辅助脚本及只读观察器不是接收方依赖，metric只评分。不改变原动作或放宽成功条件。

实际视频：[顶部变色录像](/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/task12_liquid_color_20261012/diagnostic_sample_maxpos16_full_20261016T012905Z/saved/eval_results/scientific_experiments/task12_sample_maxpos16_full_h13_a_20261016T013031_155684Z/scientific_experiments/task_12_fehling_test/unseen_prospect_10/000/top_camera.mp4)、[俯视回架录像](/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/task12_liquid_color_20261012/diagnostic_sample_maxpos16_full_20261016T012905Z/saved/eval_results/scientific_experiments/task12_sample_maxpos16_full_h13_a_20261016T013031_155684Z/scientific_experiments/task_12_fehling_test/unseen_prospect_10/000/overlook_camera.mp4)。

外部证据根：`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/task12_liquid_color_20261012/evidence`。本轮身份/运行/逐帧分析分别为`sample_maxpos16_full_identity.json`、`sample_maxpos16_full_h13_a_run.json`、`sample_maxpos16_full_h13_a_analysis_pose.json`；退出事件`sample_maxpos16_full_episode_exits.json`；视觉范围`maxpos16_full_visual_review.json`；下一候选`sample_maxpos16_depen2_full_identity.json`。完整过程见[原生诊断记录](2026-10-16-task12-native-return-failure-and-observer.md)。

规范依据：MAT-001/003、STATE-001/002、VAL-001/002/003/004/008及维护流程。此单来源结果仍有明确物理缺陷，未建立通用solver默认规则，不修改规范或包/API设计契约；操作说明已同步。
