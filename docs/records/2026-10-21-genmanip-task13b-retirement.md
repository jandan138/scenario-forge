# GenManip Task13b 停用与清理

状态：已完成本地清理、普通 push 和远端回读。目标为建通仓库的 `feature/scientific_experiments`。

用户确认不再使用 Task13b，保留此前两个汇总提交，追加清理提交 `8f989c1a771139df700444c675ae69415d3927aa`，父提交为 `efe5d08aac82ea2c58561fb7616c9db942f200cc`。Author 和 Committer 均为 `zhuzihou <zhuzihou@pjlab.org.cn>`，未修改共享仓库默认身份，未强推。

## 清理范围

- Git 删除 `configs/tasks/scientific_experiments/task_13b_blue_bottle_reaction/` 下全部 56 个配置（50 YAML、6 JSON）。提交没有其他路径。
- 从建通活动目录移除 `saved/assets/scene_usds/scientific_experiments/task_13b_blue_bottle_reaction/`；先复制到个人备份并逐文件校验，再移除原目录。共 40 个普通文件、494,652,927 字节、21 个符号链接。资产不入 Git。
- 没有独立 Task13b task data 目录或专属 metric，因此没有对应删除。
- 原 Task13 的配置、metric、共享资产及 Task04 修复保留。历史交付包、评测结果、备份分支不清除。

## 验证与证据

操作根：`/cpfs/user/zhuzihou/dev/genmanip-task13b-retirement-20261021`。
`before.json`、`untracked_before.json`、`after.json` 保存哈希和工作区状态；`before.bundle` 保存原 Git 历史；`reference_audit.json` 保存引用检查；`push.json` 为脱敏推送回执。

核验了其余 1530 个受跟踪文件、已有未跟踪文件及原 Task13 资产哈希，均保持不变；提交后其他未提交状态与操作前相同。暂存差异严格为 56 项删除。922 个 USD 层的外部引用检查无 Task13b 引用、无读取错误；受跟踪代码及配置无目录外 Task13b 引用。已知远端运行主机未发现命令行含 Task13b 的进程（不是全环境占用证明）。两个活动 Task13b 目录已移除，远端分支回读为新提交。

## 恢复与其他克隆

备份 `archive/` 保留接收方相对目录结构；详细恢复步骤见操作根 `README.md`。需要恢复时先检查工作区，再 revert 清理提交，并将归档资产保留符号链接复制回原位置，核验哈希。

根目录的 `SubUSDs` 指向 `../task_13_blue_bottle_reaction/SubUSDs`，各场景的 `SubUSDs` 指向 `../SubUSDs`。归档保留原链接字符串，不复制或删除原 Task13 共享目标；独立备份中的相对链接可能暂不解析，恢复原布局后解析。不可跟随这些链接递归清理。

其他克隆 pull 后只会删除受跟踪配置，未跟踪的 `saved` 资产不会自动删除；如需停用其离线资产，应按同样边界单独归档。原两次汇总提交仍在历史中，参见[此前集成记录](2026-10-21-genmanip-two-commit-remote-integration.md)。

适用 VAL-002/003/005/006/007：本次只停用任务入口并归档独有资产，没有改变保留任务的物理或评分行为。验证采用删除范围、文件哈希、USD 引用及远端回读，不重复物理回放。规范、设计契约无需变更；操作说明在备份 README 中同步，历史包和既有验收资格不改写。
