# 科学实验修复中途收尾：状态、失败经验与恢复入口

收尾日期：2026-10-12。实验时间以各 receipt 的 UTC 为准，最近一轮为 2026-10-11。
这是用户要求的阶段性停靠与记录整理，**不是四任务完成报告**；本轮不启动新评测。

下一位实施者先读[当前交接说明](../operations/scientific-five-item-handoff.md)，再查本记录。
早期完整过程保留在[10-11 验收记录](2026-10-11-scientific-five-item-acceptance.md)及 Git 历史，
其中带时间的“当前”“正在运行”只代表当时。不要从最后一次搜索命中的 PASS 判断当前资格。

## 1. 停靠位置与交付约束

工作根 W：`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010`。
生产者诊断根 D：`/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/sciben_waterbath_120hz_20261010/silver_bad17_diagnostic`。

任务来源为[飞书文档第4节](https://aicarrier.feishu.cn/wiki/Og5Hw2fGGi8pIyk0SpBcrkGCnjf)，
已读取缓存 `W/evidence/document_section4.json`（revision 5333）。本次收尾没有重新联网读取。
原指定18条坏例映射在 `W/evidence/bad_case_matrix.json`，不是全部140条；其中bad11为
银镜mixed20/OpenWAM，bad08为水浴mixed5/GPT。恢复时按映射读原动作，不凭编号猜场景。

| 任务 | 当前可确认 | 未完成；恢复时先做什么 |
|---|---|---|
| 滴定 task10 | 已独立封包，原版 120Hz/1582步/满分；1条成功 LeRobot v2.1、坏例、四视频、20入口静态闭包 | 冻结该包；不宣称20环境全策略成功；未部署到建通目录 |
| 称量 task09 | 新候选两次 reset 正常；完整4000步/0.5分/sr0，四视频可读，2粒入瓶、3粒留舟 | 未发布、未生成新成功数据；从留舟失败及警告定位，不能直接重复慢倒 |
| 水浴 task12 | 多个限定夹具和部分原版坏例有历史证据 | 当前最终版本无完整资格；成功示范/训练数据允许待重采 |
| 银镜 task_z4 | 同上；完整 bad11 暴露容量/引擎失败 | 先缩小故障触发条件，不能将引擎崩溃记成普通任务零分 |

接收方只安装五类：`configs/tasks/scientific_experiments/`、
`saved/assets/scene_usds/scientific_experiments/`、`saved/tasks/scientific_experiments/`、
`genmanip/extensions/metrics/scientific_experiments/` 的代码提交、LeRobot 数据集。
独立生产/测试/转换脚本可留在本人制作区，但接收方不依赖这些脚本。
原版 GenManip core、SDK、机器人源不改；本轮接收仓库 `/mnt/data/chenjiantong/GenManip-Sim`
只读，不发消息、不推送、不更新飞书文档。
Scenario Forge 不增加 runner 或仿真核心模块；资产物理修复由 ConvertAsset 生产者承担。

已授权决定继续有效，不重复询问：

- 原生120Hz；称量4000步，水浴/银镜首轮7000步。7000/120=58.333秒，部分题仅加热就需59–60秒；重采再调整完整时间预算。
- 滴定先单独交付，其余继续；水浴/银镜成功示范允许待重采，不豁免引擎稳定性。
- 称量只减慢原倒料段的候选已获批准并已测试失败；“成功后才导出新数据”仍有效。
- 滴定有足够原采样时间证据后按原时长转换到120Hz，保留原轨迹和转换记录；文档坏例动作不擅自平滑/重采样。
- LeRobot 沿用v2.1，注明实际读取环境，不修改公共环境或库来伪装兼容。

## 2. 已交付内容与冻结点

唯一已发布目录：`W/delivery_releases/task10_standalone_r1_20261011T162354Z/`。

| 文件/身份 | SHA256 或提交 |
|---|---|
| RELEASE_MANIFEST.json | `10dfabecc0709d8647e18b9512a59f3c31c02ac0f6578543350b08ecef64159e` |
| offline_overlay.tar.gz | `f660a6cdd4c1714969b9f24ce600777d555951b3de1f4d21b573909c68faf95d` |
| task10_native120_v21.tar.gz | `3d275074d053ab4a0cbdba58eb7855e820fc24d8bccd77e9d6a61665020b592c` |
| metric 提交 | `38425dc6eb18fba6560184745acf27fe91241e10` |
| 原 GenManip 基线 | `0e99ea01eec7780e53fa2ce3ecb0fce1a6b4500a` |

离线包含51个YAML、693个USD/依赖文件、287个task data文件；两项metric文件与数据集单独交付。
原版成功运行 `five_item_task10_controller_reset_standalone_20261011T162925_436423Z`；
原坏例 `five_item_bad_03_20261010T191652_101574Z` 为2000步/0.2分/sr0。
坏例用独立测试客户端提交原记录；成功示范用原版LMDB客户端。不要把两者描述成同一客户端。
补查完整server日志两者均无错误及碰撞降级，封包字节未改。

标准数据读取环境：lerobot0.1.0、datasets3.6.0、torch2.10.0、av16.1.0、numpy1.26.4。
数据为1条1582帧、120fps、四路RGB；不是大规模训练集或模型成功率承诺。
评测MP4为原版30fps编码，每帧物理采样120Hz，播放慢4倍；不要从播放器时长推算物理时长。

## 3. 踩坑台账：下次不要重新走一遍

| 问题 | 这次的证据与结论 | 下次执行方式 |
|---|---|---|
| 以为交一个USD就够 | 原版还依赖YAML、重置数据、metric、动作与读取环境 | 先锁五类边界，在干净原版目录独立安装后验证 |
| 把多个背景当成多个成功任务 | 20入口闭包/配置检查与20条完整策略是两种证据 | 分别列静态入口、原版成功例、指定坏例；不扩大发布范围 |
| 用worker日志代表完整引擎健康 | server初始化曾有8条offset错误，worker/后注册回调没捕获 | 按VAL-001查server+worker从启动到结束；错误、警告、碰撞降级分开统计 |
| 零错误等同于没有问题 | 最新称量full有328765条faceIndex警告，且任务只有0.5分 | 写“PhysX错误行0”并保留warning分类；不能写无条件engine-clean |
| 两次reset通过就认为初始化根治 | 四目标metadata、Chassis-only各有反例；新组合只有2次reset+1次full | 保留限定证据；没有跨入口验证前不推广全部YAML/data |
| 用观察器成功替代原版失败 | 接触/时序观察器运行可通过，原版仍失败 | 观察器仅定位；最终用无观察器的原版入口，记录缓存/启动条件 |
| 把关节异常归因给称量控制器 | 控制器OFF仍复现44mm从动指；mimic重解析没有证明实际后端重解析 | 已排除“控制器是必要原因”；不要重复OFF/重解析来声称修复 |
| 慢一点就能倒完 | 批准的3454动作全程精确回放，只有grain03/04入瓶，3粒留舟 | 原样方案已失败；先分析有效倾角、舟内运动和接触，任何新方案说明改变了哪个因素 |
| 缩图误读LCD | 曾把数字166读成16.6；小数点不可可靠辨认 | 结合原图和显示实现：1.66仅为代码/粒重一致推断；没有末net/tare遥测就不能说读到了属性 |
| USD API复制导致碰撞退化 | rim v1漏保留未注册Physx API，预期SDF变成实心凸包 | 核对原始apiSchemas及实际4.1解析，不能只信GetAppliedSchemas或几何外观；v1资格撤销 |
| SDF参数单位理解错误 | margin/narrowBand是mesh对角线比例，旧.00035约53.4微米 | 查目标SDK schema单位；记录比例及实际尺寸，不能当成固定毫米 |
| 局部夹具通过替代完整机器人运行 | rim v2限定夹具和1800/3200短窗口通过，完整7000失败 | 原局部资格保留其范围；禁止自动放行最终包或整批队列 |
| 以为加容量或换求解器就解决 | 原容量溢出；64M接触/128MiB stack后CUDA700；PGS约2150仍失败 | 三者都不是当前解，未经新触发证据不再盲扫参数 |
| 从故障后视频倒推物理原因 | 接触溢出在1400–1500之间，先于heater大运动；容量版本1514行截止，早于源1568松手 | 对齐第一条错误、动作编号、画面，不把后果当成原因 |
| 搜索漏掉大写字段产生错误假设 | producer代码用CreateStaticFrictionAttr，实际与native同为2.5/max | 确认调用链与大小写；“夹具没设摩擦”假设已撤回，无需据此新实验 |
| 将控制器想象为粒子跟随瞬移 | 源审计未见正常运动时写粒子/刚体位姿 | 不基于此假设改控制器；初始恢复与运行控制分开审计 |
| 把新帧率动作配旧图像称为新数据 | 重新定时改变真实物理过程 | 成功原生回放后再采/导出状态与RGB；验证11数值字段、4视频、timestamps、标准reader |
| 分数低就改成功条件 | 原阶段权重、五粒条件是验收定义 | 保留原目标，不把2粒算完成；基础设施失败不填零分 |
| HEAD/目录名等于实际输入 | default_offsets的HEAD为9d85，但1529源文件来自790并单独对比 | 记录实际文件SHA、差异、缓存及提交；final/candidate名称不赋予资格 |
| 状态越写越乱 | 原CURRENT_STATUS和操作页混有多轮过时running/PASS | 当前状态只一份；历史进入有日期记录/快照；恢复前先读本交接入口 |

上述多数是本任务诊断事实，不是通用物理参数建议。没有证据证明默认offset、PGS、某个摩擦值
适用于其他机器人或资产。大量警告的因果关系仍未确认，不把它直接定为三粒留舟的原因。

## 4. 关键失败与禁止复用项

- 称量当前候选根：`W/task09_default_offsets_candidate_runtime`。只修training001；物理机器人、USD天平部件仍在，取消的只是额外registry项及非法offset预处理。
- 最新run：`task09_default_offsets_full_20261011T175508_482868Z`，4000/.5/sr0。3454源动作逐项相等，后546步保持末目标；四视频4001帧全解码。**不导出成功LeRobot**。
- summary：`W/evidence/task09_default_offsets_summary.json`，SHA `fb378eac58895811fefbc952cdd039e5100452e900c823f8a3b6a1d8c6dbba93`；生产者记录提交 `1e6cd94`。
- 审查图在候选根 `saved/repair_20261010/audits/<run_id>/`；四视频及meta在候选根 `saved/eval_results/scientific_experiments/<run_id>/scientific_experiments/task_09_solid_weighing/repair_training_001/000/`。
- 水浴/银镜TGS完整失败：`five_item_bad_11_rim_v2_full_20261011T160352_450143Z`；加容量失败：`five_item_bad_11_rim_v2_capacity_materialized_20261011T161652_088193Z`；PGS失败：`diagnostic_proxy_rim_v2_pgs_bad11_20261011T165536_668751Z`。均不能当正常低分坏例。
- `delivery_releases/task09_task10_r1_20261011T131822Z`未发布；旧四任务候选和`baseline_runtime`不是整包交付来源。旧称量满分与旧LeRobot只保留历史资格，不能替换最新失败。
- 旧双任务目录的 `evidence/task09_weighing_no_robot_retained_demo.mp4` 及 `retained_task09_no_robot_demo.json` 仍保留。它是保留实际状态的无机器人演示、2倍播放，不是最新原版机器人成功录像；不要丢失，也不要扩大其资格。
- `table17`、`scene128`、`rim_v2_full`的测试放行已撤销。相关revocation文件保留，旧局部PASS不消除新反例。
- 实验core分支、mimic重解析、只读观察器、生产/转换脚本均不进入接收方包。失败目录、源轨迹、临时缓存不在本次收尾中删除。

## 5. 恢复工作时的有限步骤

1. 读当前交接说明与W/CURRENT_STATUS.json，核对本次证据索引；先确认没有他人的GPU/端口任务，不全局pkill。
2. 保持task10封包不变。未来称量metric需考虑已安装的task10公共repair_checks，不能盲打包含重复公共文件的旧补丁。
3. 称量先离线看已存倒料片段及原动作，解释三粒为何留舟；把初始化、倒料、显示三个问题分开。新试验先写单一假设、预期可观测量、比较基线和停止条件，再跑一个有信息量的对照。
4. 水浴/银镜从已有首错时间与前后帧建立最小复现；不要再以短前缀PASS立即启动14例。新物理版本先生产者资格，再原版完整已知失败例；首个引擎错误即保存并停止本方队列。
5. 新完整示范满分、原生120、日志/视频/数据都合格后，再推广相关入口、核对未改坏例动作/阶段权重、跑受影响坏例、独立安装并另出新包。只生成满足真实结果的数据。

## 6. 本次收尾做了什么，没证明什么

- 核对16份关键证据文件存在并计算SHA，见[证据索引](2026-10-12-scientific-repair-checkpoint.evidence.json)。此索引不是重新仿真或重新验全部归档内容。
- 只读远程核对GPU为0MiB/0%，8087连接返回111；系统无ss，改用socket检查。未杀任何进程、未启动评测。
- 改写当前交接页，旧页和状态先存W/checkpoints/20261012_midway；完整旧内容也在Git历史。历史验收记录正文不重写，仅新增导航。
- 规范依据：基线`580ade4`，ASSET-001/002/003与VAL-001/002/003/004/005/006。本次仅澄清VAL-001：零错误不等于零警告，基础设施PASS不等于示范成功。物理默认、核心/schema/API/design契约无需变更。
- 大型USD/视频/运行日志留在W和D，不进入Scenario Forge Git；不把临时试验工具变成核心模块。
- `make check`退出0：1255 passed、1 skipped（549.10秒），ruff、package-smoke、phase10x-smoke通过；16份证据SHA及25个本地链接核对通过。日志位于 `W/checkpoints/20261012_midway/make-check.log`。本次检查不提升任何失败场景的资格。
