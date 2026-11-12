# Task09 标准 v3 接收安装与验收

状态：READY。正式目录安装、两档接收reader、40例独立初始化、四条记录动作回放的执行/日志/视频检查及视觉复核均完成；任务得分分别记录，不等同四例任务全部成功。用户选择完整称量任务交付：300/500 两档数据、Task09 YAML/USD/task data、基于建通当前版本的本地集成分支，并在正式接收目录执行 40 例独立初始化与四组 case1 回放。不做模型训练，不要求四例满分，不上传 OSS、不修改飞书或发送通知。

飞书 CLI 读取文档 revision 6732，文档要求离线任务文件安装至 `/mnt/data/chenjiantong/GenManip-Sim/` 相对目录、metric 代码提交；数据目录由用户确认沿用 `/mnt/data/chenjiantong/scientific_experiments_data/releases/task09_standard_v3/lerobot_dataset/`，并非文档指定。

工作目录 `/cpfs/user/zhuzihou/dev/task09-final-delivery-20261019`。接收仓库基线为 `f52f73b3eba570d13d8a171d9c6ae87a62526602`，包括同事新增物理修复及 Task10 安装。集成分支 `delivery/task09-standard-v3-final` 已顺序接入四个 Task09 提交，头为 `82cabca55427cb199565584f20746e6862f2394d`，旧分支保留。本阶段不向远端推送。

两档正式数据已独立复制，300 档 1504 文件、500 档 2504 文件逐文件 SHA 与制作侧报告一致。划分规则沿用，但 split_manifest 的 episode 映射使用 v3 实际 source-map 重建，不能沿用 v2 编排顺序；十条留出源不进入训练数据和统计量。隔离 datasets3.6.0 已物化复制，reader 不依赖原制作目录。

候选配置静态检查：40 例、20 场景、145 个依赖项，无未解析项；正式配置 4000 步、120Hz。候选任务文件来自已绑定新初态和动作的离线包，最终运行资格须以本轮接收目录新证据为准。已有六项 metric、三项精度及三项最终渲染清理回归通过。

远端为 `10.150.164.127`，四张4090；不会套用旧单卡IP。默认客户端包指向 `/root/GenManip-Sim` 旧版本，与记录客户端参数不匹配，候选启动因此失败一次；之后明确使用接收版本自带的客户端子模块，并保留原始失败日志。记录 LMDB 客户端字节与先前 stock-client 证据一致。候选工作区必须显式准备客户端子模块，不依赖空子模块目录。

主机隔离工具在外部工作目录：每GPU独立端口、Ray目录和Kit/Omni/texture缓存，指定物理renderer GPU、CUDA逻辑physics GPU0、关闭已验证不适用的headless GLinterop。初始化只通过标准服务 CLI 将步数覆盖为1，并使用只读观察器；正式配置仍4000，完整回放不启用观察器。所有启动、worker、client日志保留，不以退出0代替验收。

已完成候选冒烟、正式目录备份/切换/安装、40例独立初始化和160个初始视角复核，以及两档接收端reader和ZIP CRC/SHA。安装886文件，1479个未涉及的跟踪文件哈希未变；40个预热后几何中心包围检查通过。四条完整回放全部通过动作前缀/末帧保持、零底座增量、有限状态、完整日志及四视频解码检查，末段视觉复核、运行归档与最终清单已完成。

unseen_instruction_6 一次在 SimulationApp 返回前停滞超过600秒，尚未进入场景；634.98秒时保存诊断后对本次控制器SIGINT，执行拥有进程的定向清理。保留启动日志，原配置、原输入和原缓存的新run_id重试通过；不修改动作、阈值或SDK。失败尝试单独保留，不计入40个通过案例，不宣称已经解释或根治SDK启动停滞。

规范依据 VAL-001/002/003/004/005/006/008。规范无需变更：本次是既定任务的安装和绑定最终内容的验证，不改变核心契约、动作、评分阈值或通用物理默认。完成后同组同步 operations 入口与最终证据。

## 最终接收结果

| 案例 | score | success_rate | steps |
|---|---:|---:|---:|
| mixed_1 | 1.0 | 1 | 1798 |
| unseen_prospect_1 | 1.0 | 1 | 1829 |
| unseen_background_1 | 0.1 | 0 | 4000 |
| unseen_instruction_1 | 0.1 | 0 | 4000 |

两条0.1分回放保留任务失败：background终帧仍见固体在舟中，instruction末帧可见一颗固体在桌面。两条满分的接受读数分别为mixed4.11g和prospect4.13g，stable=false；prospect末视频帧约3.91g，未审计逐回调时序，不宣称稳定读数或逐帧物理复现。

40例预热后包围检查通过；查看160个初始视角及四回放的首/中/源末/最终选帧，视角裁切保留为限制，未逐帧认证接触。核查1049个本次进程身份无存活，8187–8190端口关闭，四卡显存归零。未做模型训练或连续切场资格。

本轮make check通过：1255 passed、1 skipped，lint/Phase10.x/diff检查通过。两档训练ZIP和运行ZIP均完成CRC/SHA核验。运行ZIP包含离线任务文件、代码bundle/mbox、环境说明、日志、截图、全部44次验收四视频及meta_record/result_info副本；完整RRD仍保留原生结果目录。增量bundle以f52f73b3为前提并已verify。

READY绑定MANIFEST SHA256：`5a816ade0ef52908f68ca77a483bc8adc967fca61e117bf62a1e226f1ca3c924`。文件、报告及归档哈希见[证据索引](2026-10-19-task09-receiver-installation.evidence.json)。正式README给出读取、独立case回放、三归档恢复及回退方式。Git工作区40个YAML差异为清单化的离线覆盖，代码分支已提交；未改写历史包。
