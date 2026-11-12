# Task09 标准 v3 数据集 OSS 交付

状态：READY_OSS_DELIVERED。两档标准目录已上传，所有对象MD5及SSH代表回读通过，飞书称量进度已同步。用户确认：仅称量300/500两档，直接上传标准目录，采用全量传输校验及代表性OSS回读，不新增模型训练或场景回放。

飞书科学实验文档revision6749新增明确目标：`oss://pjlab-bjpai-sim/chenjiantong/scientific_experiments_data/lerobot_dataset/`。示例task_04表示命名方式，本次实际目标为`task_09_solid_weighing_300/`及`task_09_solid_weighing_500/`，每档直接包含data/meta/videos。此前[本地接收交付](2026-10-19-task09-receiver-installation.md)按revision6732完成，原READY及包保持原字节，本次增加OSS发布回执。

只读预检列出11个既有任务、22个两档目录；两个称量目标前缀均为空。现有滴定与水浴元数据为v2.1、lift2、15FPS、640×480四路AV1；本地两档20个字段定义与所核对的滴定数据完全一致。只读权限不作为写权限证明，随后在目标内实际写入一个预定Parquet文件成功。

源为建通本地release的两档已验收数据，分别1504/2504文件，共4008文件、约39.72GiB。重新逐文件核对生产报告SHA256并计算MD5；仅上传清单成员，不带缓存、ZIP或其他任务内容。使用sim-oss连接、限定两个目标、copy及immutable保护、64MiB分段阈值；实际最大文件约26.73MiB。上传先排除meta/info.json，非入口文件全部校验后最后写入入口元数据，不宣称目录发布具有原子性。

外部工作目录：`/cpfs/user/zhuzihou/dev/task09-oss-publication-20261019`。持久会话task09-oss-publish保存源清单、干跑、实际写入、对象校验和回读日志。正常代理变量仅在rclone子进程中移除，没有改全局配置或输出凭据。若远端无可靠MD5，逐对象下载计算SHA256作为后备，不以大小相等代替哈希。

代表回读从最终OSS目录下载各档全部metadata/Parquet及第0、中间、最后一个episode的四视频，先核对下载文件SHA256，再在SSH评测机10.150.164.127使用既定LeRobot环境读取每个所选episode的首中末帧及num_workers=0 DataLoader。该范围不等于重新全量解码；相同字节已有的全量语义和视频验收按原报告复用。

规范依据VAL-001/002/003/005/006；规则无需变更，仅同步外部交付目标与操作说明。通用指南和清单更新为revision6749要求；不改历史包资格，不新增核心接口。最终结果与哈希见下文。

## 最终结果

| 档次 | 对象数 | 字节数 | MD5核验 | OSS下载并SHA256核验 | 远端reader |
|---|---:|---:|---|---:|---|
| 300 | 1504 | 16801579096 | 全部通过 | 316文件 | episode0/150/299，各首中末，36次相机读取、3个DataLoader批次 |
| 500 | 2504 | 25849335937 | 全部通过 | 516文件 | episode0/250/499，各首中末，36次相机读取、3个DataLoader批次 |

所有对象均取得MD5，无仅按大小通过或下载哈希后备项。原生reader使用官方episodes选择接口；全部Parquet行数及总帧数分别为691220、1062420，核对通过。远端hostname为dsw-536365-78bdb944c8-q99ff，LeRobot0.1.0、datasets3.6.0、av16.1.0、torch2.10.0、pyarrow23.0.0，num_workers=0，离线模式运行。

首次验收调用未显式指定episodes，标准reader因此检查未下载的非样本视频并触发Hub回退，离线模式拒绝访问。随后只修正验收调用为官方episode子集接口，不改官方库或数据，失败日志保留。未将其当作OSS缺文件；全部OSS对象的完整性另由全量清单/MD5核验支持。

飞书仅更新称量进度block IMUYdEePXouuoYxoAyfcF9fNnvg。读取时revision6815，期间6816在其他单元格新增空段落，实际写入6817；历史版本比对证明6816→6817仅变更本次目标文本。并发新增段落原样保留。外部交付位置要求引用revision6749，不因进度更新改变其来源说明。

最终回执：工作目录OSS_PUBLICATION_READY.json；源本地READY和MANIFEST哈希保持一致，不重写旧包。详见[证据索引](2026-10-19-task09-oss-publication.evidence.json)。通用指南和任务清单已同步OSS发布要求。本次仅外部传输、验收及文档更新，无核心包/API变更；完成实际4008对象校验、832文件SHA256回读、远端reader、飞书定向变更验证、文档链接与diff检查。
