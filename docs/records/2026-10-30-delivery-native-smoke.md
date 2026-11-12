# 原生交付冒烟与 task09 配置问题

日期：2026-10-30。状态：回放与连续运行通过；task09 生产配置仍需修正。

## 结果

在建通实际仓库 `/mnt/data/chenjiantong/GenManip-Sim`、提交 `97ae5e98` 上完成三项测试：

1. 原装 server/client/LMDB 回放：task11 3604步、task12 3582步，均 score 1.0、SR1；原始动作前缀和四路视频完整。
2. 同 worker 连续两回合：task11/task12 的000与001均完成，score 1.0、SR1。首次发现第二 seed 缺少 metadata，复制相同000 task data 作为001测试夹具后通过；未改生产 YAML 或已有文件。
3. 20个任务族原生 reset：19个直接通过，task09 使用测试映射后通过。测试配置已清理，Git 工作树和两台主机 GPU/进程均已释放。

证据：`/cpfs/user/zhuzihou/dev/delivery-native-smoke-20261030/`。

## task09 阻断点

生产 `task_09_solid_weighing/validation/mixed/mixed_1.yml` 使用 `Chassis: Chassis`，但实际 USD 只有 `/World/_scene/obj_analytical_balance/Instance/Body`，reset 报 `Accessed schema on invalid prim`。测试专用 `Chassis: Body` 映射初始化成功，证明是配置路径错误而不是资产缺失。当前生产配置未修改，不能标为已修复；最终发布前需审核并修正受影响配置。

这是新增交付问题，不影响已完成的其他测试结果，也不改变既有水浴和物理限制。无需修改通用 standards；按 VAL-001 保留初始化与任务成功、测试夹具与生产配置的明确边界。
