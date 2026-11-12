# Task10 真液体 120 Hz r2：原生时钟与重新资格

状态：120 Hz r2 资格验证完成。主包为双运行时规定无机器人流程，VR 为 Isaac 4.5 场景集成资格；发布文件及哈希见下列交付回执。

用户要求实际运行最多 120 Hz；本次明确采用 Isaac Sim 4.1/4.5、真实 1/120 秒
物理步、位置迭代 min=max=64。另出新主包和 4.5 VR 包、视频及自包含 HTML，
保留旧 240 Hz 包和证据。共享发布目录保持原 `scene.usd`、`scene_isaac45.usda`、
`SubUSDs` 样式；原 chenjiantong 源不修改。

规范基线：`90295bcb6d17fe0061e300d3a5f47ac15763cf25`。
涉及 ASSET-001/002/003/006、USD-001/002/003、MAT-001/003、STATE-001/002、
VAL-001/002/003/006。ConvertAsset 负责碰撞及真实液体初态；Scenario Forge 消费新版本，
负责集成、原生步进验收、说明与归档。参数为任务范围，不新增通用液体默认规则。

## 旧证据的边界

旧版物理配置和验证器显式推进步长是 1/240 秒。Isaac 4.5 在打开已有 USD 后可能清空
`SimulationManager` 场景注册而未重新登记已加载 PhysicsScene，此时 World getter
回退为 1/60 秒。旧验证器手动调用底层更新并传入 1/240 秒，因此旧报告不能证明普通
World/Play 会正确采用所需时钟；也不能作为 120 Hz 资格。旧报告与包字节不重写。

诊断文件位于 `outputs/task10_real_liquid_120hz_r2_20261010/`：
`clock_diagnostic`、`clock_registration`、`clock_sync`、`clock_native_steps`。
单纯开关 active 未修复注册；完全 Stop 时经公开 USD API 暂时将 PhysicsScene 类型改为
Scope 再恢复，触发 SDK 同步登记，属性和关系保持。交付函数不写 SDK 私有缓存或替换 getter。
这只修正 SDK 场景发现，实际物理 dt 仍必须另用回调验证。

## 新验证工具

`scripts/task10_clock.py` 统一读取任务 runtime_contract 和核对原生回调。
VR prepare/reset 从合同获取 Hz 和迭代次数，并调用停止态场景同步。
控制器拒绝与合同不一致的正物理 dt，防止错误时钟继续累计释放预算。

`scripts/validate_task10_native120.py` 使用原生 World.step；不向底层手动注入 dt。
每次 PhysX post-step 读取粒子并检查内腔，覆盖 SDK 暖启动和采集重置。
最初若干步与 World.step 返回后的 after-fetch 数据逐值核对。所有物理回调均记录；
验收报告必须同时匹配实际 dt、World getter、USD Hz、64 迭代和逐步内腔采样数。
渲染 60 Hz 的 Play 时钟/落液 smoke 与规定运动的完整流程分别验证。

已有探针（均使用未重新平衡的诊断初态，整体不合格）：

- `native41_probe`：146 次回调均为约 0.008333333768 秒；原生时钟、post-step 读回、
  实际到液和质量守恒通过。液位失败；过短开放时间未形成连续流量判定样本。
- `native45_play60_probe`：362 次回调均为约 0.008333333768 秒；60 Hz 渲染、120 Hz
  物理、64 迭代，实际接收、连续滴液、质量和剂量守恒、全程内腔通过。初始液位失败。
- `native41_play60_probe`：363 次回调均为约 0.008333333768 秒（含 3 次暖启动）；
  原生时钟、连续滴液和守恒通过。旧初态的液位与源管内腔检查失败。

仓库检查：最终代码的 `make_check_delivery.log` 中 `make check` 通过，1255 passed、1 skipped，
耗时 595.59 秒；lint、package smoke、Phase 10.x 和 diff check 均通过。
早一轮检查在文件仍被修改时导入了旧模块对象而失败，随后在稳定代码上完整重跑通过；
保留两份日志，不把前一轮写成通过。

## 生产者修复过程

旧 240 Hz 初态在真实 120 Hz 下液位偏低，源管局部存在瞬态径向越界。
生产者还发现原夹具碰撞代理进入滴定管孔；随后按可见开孔结构修复并重新预平衡。
保留粒子数量、实际速度和名义水质量，不以删粒子、冻结粒子或隐含 240 Hz 子步通过验收。
详情与中间失败证据位于 ConvertAsset 的 `outputs/task10_pbd_120hz_20261010/`。

生产者增加源管局部凸碰撞壁后，GPU aggregate pair 缓冲区曾不足，导致引擎提示可能漏掉
碰撞配对。该轮 wall04 数据作废，不用来拟合物理参数。后续合同显式传递
`scene_gpu_found_lost_aggregate_pairs_capacity` 和 `scene_gpu_total_aggregate_pairs_capacity`，
本候选均为 8192；SF demo、VR prepare/reset、采集配置和活动场景读回检查同步消费。
这是缓冲区容量，并不增加物理步频或位置迭代次数。

下文保留两次冻结的静态与运动证据差异。最终交付状态以末尾的资格和发布记录为准。

## 静态资格与首次完整流程的差异

生产者 `snapshots/native120_prebalanced_09` 已通过两版独立 30 秒静态冷启动：
各 3602 个原生步骤、全程零越界、902 次液位检查全部在原容差内。
冻结 manifest SHA-256 为 `1797951647848d017f0504e7dca343c1ec8182a6213211e1bc31acc04d492884`，
PBD 层为 `b04836f4d7970e092a2896ff1c2bab7dcd93efcb5ad6e93c844f8c1d8c36aaa4`。
生产者 `cold09_receipt.json` 绑定全部 92 个冻结文件。此静态资格不扩大成运动资格。

SF `checks/main41_full`、`checks/main45_full` 的原生完整流程均未通过：唯一失败项是
Receiver 运动保液。两版记录同样 493 个越界步骤，最多 96 粒，最大径向误差 4.414 mm；
Source 与 DeadPrecharge 始终零越界。计量、终点 15.255 mL、重置、过量、漏接、质量和
剂量守恒等检查通过。所有旧报告、09 冻结及未发布的暂存构建保留；不将这个视频记录用于合格交付。

最严重的粒子位于瓶底圆角，例如局部坐标 `(37.408, 1.615, 3.730) mm`。
该处半径随高度快速变化，径向 4.414 mm 并不表示玻璃法向穿透了同样距离。
对全部 270 个保存的运动帧进行 CPU 重算，图形刷新后的粒子/刚体姿态与同一步 post-step
越界数完全一致。独立生产者运动探针还逐步比较了粒子和刚体的 post/fetch 读回，均一致，
从而没有把此次失败归因于观测错位。

生产者随后按原内腔轮廓补充归一化凸分块，完整包含底部圆角，并在原玻璃平底高度
3.684 mm 处补充解析接触面，没有抬高玻璃内底。该阶段运动诊断在 4.5 达到全程零越界，
随后重新校准了 Receiver 液位；冻结16与完整流程结果见下节。

## 冻结16与主包完整流程

最终采用生产者 `outputs/task10_pbd_120hz_motion_20261010/snapshots/native120_prebalanced_16`。
manifest SHA-256 为 `4bba3b3c82654b44a8f912e9c538dfa9a2c704f1beb899a1aa59e38b3b582f3c`，
PBD 层为 `163d61b76653dc906164790a30889a680a1ce87654055cfcc42876eff205a963`。
`cold16_receipt.json` 包含全部 91 个文件哈希，已由 SF 再次逐文件复核。
保留全部 155658 粒和真实初始速度；Source 配方不再改变，Receiver fluidRestOffset
校准到 838 µm。新增 1600 个侧壁/底部圆角凸分块及 1 个原玻璃底面接触盘；可见几何和
原始对象摆放不变。壁面 rest/contact 为 1.5/1.75 mm，底盘为 0.6/1.6 mm，均为本任务数值配置。

冻结16的双版本静态冷启动各 3602 步均零越界，902 次液位采样全部通过。
原生完整流程 `checks/main41_full16`、`checks/main45_full16` 随后各完成 5470 个物理回调，
三个保液集合全程零越界；初始液位、规定晃瓶、连续滴液、15.255 mL 终点、保持、重置、
19.089 mL 名义过量、漏接、粒子质量及剂量守恒全部通过。实际 dt 均为约
0.008333333768 秒，World、PhysicsScene 与合同一致，位置迭代保持 64。

`main_full_gate.json` 对双版报告、当前验证器/时钟模块及全部运行输入进行一致性准入。
4.5 完整流程保留 1232 个 30 Hz 实测粒子状态帧；按隔帧采样得到 616 帧、15 fps、
41.066667 秒、1920×1080 的 1 倍速视频。实测记录哈希、逐值回放、等值面范围、
全部视频帧解码与关键画面人工目视检查均通过。视觉复核由实现者完成，不声称独立评审。

## 文档同步

新增 120 Hz 主包和 VR 操作指南；旧指南及历史包继续描述旧版本。
规范无需新增通用参数规则：本次属于既有 VAL-002/003 要求的时钟变化后重新验证与证据绑定。
已同步主包/VR 操作说明、旧指南的历史入口说明、规范案例索引及本记录；核心包/API 契约未改变。


## 最终接入与交付证据

所有路径以下列输出根为基准：`outputs/task10_real_liquid_120hz_r2_20261010/`。

- 主包完整流程：`checks/main41_full16` / `checks/main45_full16`，各 5470 步。
- 主包 60 Hz 渲染 Play：`checks/main41_play60` / `checks/main45_play60`，各 603 / 602 步。
- VR 直接完整流程 `vr/checks/direct_full`：5712 步，含一次采集重置。
- VR 外部物理场景挂载完整流程 `vr/checks/mounted_full`：5834 步，含两次采集重置；
  挂载 `/World/_scene`，PhysicsScene `/World/CollectorPhysics`，偏移 (+1,-1) cm。
- 另外三个边界、固定种子偏移 (+0.3647,-0.8924) cm 及直接 Play60：各 722 步，全部通过。
  边界和固定种子是初始化/连续落液 smoke；完整运动/终点资格来自前两项，未夸大为每个偏移都跑完整任务。

上述全部报告都通过原生 120 Hz、64 迭代、逐步内腔、初始液位、质量和剂量检查；
`main_full_gate.json`、`main_play_gate.json`、`vr/runtime_gate.json` 绑定当前代码和运行输入。
额外直接 Kit Play 探针不创建 World、不调用注册同步：主包 4.1/4.5 各 241 步，VR 4.5 为 242 步，
均为 1/120 秒且控制器有效。其范围仅为直接打开时钟，不替代完整保液资格。
记录为 `direct_play41_final`、`direct_play45_final`、`direct_play45_vr_final`。

一次 fixed-seed 启动误将相对 `--entry scene.usd` 当作包内路径；报告/日志保留在
`vr/checks/seeded_random_bad_cli`，不计入验收。改用绝对入口的独立冷启动通过。
最后批处理在第一份直接 Play 报告后因大小写判断退出；该物理报告本身为 pass，
其余两份直接 Play 探针另行独立运行通过，不将批处理退出码冒充报告结果。

VR 房间全景、初态、15.26 mL 终点、重置和 19.09 mL 过量画面位于 `vr/preview_replay`，
`vr/visual_review.json` 绑定逐一目视结果。教程为 `html/task10-liquid-color-tutorial.html`：
新版实际截图内嵌，离线桌面/平板/手机、剂量交互、十个颜色参考点、打印和禁用 JS 阅读均通过。
`html/audit.json` 与 `html/visual_review.json` 分别记录浏览器检查和实现者目视检查。

主包为 `handoff/scientific_workbench_titration_task10_real_liquid_120hz_r2`；
VR 包为 `vr/handoff/scientific_workbench_titration_task10_real_liquid_vr_120hz_r2`。
相邻 ZIP 及 SHA-256 由 `handoff/delivery_receipt.json` 和 `vr/handoff/delivery_receipt.json` 给出。
新视频在主包 `media/task10_real_liquid_demo.mp4`。
干净共享发布位置为 `/mnt/data/chenjiantong/scene_usd/zzh_fixed/task_10_titration_experiment`，
即用户 `/shared/smartbot_new/chenjiantong/scene_usd/zzh_fixed/task_10_titration_experiment` 的本机映射。
原共享 240 Hz 目录完整备份为同级 `task_10_titration_experiment_240hz_r1_backup_20261010`；
`publication_receipt.json` 记录发布目录逐文件哈希和旧版保留检查。
依赖闭包、移位加载与原可见场景保真由 `relocation.json`、`vr/source_preservation.json`
及 `colleague_layout/export_parity.json` 记录。旧 240 Hz 包、ZIP、HTML、原始来源均保留。

范围仍限于规定晃瓶后静置 2 秒再回移的轨迹、单位挂载和局部 XY ±1 cm/yaw0；
没有实际头显、机器人抓取、任意快速手部操作或实时帧率资格。
