# T1 初始化 40 入口的 STOP 收口

状态：HOLD。T1 的真实杯底穿出已触发全局物理拒收，初始化通过不提升整体资格。

外部证据根目录：`/cpfs/user/zhuzihou/dev/scientific-round2-repair-20261026/bath/repair_20261028/tube_band05_guard_iso33_v1/init40_execution_report29_v1`。

- `FINAL_INIT40_HOLD_SUMMARY.json`：接受 21/40，其中原入口 native 初始化 20 项、Silver 库存 scene-init 1 项。native 仅原相邻 10 条动作的初始化范围；stock 仅 30 tick，无 taskdata/动作/任务成功资格。实际启动 22 项，第 22 项未接受，另 18 项未启动。
- `STOP_race_order22_unaccepted.json`：第 22 项于 14:24:12 启动，顶层 STOP 于 14:24:29 发布，派发监控于 14:24:30 进入 HOLD。监控停止后续派发，未终止远端在途进程；该进程于 14:25:47 自然 exit0。保留真实 receipt，不补造提前终止或接受结果。
- `final_HOLD_gpu2_closure.json`：14:29:07 在目标 host 独立检查 22 个 runID、105 个记录 PID（亦保守作为 PGID 检查），均无残留；两次 raw NVML GPU2 为空，lease 可独占，8472 可绑定。GPU2 UUID 为 `GPU-cb7873d9-2c4a-3af3-cda5-0fce088382aa`。
- `global_barrier_registry_proposal_v1/actual_three_owner_cpu_readback_v2.json`：init40、normal、matrix 三种 consumer 对同一显式 registry 的 CPU 检查均返回 HOLD。23 个边界测试通过。

原始嵌套 `matrix56_batch_case_lanes_v1/GLOBAL_T1_STOP.json` 在 11:47:13 已发布。漏检有两个原因：本地派发器只查顶层；远端递归扫描虽覆盖该目录，文件名谓词只接受 `STOP`/`T1_STOP` 前缀、`.STOP` 后缀或 `STOP_BARRIER` 子串，遗漏了 `GLOBAL_T1_STOP.json`。这是调度消费者的发现缺陷；不得用后续初始化结果覆盖物理拒收。

外部 registry 提案通过显式路径、SHA、schema、candidate/scope、原记录字段和三种 consumer 集合校验共同状态，缺失或异常均 HOLD。它尚未接入任何 owner，不能宣称已修复运行链路。今后实现应让所有 owner 绑定同一 registry，并在取得共同派发锁后、启动前再次核对；STOP 发布与启动需共享协调机制，否则单纯轮询仍有在途竞态。当前不恢复 GPU，不自动清除 STOP。

原 receipt、旧失败/HOLD、assignment、冻结 binding/helper 与输入均保留。没有修改 SDK、场景资产、核心 runner、ledger、分数或 READY。规范依据为 VAL-002 的分类型证据与资格范围要求；规范无需变更，因为此次是外部调度故障记录和未接入的 CPU 提案，不构成通用运行时契约。未重复 `make check`；本轮执行外部 CPU 边界测试并记录真实资源闭包。
