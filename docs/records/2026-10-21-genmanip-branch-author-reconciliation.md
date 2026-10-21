# 建通接收仓库原分支与朱子厚署名整理

状态：本地完成，未推送远端。用户批准保留历史交付提交，以新提交纠正署名，并恢复 `feature/scientific_experiments`。

接收目录 `/mnt/data/chenjiantong/GenManip-Sim` 从 `delivery/task12-real-liquid-r1`（9490df9a）恢复到 `feature/scientific_experiments`，其原端点 f52f73b3 快进至 `5bd481291dab9c6ab65936a7ea0cd3310bb9ac53`。三个新提交的 Author 与 Committer 均为 `zhuzihou <zhuzihou@pjlab.org.cn>`：

| 历史提交 | 新提交 | 内容 |
|---|---|---|
| 2deb80df | b7070a83 | 称量有效4–5g显示评分及可选稳定要求 |
| ed79c073 | 9cc55650 | 保存评分时的称量显示快照 |
| 9490df9a | 5bd48129 | 菲林液体有效性与几何回架判断 |

新提交只修改 scientific metric 目录；该目录全部受追踪文件与整理前安装版逐字节一致。原83334847、82cabca5两项制作端渲染修改没有纳入原分支，仍在历史分支及个人制作工作区中保留。接收工作区的对应渲染代码恢复到原分支基线，不重写历史提交。

## 验证与备份

材料根 `/cpfs/user/zhuzihou/dev/genmanip-branch-reconcile-20261021` 包含：

- `before.json`、`after.json`：分支、HEAD、受追踪文件、未提交修改及运行文件哈希。
- `before.bundle`、`backup_files`、两个patch：原分支历史及工作区修改备份。
- `prepared.json`、`metrics_reconciled.bundle`、`validation.json`、`installation.json`：提交映射、新提交材料、检查与安装回执。

1740个任务运行文件（称量、滴定、菲林、银镜，排除可再生缓存）哈希不变；原有未提交修改和未跟踪文件完整保留。共享接收仓库的原user.name/user.email不改，避免将建通本人后续操作署成朱子厚。个人GenManip、Scenario Forge、本次候选及当前银镜B独立仓库设置朱子厚身份；未修改全局配置或共享Git目录的linked worktree配置。

检查：称量6项、菲林规则7项、实际菲林metric方法12项通过；修改文件编译检查和新提交双身份检查通过。实际metric测试采用内存USD位姿，非新机器人回放资格。当前Task18冻结副本和队列不变，切换后远端仍正常步进/收尾。已有发布ZIP、bundle、MANIFEST和READY保持原样。

## 后续交付规则

建通目录保持 `feature/scientific_experiments`。新修复在独立工作区制作，代码接收仅纳入允许的metric修改，显式设置朱子厚的Author/Committer；离线YAML/USD/task data依清单安装。旧版“切到delivery分支”的安装脚本不再作为现行安装方式。已有银镜候选的旧base/commit映射须在正式交付时重新整理，不能直接执行旧安装脚本。

本记录按VAL-003/005/006/008及维护流程保存新旧证据边界。规范无需变更：这是接收分支、身份和交付操作整理，不改变通用场景规则、任务行为或Scenario Forge公共API。完整make check已在本日此前变更中通过；本次为外部Git整理及文档追加，执行针对性25项检查和文档diff检查，不重复物理实验。
