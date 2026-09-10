# 粉末＋天平实验与 Git 收尾

## 收尾范围

用户确认一起收尾粉末实验依赖的受力天平基础实现和场景制作规范库。
按依赖顺序提交规范库基础版、受力天平基础、粉末增量；ConvertAsset 的粉末生产者实现独立提交。
共享文件通过审查后的索引快照分段暂存，保留工作区原文。
滴定 r1.7、斐林 r3 及论文相关的独立改动继续留在各自工作区；大型视频、USD、NPZ 和 Blender 源按产物政策在 Git 外保留。

## 已完成实验与冻结交付

完整实验、参数、已知载荷误差、三 seed 结果和图像审查见
[粉末 r1 记录](2026-09-09-rigid-powder-force-weighing-r1.md)，运行方式见
[操作指南](../operations/powder-weighing-r1-guide.md)。

- 交付根：`outputs/powder_weighing_r1_20260909/handoff/powder_weighing_r1/`。
- canonical ZIP：同目录的 `powder_weighing_r1.zip`，130071472 bytes。
- ZIP SHA256：`acdd7cecf51afe72b758b06682cb2368a0e5caaf57e7bdb423ea0ee19c0d412a`。
- 场景 SHA256：`fcb2db7e269f9aa946a880c50352e65f8baa968a736841a8d98ab76d93778d13`。
- 当前头：`solid_sample_weighing / isaac45_rigid_powder_force_demo / r1`。

本次收尾是来源、验证和版本整理；运行资产及其已验证的场景字节保持冻结。
数值与视觉证据沿用内容身份一致的既有运行，不重新声称执行了 GPU 仿真或机器人操作。
已验证范围为 Isaac 4.5、规定运动学工具轨迹、4096 颗粒和真实秤盘接触测力；实时性能、毫克级准确度、VR/Lift2 抓持及 4.1 粉末组合仍未覆盖。

## 保留分类

| 分类 | 位置与处理 |
|---|---|
| KEEP_HEAD | SF 完整实验目录、handoff 目录及 canonical ZIP |
| KEEP_SOURCE | 原始 incoming ZIP；ConvertAsset 的来源快照、最终 `balance_fixture_r6`、seed 43/44 夹具及 Blender 源 |
| ARCHIVE_DIAGNOSTIC | 同一实验目录中的接口失败、尺度调参、测力漏项及中间渲染证据，就地保留用于追溯 |

## Git 依赖闭包

规范库初始提交采用已提交滴定 r1.6／斐林 r2 的依据；其后的 r1.7／r3 专项规范增量和任务头更新留待相应任务提交。
受力天平提交包含纯测量状态、runtime bridge、生成／验证／交付工具、测试及关联文档。
粉末提交包含接触测力变体、规定轨迹、验证／回放／打包入口、三项行为测试和场景规范增量。
每批审查暂存区的路径、引用和内容；最终用索引导出的独立源码树验证，避免未提交工作区掩盖依赖缺失。

| 前置内容 | 仓库与提交 |
|---|---|
| 场景制作规范库基础版 | Scenario Forge `2a61514` |
| 受力天平基础实现 | Scenario Forge `a81082f` |
| 粉末生产者与 Blender 工具源生成入口 | ConvertAsset `3240ca3`（天平原生产者基线为 `8d7e2da`） |
| 粉末集成与本收尾记录 | 本记录所在的 Scenario Forge 提交 |

已完成检查：交付 132 个文件哈希与 USD 闭包再次通过，ZIP SHA256 与冻结值一致；
规范库的索引独立源码快照中 9 项测试通过，受力天平独立快照中 15 项测试及定向 Ruff 通过，
ConvertAsset 粉末测试 2 项通过。暂存区本地文档链接、脚本 import、生成文件排除与字面量凭据检查通过。

## 最终验证（2026-09-10）

1. 工作区运行：
   `make check SMOKE_OUT=/tmp/opencode/powder-closeout-smoke-package SMOKE_SUITE_OUT=/tmp/opencode/powder-closeout-smoke-suite PHASE10X_SUITE_OUT=/tmp/opencode/powder-closeout-phase10x`。
   **976 passed、1 skipped**；Ruff、包/suite smoke、Phase 10.x 与 diff-check 通过。
   日志：`/tmp/opencode/powder-closeout-check.log`。
2. 索引源码导出到 `/tmp/opencode/powder-final-stage`，只接入原有 `outputs` 产物目录，未接入工作区其他源码。
   运行 `make test-ci lint package-smoke phase10x-smoke`，三个输出参数分别为
   `/tmp/opencode/powder-stage-smoke-package`、`/tmp/opencode/powder-stage-smoke-suite`、`/tmp/opencode/powder-stage-phase10x`。
   **928 passed、1 skipped、38 deselected**；Ruff 和全部上述 smoke 通过。
   暂存区另执行 `git diff --cached --check`，日志：`/tmp/opencode/powder-stage-data-check.log`。
3. 最初未接入产物目录的独立源码试跑有 13 failed、4 errors，均因既有滴定/斐林测试读取缺失的 `outputs`；
   它们尚未完整标记 `local_artifacts`。这是已记录的无本地数据 CI 限制，不将接入数据后的通过解释为无数据 CI 通过。
4. 本轮没有改变仿真/渲染实现与交付字节，原三 seed、机身落粉回归、已知载荷、视频与视觉证据仍绑定同一冻结包。
