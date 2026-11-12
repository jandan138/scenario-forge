# Task09 制作目录写入失败与恢复

2026-10-17 10:43 UTC检查ETA时，六卡队列停在446/500，最后心跳约10:20 UTC。监督日志捕获退出码1和`OSError: [Errno 28] No space left on device`，发生在原制作目录写COORDINATOR.tmp时；异常处理再次写同一目录也失败，因此旧JSON仍写RENDERING。

## 已知事实与边界

原路径为`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/task09_recapture_600_20261012/standard_v3`。本机及四卡评测机向该路径创建小文件均失败，父级saved目录也失败。全盘df仍显示约39TB空余，inode使用率约32%；不能据此认定整盘容量或inode已耗尽，也没有证据把之前所有中断都归因于同一个问题。目录配额或后端限制的精确原因尚未确定。

同一共享存储的`/cpfs/user/zhuzihou`挂载子树可写。新的制作根为`/cpfs/user/zhuzihou/dev/task09-storage-recovery-20261017/task09_recapture_600_20261012/standard_v3`，位于Scenario Forge仓库之外；三个SSH主机均通过该路径1MiB写入及fsync测试。

## 恢复内容

446个已验收输出保留原位，不搬动、不删除，以原绝对路径和哈希继续引用。复制小型制作代码、配置、队列清单，建立新的日志、状态、输入生成、渲染和导出目录；原始录制与静态资产只读链接，mesh缓存复制为独立可写副本。未验收尝试留在原目录，新尝试使用新目录。

复制后逐项核对原队列绑定的代码哈希完全相同；标准parser在新根对源105/背景9完成往返验证，49个姿态轨迹、79个属性轨迹和原始动作一致。源数据和任务划分没有变化。新监督进程同时持有原BATCH.lock的只读文件描述符锁，防止同一制作机再次启动旧协调器；仍沿用新的原子owner目录和逐主机进程核验。

10:55 UTC以tmux session `task09-storage-recovery`恢复，协调器PID3307840，六路领取组91–96。新健康检查入口为新根下`tools/multi_health.py`；`/cpfs/user/zhuzihou/dev/task09-current.json`保存重定向信息。旧CURRENT_STATUS因目录不可写未能更新，不能再作为最新入口。

该记录仅说明存储迁移和生产恢复，不宣称全部数据、导出或最终接收安装完成。新目录剩余配额未从管理员侧取得，运行时写入与状态仍需检查。依据VAL-001/003/004/005/006；未新增场景/物理通则，规范正文与核心设计无需改变。

恢复后六路均已实际出帧，新目录下LMDB数据持续增长；对首个完整新输出（源105/背景9）单独运行标准数值校验，1484帧、动作/状态和实际28连杆读回通过原阈值。证据为新根`evidence/rendered-numeric-105-9.json`，绑定于[存储恢复证据](2026-10-17-task09-storage-recovery.evidence.json)。全组完成计数仍由协调器验收后更新，该单条探针不额外增加训练条数。
