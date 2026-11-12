# Round2 client 输出归档与追加清理

本次继续用户已授权的归档后清理，补齐原 native result_path 单元未包含的 client 输出。原 receipt、实际 client.log 输出目录参数、每行 steps 的完整 episode_id、原 task/case/metadata 和真实主机闭包逐项绑定。285 个有原 controller end 的 client 单元完成实际上传、完整远端读回、源稳定性检查和逐文件 SHA 清理；另 5 个原 receipt 缺 end 的失败 client 由此前已 remote_verified 的显式外部终止证明、原 metadata 哈希和新鲜 PID/PGID/runID/NVML/FD 观察建立独立有限诊断快照，未补造任何 end/result/SR。

截至 2026-10-29T09:17:27.319728+00:00，新增原始 client 实际删除 **8,613,965,377 B**（8,616,353,792 B allocated_unlinked，580 文件）。此外，134 个原 receipt.contact_observer.path 精确绑定的已闭 observer 单元另清原始 JSONL/NPZ **1,148,818,266 B**（1,150,316,032 B allocated_unlinked，491 文件）。两类新增原始源合计 **9,762,783,643 B**；此前完成的 **63,507,049,057 B** 单列不混入新增。两期显式相加为 73,269,832,700 B。新建重复冻结 raw 副本删除 1,150,684,088 B，另列；压缩暂存也另列，不能作为原始源释放量重复累计。allocated_unlinked 为原单链接文件块数，不是共享池 df 差值。

完整源 SHA/身份/读者门逐文件执行；已纳入本批计划的 SHA 删除没有跳过项；未绑定内容在 admission 保留。首次 v7 client pilot 因旧远端 prefix 白名单拒绝，原失败日志/暂存保持；独立 v8 只显式增加本项目 client 前缀，30 个 CPU 所有者/路径/原字节/进程/NVML/FD/prefix 边界测试通过。4 次 FD 扫描不完整被拒绝并保留源，后续真实重新取证通过后才上传和清理。已有失败诊断引用的另 10 个边界测试通过。worker 只在静止 idle/error、无 pack/upload/readback 时交接，同一 lock、单 archive worker、16 MiB/s 限额不变；既有持续 staging watcher 未中断。

实际从 OSS 下载并恢复已经删掉的 client steps 到新目录，1,499 行、1,631,057 B 的原始 SHA 与 episode_id 全匹配，原路径仍不存在；下载 tar 也经 exact SHA/无读者检查后删除。merged MP4 和原 actions/state/mode/clock 字节按实际 schema 保存，未因“可重建”删除未归档数据。全部 799 份 archive receipt 与原 committed-stage 字节一致。新旧删除路径重叠为零；52 个当前 task head 路径、820 个已解析输入文件和当前 T1/P/control/source 保护范围保持。Git 释放为 0，未改路径/模式/历史/HEAD；未启动或停止 GPU，未改 SDK、场景、输入、score、ledger 或 READY。

剩余原统计口径输出 1,338,886,713 B 保留，明细列出需独立 sequence/fixture controller 闭合 admission 的 native/trace、映射输入，以及 9 个未被原 metadata 声明的派生 NPZ。该数不是“全部未归档”或可删除量，也不是整个原 174G 父树覆盖证明。C1 rejected / 39 项初始化 HOLD 的科学状态不因归档改变。

规范依据：4f1b6a69c711773119fd5870c47e8093a1d105b7；涉及 VAL-003/005/006/008。**规范无需变更**：仅外部证据存储、原始数据保留和恢复定位，不改 core/package/API、物理或任务资格。实现者已同步 [操作指南](../operations/scientific-experiment-oss-backup.md)、本日期记录和 [小型证据索引](2026-10-29-round2-client-output-eviction.evidence.json)。大型脚本/清单/审计全部位于 R/archive_oss/client_output_closure_20261029。验证包括 40 个 CPU 边界测试、实际全量上传/读回、逐文件删除审计、原 receipt 比对、真实 OSS 恢复和 git diff --check；未重复已有两份 PASS 的 make check。
