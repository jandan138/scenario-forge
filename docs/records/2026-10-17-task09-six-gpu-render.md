# Task09 四卡接入与六卡标准渲染

2026-10-17；用户要求保留现有两台生产并接入新四卡实例。本记录属于标准流程v3的外部生产调度，不改变Scenario Forge核心包、API或schema。

## 环境与资源

`root@10.150.164.127:22`，主机`dsw-536365-78bdb944c8-q99ff`，实际四张4090、各46068 MiB，约400 GiB内存、72个可用CPU。初检四卡空闲；原CPFS数据、两个GenManip仓库、Isaac 4.1.0-rc.7及指定提交的LeRobot已存在。未复制或重装Conda、未修改全局Python依赖。既有隔离datasets3.6.0下成功打开6894帧试制集，并读取首帧四相机和12维关节。

物理GPU编号/UUID：0=`GPU-6a600047-0d73-893f-8fb5-e55181d4ab28`；1=`GPU-c84d4ef4-0464-3c2d-5c17-a0247ebb0e09`；2=`GPU-cb7873d9-2c4a-3af3-cda5-0fce088382aa`；3=`GPU-28ab80b9-19a4-11f4-f1c3-565dcbb11b9d`。另保留`10.150.163.175`和`10.150.164.67`各一张卡。

## 实现与验证边界

新增制作根`standard_v3/tools/multi_*.py`，不改正在执行的dual脚本或标准renderer/recorder/converter/exporter字节。资源配置按host、UUID、物理索引明确分配：CUDA只暴露目标UUID，Isaac的active_gpu指定物理索引，physics_gpu在可见CUDA空间内为0，multi_gpu=False。仅检查目标卡占用，其他卡运行不阻塞。每卡独立Kit/Omni/RTX纹理缓存、日志和输出。

先在四张卡同时独立重渲染源3/背景1，均使用新的输出目录，不重复计入500训练条目。检查真实SDK进程组到NVML UUID映射、单个CUDA可见设备、数值/28连杆/帧数、全部JPEG解码、跨机关键帧和实现者目视。此处为记录状态渲染资格，不扩大为物理回放或仿真时钟资格。

调度器继续复用`dual/COORDINATOR.owner`全局原子目录，以及已有共享盘终态最长180秒等待。新卡通过后，仅暂停旧协调器继续派发，两条在途任务自然结束并验收，再保存清单、确认旧父进程退出并转交占用。新实时状态为`multi/COORDINATOR.json`。通过的卡参与生产；失败卡保留任务归属并停止接新任务，健康卡继续处理其他任务。

## 交付范围

训练来源仍为数字ID升序前50源乘10个seen背景，300档使用前30源；留出源和40评测任务不变。复用全部已验收产物，分组同背景且最多五条。达到500条后只交接一次既有标准导出/验收流程。后台生产不等于最终安装完成；接收目录部署、40次冷启动、四组完整动作回放和最终清单仍是后续门槛。

规范依据VAL-001/002/003/004/005/006/008。没有新的场景或物理通则，故规范正文和核心设计契约无需修改；本次同步任务记录、证据索引及操作说明。

## 首轮无头枚举问题与修复

首轮四卡均完成2494帧，但严格日志检查发现启动阶段`GLInteropContext::init: carb::windowing is not available`，因此全部保留为失败尝试，不计入资格或训练数据。旧尝试入口为`multi/PILOTS-with-glinterop-errors.json`。该类无头日志问题也有[NVIDIA论坛报告](https://forums.developer.nvidia.com/t/error-carb-glinterop-plugin-glinteropcontext-carb-windowing-is-not-available/262382)，该链接仅作背景，未提供本次修复的充分依据。

本次修复依据来自实际安装的`libgpu.foundation.plugin.so`：它包含`/renderer/gpuEnumeration/glInterop/enabled`开关。私有bootstrap v2显式关闭OpenGL设备枚举，保留Vulkan图形后端、CUDA和物理GPU配置；不降日志级别、不屏蔽错误、不启动X服务器或改全局环境。GPU1上的启动探针退出0，记录开关false、active_gpu=1、CUDA可见设备数1，日志无Error；见`multi/glinterop-probe.json/.log`。随后四卡用新目录重新完整试制，旧bootstrap/worker脚本及旧产物保持可追溯。

新的`multi_render_bootstrap_v2.py`与`multi_worker_v2.py`由各次job绑定哈希；`multi/headless-fix.json`记录修复范围。只有完整重试通过数值、全部图像解码、跨机对照、目视和日志门槛后才接入生产。

## 四卡资格结果与启动重试

修复后的四张卡均完成2494帧、四路完整输出，合计9976帧、39904张JPEG全部解码通过；每卡20个同帧图像与既有合格标准渲染对照，最大全图平均RGB误差分别为1.26824、0.91255、0.90256、1.18491/255。四卡实际28连杆逐帧读回、动作与状态均满足原阈值。实现者检查每卡四相机五个关键帧，未见黄格或缺材质，固体转移和瓶回秤可见，右腕末帧读4.56；顶部裁切和腕部遮挡保留，不宣称独立视觉审查或原生物理成功。

GPU1一次在SDK的omni.physx启动阶段无进度达300秒；尚未加载场景。核对worker命令参数、PID和独立进程组后，仅终止该worker，由其清理自己的SDK子进程。相同输入、相同缓存的单次新目录重试通过，GPU0/2/3未受影响。旧尝试与`startup_stall.json`保留在`PILOTS-v2-before-quad1-retry.json`索引，操作日志为`multi/startup-retry.log`。

正式生产使用`multi_worker_v3.py`，与合格v2使用相同渲染bootstrap，仅新增预场景启动监控：SDK未完成启动且日志300秒不更新时标记可重试错误；进入场景后的停滞、数值/日志错误不属于该重试范围。协调器确认所属主机上的原任务进程已经退出后，同一组最多重试一次，每次用新目录。连续启动失败隔离该lane，健康lane继续处理可用任务。相关回归覆盖首次启动失败后成功、第二次仍失败时不再重试。

`multi/PILOTS_ACCEPTED.json`绑定四卡数值、图像、目视、实际渲染期间NVML进程组到UUID映射、缓存设置及既有两卡资格。确认六路均合格后才启动原双机队列的自然结束交接。

本轮完整`make check`退出0，1255 passed、1 skipped（512.25秒），lint/phase10x/diff均通过。外部专项测试随后共41项通过，其中新增多卡测试12项；新增路由/启动分类模块在实现前先出现失败测试。后续仅为外部启动监控和文档变化，执行对应外部回归与文档diff检查，不重复核心全套检查。

## 六卡接管

原组58、59自然结束并通过完整收据检查后，旧协调器PID633368退出。`multi/migration/ADOPTED.json`确认保留291条合格结果，并绑定迁移前后脚本身份。新协调器PID1218725在制作机运行，按资源分别领取组60–65；原两张卡继续参与，四卡实例每张卡各一个进程。四条硬件资格试制不重复计入训练集。

新状态入口为`multi/COORDINATOR.json`，查看命令为`python standard_v3/tools/multi_status.py`；`CURRENT_STATUS.json`已同步，旧入口快照保存在`multi/current-status-before-six.json`。接收仓库分支仍为`delivery/task09-standard-v3`，提交`a13c22fa5dcaec6f82aa09da60b80aa206dd12be`，此次仅增加外部制作调度和环境启动器，不改已提交的metric或渲染修复。

## 实际并行证据

接管后六个独立SDK进程均已产生持续增加的帧计数，三个主机的NVML记录分别显示1、1、4个目标GPU上的实际计算进程，约8 GiB显存/卡。六组输入互不重叠且不在已完成清单中；原497个批量source/background对与三个既有试制仍恰好覆盖500条，分组清单与双机阶段逐字节相同。

`multi/concurrency-audit.json`、`multi/gpu-concurrent-snapshot.json`和`multi/checkpoint-six-running.json`保存291条已完成时的运行证据。资格与代码、测试、迁移、作业清单的哈希索引见[证据索引](2026-10-17-task09-six-gpu-render.evidence.json)。该快照不是整批完成证明，实时进度继续读COORDINATOR.json。

完整渲染完成后自动导出300/500并做数据验收；接收方安装、40次独立初始化、四组完整回放和最终交付清单仍待后续完成。本轮未把数据制作状态升级为接收方READY。

## 08:42 UTC 中断发现及恢复

用户再次询问ETA时发现协调器心跳停在约06:22 UTC，状态文件仍写RENDERING，但PID1218725已不存在，三台主机六张卡均空闲。最后持久化完成数356，另有组73的完整VALIDATED收据未计入；其他在途目录保留，不能仅凭目录或旧进度计为成功。没有协调器异常栈可确定退出原因，不能宣称已证明是SSH断开、OOM或实例重启。

核对旧owner已退出、所有原任务的精确命令参数在所属主机均不再存活后，使用原协调器`--resume`恢复。组73经哈希核验接纳，计数升至361；其余未验收组使用新尝试目录。调度器改由既存、独立于工具调用的tmux服务托管：socket `web-terminal`、session `task09-six-gpu`，新PID2543693，日志`multi/coordinator-tmux.log`。不把start_new_session单独视为持久运行保证。

新增只读`multi_health.py`，同时检查心跳年龄及当前协调器PID/启动标识/owner身份，进程不存在时明确显示停止状态，不再仅转述JSON中的RENDERING。原状态脚本和已绑定证据保持原字节；CURRENT_STATUS入口改为健康状态脚本。此次仅恢复生产和改进进程托管/状态展示，不改数据处理或渲染代码。

## 09:44 UTC 再次中断与监督层补充

再次询问ETA时，完成数416，最后心跳约09:35 UTC；协调器PID2543693及tmux任务窗口均不存在，三台六GPU空闲，六个在途任务没有完整组收据。此次证明仅改用tmux不足以解决退出问题。原因仍未确定：未获得异常栈；本地cgroup v1读取memory.failcnt=56242、约100GiB内存上限、oom_kill=0，这只能作为内存压力线索，不能据此判定或排除OOM。

保留`multi/recovery-20261017T094657Z`状态快照后恢复原队列，416个已验收结果不重做，未验收尝试保留并另起目录。新增`tools/supervise_multi.sh`在tmux中保留shell监督进程，协调器通过setsid使用独立进程组；监督日志记录启动时间、PID和真实退出码，tmux启用remain-on-exit以保留最终退出状态。仅对被信号终止、状态仍为RENDERING且无数据错误的协调器进行有限恢复，最多三个启动尝试；恢复仍由原脚本逐主机确认旧任务已退出。普通错误退出不自动重跑。

监督层故障注入测试通过：首次SIGTERM后成功恢复；普通错误只执行一次。记录为`multi/supervisor-test.json`。新监督日志`multi/supervisor-events.log`、协调器日志`multi/coordinator-supervised.log`；09:48 UTC新协调器PID2946622，状态心跳恢复且无错误。数据转换、渲染及导出代码未变化。
