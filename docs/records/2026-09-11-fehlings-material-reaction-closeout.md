# 斐林材质显色实验与 Git 收尾

## 范围与依赖

用户要求收尾已完成的斐林实验及 Git 改动。仓库基线为 `bb36b24`，
其中斐林源码已提交到 r2；本次将 r6 所需的 **r3→r5→r6** 依赖链一并纳入。

- r3：无碰撞假水、基于真实刚体位姿的样液区域接触判定、暂停／继续。
- r5：两块固定区域、仅材质显色，独立可重建的历史版本。
- r6：五层等高、错时多色显现、累计触水30秒完成、稳定观察3秒及重置。
- 同步各版本生成／验证／渲染／打包入口、行为测试、操作说明、设计与证据记录。
- 当前普通视觉反应任务头从已提交的 r2 更新到 r6；r3/r5 保留为构建来源。

CPU 碰撞 r4 是另一项工作树任务，不属于 r6 的来源链。它的生成器、测试、
专项规范和任务头继续留待该任务提交。共享 finalizer 暂存的是 r3/r5/r6 分派，
工作树中的 r4 分派原文保留。滴定 r1.7、粉末 r4 和研究套件的改动亦保留在各自工作树。
共享材质规范与任务头通过审查后的 Git 索引快照选择暂存，避免覆盖工作树。

## 冻结交付

完整证据见 [r6 记录](2026-09-11-fehlings-r6-five-layer-color-development.md)，
使用方式见 [操作指南](../operations/fehlings-r6-color-guide.md)。

- 输出根：`outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r6_20260911/`。
- 包目录：`handoff/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r6/`。
- canonical ZIP：相邻 `scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r6.zip`。
- ZIP 大小：122081459 bytes。
- ZIP SHA256：`76cf3bf55c4659c98407c73fa2607f141900fe0d471d054cbadeda24c181c3f5`。
- 场景 SHA256：`2835c2b541c5f2db5008653345f4ace86d3780c82beac664d4aff0e7c30de3d4`。

本次 Git 收尾只整理源码、文档和提交闭包，冻结的场景、ZIP 和运行证据身份保持不变。
既有三次 Isaac Sim 4.5.0 冷启动、每次28项检查与36个快照、20张回放图沿用同一最终场景证据。
本地目视结论为 WARN／可用：多阶段颜色和高度差异可辨，玻璃仍使管尖偏暗；
不宣称独立目视审查、真实化学、颗粒流动、机器人成功或4.1运行资格。

## 保留与规范同步

适用 VAL-003/005/006 和规范维护流程。本次无需修改通用规则；保留先前已验证的
MAT-005 分区渲染证据增量，另补本 Git 收尾记录。

| 分类 | 本次处理 |
|---|---|
| KEEP_HEAD | r6 完整输出目录、handoff、ZIP 与校验文件 |
| KEEP_SOURCE | r5、r3 来源包及其依赖；原始参考视频 |
| ARCHIVE_DIAGNOSTIC | 原位保留各版本运行与分析中间产物，用于追溯 |

USD、ZIP、截图、视频和大型运行输出按既有政策留在 Git 外；本次不做产物清理或外部发布。

## 验证

实现阶段完整工作树 `make check` 已通过：1003 passed、1 skipped，Ruff、
package-smoke、phase10x-smoke 和 diff-check 通过；日志位于 r6 输出根 `make_check.log`。
交付重定位、70项本地依赖闭包、441个来源依赖文件、1702个非液体世界变换、
物理配置、ZIP CRC 和 SHA 的检查结果见同目录 `delivery_verification.json`。

### 暂存区独立源码验证

暂存32个文件。通过 `git checkout-index` 将完整暂存源码导出到
`/tmp/opencode/fehlings-closeout-stage/`，只接入现有 `outputs` 和
`external_artifacts/incoming` 数据目录。确认 `scenario_forge` 与 r6 生成器的实际
Python 导入路径都在该独立源码目录内，没有导入工作树中的其他未提交源码。

在独立目录执行：

```bash
make test lint package-smoke phase10x-smoke SMOKE_OUT=/tmp/opencode/fehlings-closeout-smoke SMOKE_SUITE_OUT=/tmp/opencode/fehlings-closeout-suite PHASE10X_SUITE_OUT=/tmp/opencode/fehlings-closeout-phase10x
```

结果：**995 passed、1 skipped**（291.82秒）；Ruff、package-smoke 和 phase10x-smoke
全部通过。主仓库另执行 `git diff --cached --check`。与完整工作树1003项通过的
数量差异来自本次未纳入的其他任务测试，不是斐林测试被跳过。

首次只接入 outputs 时有6个历史 task02/task08 测试因缺少 incoming 原始资产失败；
补接已有数据目录后完整重跑通过。这个结果依赖本地资产，不解释为无数据 CI 通过。

暂存区文档本地链接、脚本内部导入、生成产物排除和字面量凭据模式检查通过。
收尾再次核对 r6 ZIP CRC、SHA、重定位和最终场景身份通过，内容哈希与冻结值一致。
最终只追加本收尾说明与验证日志，没有改动场景或运行实现。

日志与索引审查摘要保留在 r6 输出根：
`git_closeout_index_check.log`、`git_closeout_index_audit.json`。
本次提交编号以本记录所在的 Git 提交为准。
