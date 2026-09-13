# 斐林 r7 与玻璃试管生产者 Git 收尾

## 范围

用户在 r7 制作与交付后明确要求“收尾＋Git 收尾”。本轮按依赖顺序提交：

1. ConvertAsset：18×150 mm Blender 玻璃试管模型、USD／材质／物理封装、资格晋级、测试与生产者记录。
2. Scenario Forge：r7 集成、8 mL 五层、架子与水浴验证、渲染／打包入口、操作及规范证据。

两个仓库的共享文档索引按 r7 条目选择暂存，保留其他工作树内容；实验产物仍按 VAL-005/006 留在 Git 外。
本轮没有改变冻结场景、模型、MDL、图片或运行报告。其他论文及研究任务的改动不属于 r7 收尾范围。

## 冻结内容

完整实现与验证见 [r7 实验记录](2026-09-12-fehlings-r7-glass-test-tube.md)。

- 场景 SHA256：`71e38a115fc2b1e5fa8294224d16a3cc17474bc6015196e319c7d431ed460098`。
- 生产者资产 SHA256：`4f7129da98db6d3307bb924834e97f001f6d7ce9e3fba95273bb95d6788cd757`。
- Blender 源 SHA256：`96ed8e1a6c627317fe9a6afd7d78f84c3a024cf86fdfc6881eb3cfdc64ca3547`。
- ZIP：138214173 bytes，SHA256 `f8340b4c61aeda7efabc161fb4ee926bea6c49631091664cc7b72c4acc405fcd`。
- 当前头：`fehlings_reducing_sugar_water_bath / vr_open_tube_positive_visual_reaction / r7`。
- 输出根：`outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r7_20260912/`。

既有三次 Isaac Sim 4.5.0 独立冷启动，每次35项检查及38个快照，29张最终图像沿用相同内容身份。
原架 scale1 的落座／拔出／再插入通过。范围是规定动作及任务视觉，非实物耐热、机器人抓取或CPU/4.1资格。

## 测试夹具收尾

晋级完成后复跑生产者测试，发现两处测试仍假定 live 包尚未晋级。先复现失败，再仅修正测试：
实际包检查覆盖待验证／已晋级两种合法阶段，晋级测试从新建的临时静态包开始。
保留不同既有资格必须拒绝的生产行为，不为让测试通过而重置 live 资格元数据。
修正后46项生产者及晋级测试通过，实际报告读检也运行，目标 Ruff 通过。

## 提交闭包与验证

每个仓库以 Git 索引导出独立源码树，只接入已存在的必要产物／输入数据。
检查新脚本内部依赖、文档相对链接、生成产物排除以及最终提交树与测试索引树的一致性。

### ConvertAsset 生产者批次

提交：`994dd6c`，`feat: qualify Blender glass test tube for Fehling r7`。
包含8个文件：三份实现脚本、两份测试、一份生产者记录和两处导航条目。
工作树中其他导航条目及论文／研究改动未混入该提交。

从暂存区导出 `/tmp/opencode/fehlings-r7-producer-index/`，只接入原有 `outputs` 数据。
在该独立目录执行生产者与晋级测试，并通过 `CHEMISTRY_TUBE_R7_REPORT_DIR` 指向 r7 实际报告：
**46 passed、无 skips**（11.77秒），目标 Ruff 通过。
日志在 r7 输出根 `git_closeout_producer_tests.log` 与 `git_closeout_producer_lint.log`。
提交树与已验证的索引树一致。

### Scenario Forge 消费者批次

从暂存区导出 `/tmp/opencode/fehlings-r7-consumer-index/`，只接入已有 `outputs` 和
`external_artifacts/incoming` 数据目录；确认 `scenario_forge` 与 r7 生成器实际导入路径均在该独立源码树。

在独立目录执行：

```bash
make test lint package-smoke phase10x-smoke SMOKE_OUT=/tmp/opencode/r7-git-smoke SMOKE_SUITE_OUT=/tmp/opencode/r7-git-suite PHASE10X_SUITE_OUT=/tmp/opencode/r7-git-phase10x
```

**1012 passed、1 skipped**（371.68秒），Ruff、package-smoke、phase10x-smoke 全部通过；
主仓库另执行 `git diff --cached --check`。日志：r7 输出根 `git_closeout_consumer_check.log`。
与制作阶段完整工作树1022项通过的差异来自其他研究任务的未提交测试，不是r7测试被跳过。
测试依赖已保留的本地资产，不能解释为无数据CI全部通过。

本消费者提交包含16个文件，覆盖完整 r7 代码／文档／任务头。测试后只补本收尾记录，
运行代码与测试索引一致。消费者提交编号以本记录所在的 Git 提交为准。

## 交付复核与保留

收尾重新执行 `verify_fehlings_r7_delivery.py`，ZIP CRC/SHA、异目录入口与71项依赖闭包、
1657个非试管世界变换、441个r6来源依赖文件、14个生产者文件及8 mL实际网格体积均通过。
报告保持在输出根 `delivery_verification.json`。没有重跑 GPU 仿真、重写图片或更新已冻结 ZIP。

按已有保留规范：r7 为 KEEP_HEAD，r6／生产者 Blender及资产为 KEEP_SOURCE，
早期失败与暗纹诊断目录原位作为诊断证据保留。本次无需新增通用规范规则。
