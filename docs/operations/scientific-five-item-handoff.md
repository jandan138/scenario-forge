# 四项科学实验修复：受限交付操作记录

当前为候选修复阶段：称量与滴定已通过限定原版回放；水浴/银镜的联合液体与机器人接触仍有CUDA失败，最终交付尚未就绪。任务范围为09称量、10滴定、12斐林，以及文档18对应的银镜任务。
当前无原版远端评测队列运行；生产者正在验证减少试管PBD底部碰撞形状的候选。
旧归档与名含 `final` 的实验目录都不代表最终资格。最新决定及证据限制见[任务记录](../records/2026-10-11-scientific-five-item-acceptance.md)。

工作根为 `/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010`。
其中 `baseline_runtime` 是以原版 GenManip 为底座的验收 checkout。自己的主 checkout
已切至 `delivery/scientific-five-items-20261011`，同样为原版core加允许的metric提交，
并同步四任务当前候选；3172个候选文件哈希与验收目录一致。588个非允许范围的原版
Git blob（587个普通文件和1个原始软链接）保持原内容。旧core实验保留在
`experiment/scientific-repair-runtime-hooks-20261010` 历史分支，旧资产/data另存工作根
`experimental_main_payload_snapshot/20261010T185138Z`。候选仍有未通过项，不能
把整个主 checkout（含本方工具和实验记录）作为交付包。

## 允许交付的内容

| 类别 | 接收仓库内的相对路径或形式 |
|---|---|
| task config YAML | `configs/tasks/scientific_experiments/` |
| USD及其资产依赖 | `saved/assets/scene_usds/scientific_experiments/` |
| task data | `saved/tasks/scientific_experiments/` |
| metric代码 | `genmanip/extensions/metrics/scientific_experiments/`，单独代码提交 |
| LeRobot | 完整数据集目录，包含 metadata、Parquet、视频 |

生产、转换、验证辅助脚本保存在工作根的 `five_item_tools` 等目录，不作为接收方运行依赖。
当前部署与验收只在朱子厚目录进行；没有向陈建同目录写入，也没有推送或改飞书文档。

metric提交为 `9d85d222e213d34bda43e8834266e4fff401ce56`，父提交为原版
`0e99ea01eec7780e53fa2ce3ecb0fce1a6b4500a`。它只改允许metric目录中的5个文件。
工作根的 `metric-only-9d85d222.patch` 是同一提交的补丁；原版core未列入该提交。
具体文件清单与补丁SHA见 `evidence/metric_only_commit.json`。

## 运行与数据含义

运行目标为 Isaac4.1、原生120Hz。USD自行携带任务控制和必要SDK初始化；metadata通过
原版已支持的属性恢复接口工作，不依赖新增core helper。

滴定的 `titration:initial_points`、初始速度、重置标记和epoch由metadata恢复，再由USD
控制器统一恢复粒子点、速度、宽度、ID和质量。该任务不同时启用通用
`initial_particle_states` 恢复：限定对照中，重复恢复导致接收量异常，控制器单独恢复
则在释放5.454mL时全部接收、零洒出。完整原版机器人回放仍作为最终门槛，不能用此
无机器人对照替代。

滴定动作的120Hz转换保留原LMDB及转换记录。为帧数兼容而重复的原观测不是新采的训练
观测；训练数据来自实际物理状态捕获与对应离线渲染。原生评测视频编码30fps，查看
动作时以帧号定位；LeRobot候选按真实捕获频率标为120fps，不混用两种播放时间。

LeRobot候选沿用现有导出工具的v2.1格式。独立RGB导出工具修复BGR/RGB顺序，最终
数据集不导入或调用该工具。旧的非RGB候选已标记 `NOT_QUALIFIED`，不作为交付。
生产机旧LeRobot与datasets4.5不兼容；隔离验证使用未修改的LeRobot0.1和datasets3.6，
未改写原环境。导出文件中11个固定float32向量的Hugging Face描述由新`List`规范化为
v2.1兼容的`Sequence`，所有Arrow数值和视频字节不变。称量3372帧、滴定1582帧均已
通过未修改读取器的首/中/尾帧读取；接收训练环境版本仍待用户提供或确认沿用v2.1。

标准候选目录为工作根 `lerobot/final_candidates/task09_native120_v21` 与
`task10_native120_v21`。两者均已有首轮单示范资格记录 `QUALIFICATION.json`。
滴定训练源在最终USD和未修改原客户端/core上1582步满分通过，评测源1574步满分通过；
机器人状态差异保留在证据中，不能套用称量的逐位一致结论。仅覆盖各一条示范。

## 验收与已接受的待补项

称量原版关键回放 `five_item_task09_sdk_graph_20261010T164048_441466Z` 已取得1.0分、
成功率1、3372步；原始4000步上限不变。四路视频完整解码通过，实现者查看了四路
关键帧，总览和右相机可见末帧4.56g；顶部裁切与腕视角遮挡记录为WARN。没有独立审查，
也不宣称逐帧目视检查。

用户允许水浴和银镜在首轮明确写“完整成功示范待重采”，先交资产修复和真实坏例结果。
不得为其合成成功轨迹或将初始化片段当成成功训练样本。此决定不免除原版可运行、
资产有效性和坏例证据要求。

验收目标是全部18条坏例按文档原动作顺序回放，目前尚未全部完成。水浴首条`unseen_background_3`已完成7000步，
得分0.15，四路视频解码通过；移出水浴后累计加热停在16.325秒。银镜首条`mixed_1`
在约2077步触发articulation求解器CUDA700，未产生完整结果，保留为异常尝试，后续
银镜回放暂停排查；不把用户接受“待重采”解释为接受引擎崩溃。

银镜后续fluid-only候选已完成本地7000动作及冷态、升降、管杯和管架接触验证，
并以独立USD强层接入20场景，原scene.usd保持不变；远端9条原版坏例仍待验收；等待队列已因水浴bad06失败而停止。
该fluid-only候选仅修改银镜资产，并保留原SDF刚体接触；后续代理诊断在另一个冻结的原版目录进行，未替换此候选。大量非致命SDF face-index
警告保留为限制；不能把本地通过或“无CUDA错误”写成全部物理/任务通过。

自动检查覆盖结果、视频完整解码、原生时钟日志
及物理错误，画面仍需另行查看。周期时钟日志不保证包含最终计数快照，其限制应保留。
坏例任务未成功与基础设施异常分别记录，不能用零分替代没有完成的运行。

工作根 `delivery_candidates/20261010T193046Z` 已有五类候选归档及逐文件/归档哈希，
3188个离线覆盖文件、metric补丁、称量/滴定各一份LeRobot数据。tar成员哈希与gzip
CRC/长度完整验证通过；当前状态已更新为 `CANDIDATE_WITH_UNRESOLVED_WATERBATH_PHYSICS`，保留在本人目录，
尚未完成其余水浴/银镜坏例验收，不用于覆盖接收仓库。

最终打包前核对：五类路径白名单；无包外资产引用/逃逸软链接；哈希绑定最终内容；
原始140个评测goal的阶段结构和权重不变；20环境映射保留；每项待补与已通过范围清楚。
当前证据见工作根 `evidence`、`baseline_runs` 与 `audits`，不能仅凭目录名含`final`
或进程退出码0判断可交付。

USD依赖扫描与MDL字面资源检查需分开解释：80个入口的USD依赖无缺失；原始MDL中
2568处可选材质浏览器缩略图注解指向未附带的`.thumbs`文件，未发现缺失的运行时贴图
字面引用或目录外贴图路径。此限制不能写成“所有浏览器缩略图完整”。

规范依据为 ASSET-002/003、STATE-002/003/005、VAL-001/002/003/004/005；没有新增通用
物理参数或包契约。运行器、辅助导出代码及大型场景/视频不进入Scenario Forge核心层。
