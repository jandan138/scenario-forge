# Task09 r2/r3 Git 收尾

用户于 2026-09-11 授权先完成 r3 Git 收尾，再制作近满瓶 r4。
本次将此前未提交的 r2/r3 生产者与消费者依赖一起纳入基线。

- ConvertAsset 基线 `3240ca3`：瓶/舟模型、场景生产、三组测试、日期记录及相关导航。
- Scenario Forge 基线 `90bfc13`：协议、称重、验证、回放、证据与打包、教程、记录及当前任务头。
- 对混合修改的索引与规范，按已审查内容从 HEAD 构建暂存版本，核对工作区原字节不变。
- 提交内容为源码与小型文档。r3 ZIP SHA 保持
  `e1ac66ae061a1706951f70e3364e3d5c30c6e94f44ffcdae59f6a90d3dd0235b`；
  r2 ZIP SHA 保持 `193a3c566348c65d223097d2c66dd5ced94273860417298205f46231369eca0a`。

## 拟提交版本验证

通过 `git checkout-index` 导出两个暂存快照到 `/tmp/opencode/task09-r3-{ca,sf}-index/`。
本地依赖测试使用显式 `outputs`、`external_artifacts/incoming` 链接；源码只来自所选暂存内容。

- ConvertAsset：`python -m pytest -q tests/test_task09_powder_bottle.py tests/test_compact_powder_bottle.py tests/test_compact_powder_scene.py`：**16 passed**，相关七个脚本/测试 Ruff 通过。
- Scenario Forge：`make check SMOKE_OUT=/tmp/opencode/task09-r3-index-smoke SMOKE_SUITE_OUT=/tmp/opencode/task09-r3-index-suite PHASE10X_SUITE_OUT=/tmp/opencode/task09-r3-index-phase10x`：
  **977 passed、1 skipped，274.21 s**；Ruff、package/suite smoke、严格 phase10x 及 diff 检查通过。
  日志 `/tmp/opencode/task09-r3-index-check.log`。
- 工作区先前的 987 项通过记录涵盖另外的未提交任务；本次 977 项来自只含拟提交内容的快照，二者范围不同。
- 暂存文件语法、体积、明显私钥/访问密钥标记及差异检查通过。

收尾后 r4 另出新候选与证据。通用规范无需变更，本记录仅说明版本边界和 Git 验证范围。
