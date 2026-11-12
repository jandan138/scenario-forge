# Round2 已校验原始证据清理

用户明确指示“已经 oss 归档的都清理吧”，取代本轮此前保留本地源的约定。该操作只清理已闭合、已完整上传和读回校验、逐文件 SHA 仍匹配的原始输出；不以 archive source_bytes 重叠总和推算释放量。

截至 2026-10-29T07:54:04.221658+00:00，实际逐文件删除 254,747 个源 payload，logical_deleted **63,507,049,057 B**，allocated_unlinked **64,989,290,496 B**。后者是原单链接文件对应的块数，不是共享 CPFS 池的 df 差值。另清理完成校验后的压缩暂存 295 包、26,086,907,796 B，单列计算；root 此前清理的暂存与恢复 tar 不混入源计数。全部 368 份 archive receipt 与原 committed-stage 字节一致。

清理保留 inputs/input_sources、原 metadata 小输入、脚本、报告、summary、证书和完整恢复定位。canonical 资产/config/taskdata/core、冻结 runtime_base、payload_complete_v2、当前 tube_band05_guard_iso33_v1 全树继续保护。已拒收 c1_sample_vmax6_guard_iso33_v1 仅闭合 runs/native_runs 的已校验大输出可清，inputs/tools/candidates/runtime_prefix2000 保留。没有整目录 rm。文件变化、硬链接、实际读者或闭包证据不足均不降低 SHA/保护门槛。跨任务旧输出使用独立 round2-closed-outputs OSS 前缀，当前 task head 路径重叠复核为零。

原 73 档及后续明确闭合的 fixture、旧 bath、多任务输出均按原所有者范围处理。三条更早 hot-switch 的原 sequence_results 首段另外建立追加 diagnostic unit；逐段 result/path/task/case/runID 和原失败记录保留，尾段已有 archive 的精确 member/SHA 定位保留。它们不冒充新版 native_sequence.v2 或自然 done 验证。worker 只在无 pack/upload/readback 的静止边界交接，同一 worker.lock、单 worker、16 MiB/s 限额继续有效。

删除后实际从 OSS 恢复一个 4,160,033 B 原生 overlook 视频到新目录，恢复 SHA 与删除审计完全一致，原路径仍不存在。新的 tombstone/restore 入口位于 source_registry；原 receipt 没有补造 end/result/SR。Git 的只读统计保留：当前 pack 为 0644，不满足只读硬链接门，未 chmod、未建立硬链接、未改路径/历史/HEAD，Git 实际释放 **0 B**。CPFS reflink 能力探针返回不支持。

剩余输出按明细保留；特定 admission HOLD 与当前输出 stat 清单均在证据快照中。它们不是整个原 174G 父实验树的完整归档证明，也不能用低 HOLD 或 verified 数量声称全部覆盖。当前输入/源资产、未确认所有者、delivery/review 副本和仍活跃输出不进入本次清理。C1 物理仍 rejected，39 项初始化仍 HOLD，归档不改变分数、READY 或任何任务资格。

规范依据：4f1b6a69c711773119fd5870c47e8093a1d105b7；涉及 VAL-003/005/006/008。**规范无需变更**：本次仅用户授权下的证据存储生命周期与恢复定位，不改变场景、物理、指标、包/API 或资格门槛。同一实现者已同步 [操作指南](../operations/scientific-experiment-oss-backup.md) 与本日期记录；完整外部证据由 [小型索引](2026-10-29-round2-verified-payload-eviction.evidence.json) 绑定。验证包含逐文件 SHA/身份检查、完整 OSS 读回、实际恢复、原 receipt 字节比较、当前 source/head 保护复核与 git diff --check；遵照 root 指令未重复运行已有两份 PASS 的 make check。
