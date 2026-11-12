# 新背景 validation v2：制作记录

状态：制作中，尚未安装或推送。现有 validation 保留。

用户确定：新增136例，覆盖20任务；task01–14四类各2例、z1–z6 mixed各4例。5套背景为教学化学、环境水质、食品理化、工业材料、制药分析，分配28/27/27/27/27例。仅背景组保持非背景基线，其余按各任务既有规则生成新样本并与旧validation去重。只换周围房间，操作台与材质、机器人、器材及物理设置继承基线；不制作新成功示范。

源基线为建通4baf01cddb588b6e396077b0d73f7bcfcdddd06c，含task07正式修复。136份配置和metadata已复制到`external_artifacts/validation_bg_v2_20261105/source_snapshot/`并登记哈希。当前只是源快照，不冒充新样本。

## 实现与验证

新增纯Python分配器`src/scenario_forge/generation/validation_background_batch.py`。先写失败测试，再实现；验证数量、组内背景不重复、常规任务覆盖5套、z任务覆盖4套、背景总量均衡、确定性及非法输入。`make check`通过：1257 passed、1 skipped，lint与Phase10.x均通过。

五张新参考图已生成，复制到本仓库external_artifacts下并登记reference_manifest.json。它们只是生成输入，不是USD或运行时证据。

用户明确要求停止使用外部模型服务，由当前Agent承担模型阶段。已终止原API生产进程，保留部分运行记录；随后由Agent编写房间设计及自包含Blender脚本，通过Code-as-Room既有room-source-v2导出器产出room.blend、room_source.usdc、source_manifest及support_relations。不是声称旧12阶段MLLM服务自动运行成功，也没有在Scenario Forge复制转换逻辑。

生产目录：`/cpfs/user/zhuzihou/dev/Code-as-Room/runs/validation_bg_v2_agent_20261105/`。
当前候选来源：`/cpfs/user/zhuzihou/dev/Code-as-Room/deliveries/room_sources/validation_bg_v2_agent_20261105_r3/`。
R1曝光偏高，R2俯视取景裁切，R3修正；旧候选保持。生产者数值支撑检查通过不替代ConvertAsset独立准入。五套r3正在由既有build-facade与normalize-asset进行/Room到/World准入，目标Isaac4.1。

任务状态与日志统一位于`external_artifacts/validation_bg_v2_20261105/`：batch_manifest.json、agent_rooms_r3_status.json、admission_status.json及各主题日志。背景准入、136例非背景新样本生成/去重、原生场景验收及建通交付仍未完成。

适用ASSET-001/002/003、USD-001/002、STATE-001/003、VAL-001/002/003/005。规范无需变更：本次沿用生产者、转换者、组合者的现有职责和证据边界，不新增通用物理参数或核心模拟器依赖。

## 分支流程更新

用户同步：原feature/scientific_experiments已合入feature/pioneer且远端旧分支已删除。已认证只读确认远端pioneer为7939a4c8，包含4baf01cd。当前临时分支改为feature/validation-bg-v2-20261105，从该pioneer端点创建；源配置/数据快照仍绑定4baf01cd，两者genmanip、科学实验配置和相机配置tree一致。后续只推临时分支并提PR，以Merge方式合入feature/pioneer，不重建旧远端分支或直接推主分支。已完成的旧基线canary保留，后续验证绑定新开发基线。

首例canary初始化与20步完成，但保存的原生图像接近全黑，尚未视觉通过。检查发现替换旧Room同时移除了GenManip额外的无纹理环境补光。候选组合正在显式继承源场景该环境照明参数（不更改任务物理或操作台材质）；需重新render验收。

## r5候选与新基线检查

五套r5房间均已通过ConvertAsset独立支撑、闭包和Isaac4.1准入；front_visible_open_floor的5.8×4.0m空间profile通过。地板接缝在生产者侧归入完整Floor组件，保留r3失败证据。房间组合采用已检查的平移(0,-1,0)，保留任务操作台及材质。移除旧Room后继承源任务无纹理环境补光，解决原生画面偏黑；r5采用可在固定机位区分的地面配色，固定机位主要看到地面和少量柜体，不能把这些视图当作房间全景。

136份配置、场景overlay、初始化metadata已在独立GenManip worktree生成。80条新指令经数值保留与文本去重；80例按来源声明的对象组进行局部XY重采样，粒子归属经几何核对，三类原粒子编号与容器顺序不一致的问题已在草稿阶段纠正。仅背景组保持非背景语义指纹。元信息改为新任务身份与初始化专用记录（num_steps/max_size=0、keys为空），不复制原LMDB。

GenManip新增轻量catalog及选择器测试，40项unit通过。Scenario Forge分配器/元信息适配器的4项测试和完整make check通过（1259 passed、1 skipped）。元信息相关处理置于adapters/ebench，generation层仅负责分配。冻结982个运行输入文件；原生136例检查将绑定各例输入哈希。

五套r5各一例完成原生reset和短步进，初态overview图由实现者复核，未见黑屏或明显缺资产；不是独立审查或完整任务成功证明。全部136例原生检查和最终PR仍待完成。当前临时分支feature/validation-bg-v2-20261105，目标feature/pioneer，旧validation和建通目录未覆盖。

## 批量原生检查启动

GenManip临时分支feature/validation-bg-v2-20261105已有候选提交020ee136（222个新文件）；其父提交是最新pioneer基线7939a4c8。新增catalog和选择器回归检查后40项unit通过。Scenario Forge生成工具与记录本地提交176b03b；未推送Scenario Forge仓库其他改动。

五套r5代表性画面已复核，保留固定机位只看得到地面/部分柜体的限制。136例批量检查在10.150.168.71 GPU0启动，绑定982个输入文件，复用5例完全相同输入的canary；普通案例20步，滴定/水浴/银镜320步以覆盖原生状态采样。每例独立运行ID与端口；仅对明确CUDA/端口临时故障冷重试一次，其他失败记账并继续，不计为通过。状态见external_artifacts/validation_bg_v2_20261105/native_batch_status.json。最终全例画面复核、交付安装及feature/pioneer PR尚未完成。

## 四卡迁移

按用户指示迁到10.150.164.127（Isaac4.1、4×4090）。仅停止旧主机本任务等待队列，原8例保留，未触碰scibench-test-repair作业。新主机默认客户端未正确处理异步reset；两次迁移尝试日志保留，随后显式绑定旧主机实际使用的共享genmanip_client源码，未安装或修改Conda环境。四卡首例均完成原生reset及短步进，初态overview由实现者查看，GPU UUID和进程映射核对通过。

每卡独立进程/端口/缓存/日志，Ray配置CPU16与object_store比例0.02（实际每路约8GiB）。每卡状态独立写入，由汇总器按任务ID去重；截至迁移确认累计12/136例完成，后续四卡续跑。详细回执FOUR_GPU_MIGRATION.json，统一进度仍为native_batch_status.json。

## 2026-11-06 单卡续跑

四卡主机在74例完成后失联，用户指定恢复到10.150.168.71。已确认Isaac4.1、GPU0空闲及共享目录完整；单卡控制器取得原四个shard锁后启动，保留74例并将原超时task07案例重新纳入。恢复后该超时案例已通过，截至本次核对累计89/136、当前失败0。旧失败和断线状态独立保留，不删除历史记录。

当前权威入口为external_artifacts/validation_bg_v2_20261105/ACTIVE_EXECUTION.json，状态single_resume_status.json同步发布到native_batch_status.json，避免读取旧的四卡RUNNING快照。当前进程继续执行，尚未完成全例视觉复核或PR交付。
