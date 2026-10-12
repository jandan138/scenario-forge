# task12 均匀变色真液体：验证与恢复

工作根R：`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/task12_liquid_color_20261012`。
决定及资格边界见[日期记录](../records/2026-10-12-task12-uniform-liquid-repair.md)。本页不为Scenario Forge添加runner或SDK核心层。

## 恢复入口

先读R/CURRENT_STATUS.json、evidence/first_native.json及对应baseline_runs/receipt.json，再检查远程GPU与8087占用。
称量600条在另一台机器上运行，勿停止或重复启动其producer。水浴只使用10.150.162.223的单4090。
独立运行工具在R/tools；接收方只依赖允许的YAML、USD、task data与scientific metric。

## 验证与停止

- 当前首例mixed5按完整7000步验证；其原始动作来自bad_case_matrix中第8项，不混用teleop或其他策略轨迹。
- tools/run_first_native.py记录自己的helper、server/client与run ID，首个物理/加热运行时错误即停止；只清理本次进程，禁止全局pkill或ray stop。
- 原生结果、启动及worker日志、周期120Hz时钟、状态、四视频都要核对。已有静态结构及八项规则检查不能替代完整运行。
- 首例通过后才运行其余四个task12坏例；银镜的失败和局部资格不自动归给水浴。
- 规定无机器人演示需要明确夹持约束，只能支持相应液体/规则范围；完整反应演示不改变正式评测7000步上限。

首个mixed5原生尝试已在6495条有效观察后出现CUDA错误。`first_native_failure_audit.json`为实际失败证据；流式客户端视频可以用于故障前画面，不能替代不存在的完整服务器结果。
重置材质修正和浴液投影修正已写入20个场景入口；原静态报告的旧wrapper哈希须在最终验收前刷新。
当前真实反应视频见`normal_visible_process.json`；`shadow_diagnosis_process.json`等是强制颜色/暂停物理的诊断，不能当作反应视频。

默认凸分解候选因内腔偏差未通过，不得安装。第二个shrinkWrap诊断由`tools/run_shrinkwrap_qualification.py`调度，先等真实反应与源SDF测量，再核对内腔及冷态/升降夹具；任一失败停止，完整原生资格仍单独建立。

## 安装兼容与交付

metric共享repair_checks与已交滴定、称量相同。未安装共享文件的接收环境使用task12_metrics_standalone.patch；已有且哈希一致时使用task12_metrics_existing_shared.patch，只修改task12 metric。哈希不一致时先处理版本差异，不盲覆盖。
两种补丁及只读检查在R/evidence，正式交付时复制到独立发布目录。
最终包须含20场景入口、离线相对路径、补丁、安装说明、哈希及实际证据；无GenManip核心、SDK、机器人或生产脚本安装需求。
缺成功机器人示范/LeRobot如实标为待重采；引擎错误不可作为正常坏例放行。
