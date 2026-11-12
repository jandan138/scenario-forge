# Lift2 科学实验路径隔离交接

## 当前入口

- GenManip：`73066ae3d066a100269f7957663173ab6e9843de`，分支 `delivery/zhuzihou-scientific-round2-validation-20261029`；未 push。
- 候选目录：`/mnt/data/zhuzihou/GenManip-Sim-deliveries/releases/lift2-path-isolation-r1-20261030/`
- 候选包：`/mnt/data/zhuzihou/GenManip-Sim-deliveries/releases/lift2-path-isolation-r1-20261030.tar.gz`
- 包 SHA-256：`b94399f460233ccf23abe699b68e26a1990367a66d81fe92b612cb742ac3a68b`
- 构建与验证证据：`/cpfs/user/zhuzihou/dev/scientific-lift2-path-20261030/`

候选状态为 `CANDIDATE_VALIDATED_NOT_INSTALLED_NOT_PUSHED`。原 R2 活动交付、共享 `robot_usds/lift2` 和水浴 runtime 均未改。

## 已验证范围

957 份科学实验 YAML 仅新增 `usd_path: robot_usds/lift2_scientific_experiments/robot.usd`；缺省、`None` 和空字符串仍走旧默认。新目录12个文件独立且哈希一致。完整 unit 37项通过。

科学 test、validation 实际加载新 layer；默认对照实际加载旧 layer。task11 P2 回放3604步、score 1.0、SR1、杯体16/1、无 guarded invalid state，原始输入前缀不变。四路视频完整解码，关键连续帧无甩臂或容器弹出。既有20类 PhysX 错误签名与 R2 相同，不称为无错误运行。左右相机遮挡限制精细接触目视判断。

## 共同合并前

1. 等水浴版本完成，不触碰其运行目录或公共旧机器人。
2. 重新扫描合并后的全部 `configs/tasks/scientific_experiments/*.yml`，确认新增水浴配置也带正确 `usd_path`，并保持 anchor/alias。
3. 复查代码提交、候选资产和证据哈希；若内容变化，刷新受影响验证。
4. 仅以新增方式安装 `robot_usds/lift2_scientific_experiments`，逐文件核对 manifest；不得删除或覆盖公共 `lift2`，不得使用 `rsync --delete`。
5. 接收验证通过后再更新安装清单和活动交付入口，按约定完成双方 squash 集成与统一 push。

回滚仅删除仍匹配候选 manifest 的新增资产并回退独立代码提交；不得删除或恢复公共 `lift2`。

## 证据索引

- `migration_report.json`：957/977/1914及字节、语义差分。
- `asset_report.json`：12文件来源、独立 inode 和 USD 依赖。
- `final_static_report.json`：最终变更 allowlist 和排除文件不变。
- `runtime_audit.json`：实际 layer、DOF、LMDB、执行前缀、结果、错误签名和媒体解码。
- `visual_review.json`：独立 A/B 与关键连续帧结论及遮挡限制。
- `runtime_infrastructure_retries.json`：两次非物理基础设施重试。

本次没有形成新的通用场景规则，因此未修改 `docs/standards`；任务特定决定按 ASSET-002、VAL-001/002/003/004/005/008 记录。
