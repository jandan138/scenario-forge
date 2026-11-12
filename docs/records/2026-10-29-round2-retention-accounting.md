# Round2 保留数据与删除账收尾

Root 独立复算过的 807 个唯一 tar 路径及 accounting 原账已冻结，SHA 为 `e335b7275e92211de97c95f0c52668493cdd201b26b498ddf744d8b677e5ef20` / `7fda2ea4b875549caa63e43657d6afbe61818cf5ebc1355f11ce0c92cfebfafe`。原文件与冻结副本均不覆盖，后续新增写 accounting_latest.json 与新快照。

26,086,907,796 B 是较早 watcher 累计；12,787,386,898 B 是其后的增量，两者相加为 38,874,294,694 B。当前 watcher 累计 40,079,252,543 B 已包含这两数，不能重复相加。Root 的 32,863,771,206 B 已含 73 个上传暂存和 2 个恢复 tar；agent 此前 141,163,321 B 为另 3 个恢复 tar，另有 client steps 恢复 tar 12,493,623 B。全部 807 路径相互无重复，合计 73,096,680,693 B；对源 payload 的 919 份删除审计比对，tar/source 路径重叠为零。

86 个尚存但 exact member/SHA 已 verified 的文件逐项复查：80 个受当前解析输入/映射保护，3 个 8–17 KB 的原始 cleanup failure 日志保留；另 3 个连续原始 JSONL 通过原 controller/archived closure 所有权、新鲜真实主机 PID/PGID/NVML/FD、当前输入依赖和本地无读者、单链接、相同 inode/size/mtime/SHA 门后，实际再清理 **13,919,265 B**（allocated_unlinked 13,934,592 B，3 文件，无 HOLD/skip）。原生 receipt、结果和失败字段均未改。

当前累计原始源为 **73,283,751,965 B**，加全部唯一 tar 为 **146,380,432,658 B**；另新建重复冻结 raw 副本删除 **1,150,684,088 B** 单列。若统计全部这些实际 unlink 路径，合计 **147,531,116,746 B**。这些是跨 CPFS/本地暂存的删除事件字节，不是当前容量净增或共享 df 差值。剩余原统计口径 **1,324,967,448 B** 保留，包含输入映射、原始失败证据，以及还需单独所有权/闭合 admission 的 trace/native 数据；9 个无原 metadata 声明的派生 NPZ 未因 hash 相同而删除。

当前可见 /tmp 实占约 35.66 GB，其中 pytest 约 24.95 GB（不在本次授权范围）、归档 scratch 约 5.72 GB。归档 scratch 留有 12 个无该 generation verified receipt 的失败 tar，共 4,718,032,122 B；已 verified 的 stage tar 没有积压。失败 tar 在逐 member 内容覆盖证明通过前保留，原失败日志/manifest 保持；没有为审计再复制同量 payload。/tmp 是 kubelet empty-dir 子目录，df 显示整块共享 ext4 后端；09:50–09:53 后端可用量由约 166.4 GB 回升至 326.2 GB，而可见子树用量稳定，本容器 deleted-open 大文件为零，因此不能把后端约 160 GB 波动归因本归档目录。

归档 worker 1190702 与持续 stage watcher 1047611 的身份、源码 SHA、心跳和存活复核通过，当前无 unresolved archive failure；未中断传输或触碰活跃 T1、GPU、输入、源码/资产、Git、ledger/READY。恢复入口是 R/archive_oss/local_eviction_registry.json 与 restore_any_evicted.py，新增 3 个文件各保留原路径、archive/member、manifest SHA、内容 SHA 和实时闭包证明。

规范涉及 VAL-003/005/006/008。**规范无需变更**：仅证据存储生命周期与真实删除账复核，不改场景、core/package/API 或任务资格。实现者同步本记录、[证据索引](2026-10-29-round2-retention-accounting.evidence.json) 与 [操作指南](../operations/scientific-experiment-oss-backup.md)。验证包含原唯一账 SHA、路径集合不交叉、当前成员 SHA/输入依赖/所有权/无读者检查与 git diff --check；未重复 make check。
