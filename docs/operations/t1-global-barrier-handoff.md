# T1 全局 STOP 交接

当前 T1 已物理拒收，所有后续 GPU 派发保持 HOLD。冻结初始化工具与已有 receipt 不改写。

收口证据与范围见 [2026-10-29 记录](../records/2026-10-29-t1-init40-global-stop.md)。外部 `init40_execution_report29_v1/global_barrier_registry_proposal_v1` 是 CPU 提案，尚未部署到各 owner。

后续 root 明确授权新候选后，交接时应显式列出各 owner 共用的 registry 绝对路径、SHA、schema、candidate/scope 及 consumer 集合。各消费者必须验证全部登记的 barrier 来源路径、SHA 与结构；缺失、变更、未知状态均保持 HOLD。不要通过文件名猜测全局授权状态，也不要以局部任务通过覆盖全局物理 STOP。

共同派发锁、STOP 发布与启动前检查的集成需要单独实现及验证。CPU 提案的边界测试不代表 owner 已采用，也不能消除启动后才发布 STOP 的在途情况。在途进程的取消或自然收尾必须如实记录，不能修改原始 receipt 使它看似更早终止。
