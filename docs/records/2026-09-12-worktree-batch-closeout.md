# 工作树全部改动的规范化与分批 Git 收尾

## 范围与批次

用户在斐林 r6 提交 `2df3c4c` 后要求规范处理本仓库全部剩余修改并分批提交。
按任务归属审查源码、配置、标准增量、记录和产物；共享任务头使用索引快照分批暂存，
保留各批未提交的工作树原文。最终每批源码均可从 Git 索引独立导出并验证。

| 批次 | 提交 | 内容 |
|---|---|---|
| 滴定 r1.7 | `47ab4cd` | 生产者滴嘴视觉接入、五对象参考位姿、验证／回放／打包、MAT-003 与任务头 |
| 斐林 CPU r4 | `6ced811` | CPU 碰撞候选、无 PhysX 插件时的原始 schema 清理、测试、规范与修正候选头 |
| 粉末 r4 | `f11e3c6` | 近满瓶预沉降初态检查、证据约束、回放／包装、指南与任务头 |
| EBench 研究原型 | `3245e33` | 四条件编译／本地安装、惯性匹配和指令干预配置、类型标注、异常路径回归及契约 |
| EBench 互补惯性配置 | `3a21451` | 收尾期间新增的 control 几何／wide 惯性诊断配置、说明与索引 |
| 总收尾 | `045d3ea` | 既有规范 ZIP 归置、完整验证和 Git 状态记录 |
| 互补惯性结果补录 | `a6cd756` | 1000步固定窗口回放结果及 EEOS 出处 |
| COM／惯性分项截止快照 | 本补充提交 | 两份配置、对应记录与索引；用户指定的本轮截止范围 |

生产者资产由 ConvertAsset 管理。本次提交的是 Scenario Forge 的消费者／适配器实现；
已交付包保留对应来源资产、receipt 或 source_scripts 快照。没有将外部流水线搬入核心包层。

## 各批审核与验证

每批在 `/tmp/opencode/batch-closeout-<batch>-stage/` 导出当前完整 Git 索引，
只接入 `outputs`、`external_artifacts/incoming` 数据目录。源码依赖与本地文档链接
均从暂存内容检查，不依赖其他未提交源码；提交前核对测试索引树与实际提交树一致。

| 批次 | 独立源码检查 |
|---|---|
| titration | r1.7/r1.6/r1.5 与当前任务头：21 passed；定向 Ruff 通过 |
| cpu | r4/r3/r5/r6 与当前任务头：24 passed；定向 Ruff 通过 |
| powder | 满瓶／紧凑瓶协议、证据、回放与当前任务头：13 passed；定向 Ruff 通过 |
| research | adapter 与架构边界：5 passed；定向 Ruff 和模块严格类型检查通过 |

新发现的行为缺口均先写失败回归，再作最小修复：

1. **r4 原始 schema 残留。** 普通 usd-core 的有效 API 列表忽略未注册 PhysX schema，
   原候选文件仍有 SDF 元数据。改为按 token 移除；额外检查原始 `apiSchemas`。
   修正候选另存、保留旧候选和原 DemoGen 记录。新候选仅获静态验证。
2. **研究编译失败留下半成品。** 非法 USD 资产路径的检查移至输出目录创建前。
3. **研究安装漏核对源入口。** 安装前补查源 `.usda` wrapper 的记录哈希，变更即拒绝。

研究三份实际配置在临时目录重新编译、USD加载与临时注册，共12个入口通过，
每个入口包含2886个 prim及预期勺子节点。实际 GenManip 注册与模型任务没有被本次验证重跑。
研究状态仍为 `compiled_not_runtime_verified`，不解释为可移植闭包或运行成功。
最终核对期间又出现一份互补惯性配置，按用户“全部修改”要求追加独立批次：
四个新入口的实际编译、USD加载和临时注册通过，配置哈希与暂存内容一致。
详见 [互补惯性收尾复核](2026-09-12-ebench-reverse-inertia.md)。

模块类型检查使用临时 mypy 2.3.1 工具环境：
`mypy --follow-imports=skip src/scenario_forge/adapters/ebench/intervention_suite.py`。
默认项目 Python 原先未安装 mypy；工具安装在临时缓存中，没有修改项目依赖。
跟随全部导入的尝试暴露了既有核心／adapter 的类型错误；这里的严格定向通过不是全库 mypy 通过。

## 交付内容复核

| 产物 | 本次结果 |
|---|---|
| 滴定 r1.7 | 冻结场景、运行报告、ZIP CRC/SHA 和异目录19项依赖闭包通过；ZIP 31,604,694 bytes |
| 粉末 r4 | 冻结场景、205个文件哈希、ZIP CRC/SHA、异目录24项依赖闭包通过；补齐旁路 `.zip.sha256` |
| 斐林 CPU r4 修正候选 | authored schema、世界平移、70项依赖闭包、异目录解压和 ZIP CRC/SHA 通过；`runtime_pending` |

对应身份与边界见
[滴定记录](2026-09-08-titration-r17-open-tip-reference-poses.md)、
[粉末记录](2026-09-11-task09-powder-bottle-r4.md)、
[CPU候选记录](2026-09-11-fehlings-r4-cpu-contact-colliders.md)。
既有 r6 交付、原视频／渲染证据和其他历史包继续保留；本次静态复核不冒充新仿真或新目视审核。

## 规范快照与保留

根目录原有 `docs-standards.zip` 是已生成的历史文档快照，不是当前规范的权威来源。
按照 VAL-005/006 将其原字节移至：

`outputs/documentation_snapshots/20260911/root_docs_standards_snapshot/docs-standards.zip`

- 分类：`ARCHIVE_DIAGNOSTIC`，就地保留，未上传或删除。
- 24,074 bytes，8份 Markdown 文档，ZIP CRC 通过。
- SHA256：`c02ae25bc3bd3f14e495ce504f0d67c3c7194bad1a21783e4de1bd7d60bf13b4`。
- 相邻 `manifest.json`、`.zip.sha256` 记录原位置、文件清单与内容身份。
- 当前规范仍以 Git 中 `docs/standards/` 为准，没有用旧 ZIP 覆盖新规范。

无需新的通用保留规则；本次按现有维护流程与 VAL-005/006 执行。大型 USD、ZIP、视频
及运行数组均未纳入提交；各批只提交源码、配置、说明与小型证据摘要。

## 最终全量检查

执行：

```bash
make check SMOKE_OUT=/tmp/opencode/all-batches-smoke SMOKE_SUITE_OUT=/tmp/opencode/all-batches-suite PHASE10X_SUITE_OUT=/tmp/opencode/all-batches-phase10x
```

**1006 passed、1 skipped**（299.07秒），Ruff、package-smoke、phase10x-smoke 和
`git diff --check` 全部通过。其后新增的互补惯性配置已做上面的专项加载／安装验证，
没有再改运行源码或既有交付场景；最后追加本收尾结果与文档索引。

证据目录：`outputs/worktree_closeout_20260911/`，含 `make_check.log`、各批索引审查、
交付复核、研究配置编译核对与规范 ZIP 身份。本记录与文档索引作为最后一批提交。
分批测试和全量测试均使用已有本地资产，不宣称无资产环境的所有集成测试通过。

## 用户指定的截止快照

其他会话在收尾期间持续新增研究任务。用户明确选择“以当前快照为截止”：
处理当时已出现的 COM／惯性分项配置与记录，之后新增或更新的内容留给下一轮。
本轮追加固定以下文件的索引快照：

- `configs/research/ebench_dish_component_com.json`
- `configs/research/ebench_dish_component_tensor.json`
- `docs/records/2026-09-12-ebench-inertia-components.md`
- 文档索引中指向上述记录的条目。

快照导出为 `/tmp/opencode/batch-closeout-inertia-components-cutoff-stage/`。
确认实际导入的编译器来自该快照，而不是后来改动的工作树；两份配置的8个入口均通过
真实 USD 加载和临时运行目录注册，每个入口2886个 prim。配置 SHA256 分别为
`0be72d8ab98803fe715114284db154b81af2b788a0bd280365fe58787a63f06c`、
`b78a13a76f8135cf68d003eba753820a3e749a36cc8a43a9f0a330883d7af5d9`。
日志为证据目录下 `inertia_components_cutoff_check.log`。

后续成对布局变体、齿轮相关记录及 native adapter 的继续修改未纳入该截止快照，
保留工作树供下一轮处理。因此本轮完成含义是“截止快照已提交”，不是宣称并行会话持续写入的工作树永久干净。
