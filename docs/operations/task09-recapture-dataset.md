# task09 新数采数据制作与恢复

制作根目录：`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/task09_recapture_600_20261012`。
本页只记录外部制作流程；项目不新增 episode runner、模型适配或 benchmark 核心层。
决定与证据边界见 [日期记录](../records/2026-10-12-task09-recapture-dataset.md)。

## 输入与产物

- `manifest.json`：三个输入文件的来源、哈希、交付范围。
- `source/`、`extracted/`：不可变归档及安全解压结果。
- `episode_plan.json`：600 个计划 episode 对应的源示范、seen 背景和指令。
- `numeric/`：与可见连杆位姿一致的训练状态；动作原样保留。
- `evidence/numeric_validation.json`：60 条逐条数值闭合结果。
- `pilot/queue.json`：完整三条试制队列状态；各运行目录保留视频、关键帧、日志和报告。
- `evidence/pilot_acceptance.json`：完整三条和十背景的已完成验收门槛，不等于600条已完成。
- `production/queue.json`：持续生产状态、当前 episode、PID、完成计数与每条视频哈希。
- `CURRENT_STATUS.json`：任务概要；生产计数以队列为准。

## 验证顺序

1. 执行制作侧 `tools/test_source.py` 与 `tools/source.py`，通过后才使用生成的数值。
2. `tools/render_states.py` 在 Isaac 4.5 中恢复状态，只渲染；保持 timeline 停止。禁止把 Replicator 默认 `step` 当作无物理渲染。
3. 先做完整三条和十个背景关键帧检查，观察取瓶、去皮、倒料、回秤、读数及相机视角。
4. `tools/export_dataset.py` 生成标准 v2.1 目录，核对 Parquet、视频帧数及完整解码。
5. 在远程既有 LeRobot 环境执行 `tools/check_reader.py`；用现有隔离 datasets 3.6 路径，不修改原环境。
6. 上述门槛通过后才批量生产；最后检查 600 条、1248020 帧和 2400 视频，不得静默排除失败项或重复补数。

## 恢复与交付边界

先读进程记录与队列状态，核对实际 PID、GPU 和输出，避免重复启动同一 GPU 任务。
成功产物必须同时有完整视频、报告和校验；单有目录、进度文件或部分 MP4 不算完成。
失败目录保留，新尝试使用新版本目录。只停止本次拥有的进程。

批量入口为制作侧 `tools/batch600.py`，实际工作根中运行 `python tools/batch600.py --resume` 可以恢复。
恢复前必须确认原 supervisor 和其记录的渲染进程已结束；不要在已有活跃队列上再运行。
队列会核对已完成视频哈希、保留失败尝试，完成600条后导出数据集并在远端标准 LeRobot 环境校验。
状态 `DATASET_VALIDATED_FINAL_HANDOFF_REVIEW_PENDING` 只表示批量数据验证完成，还需最终清单、哈希及交付范围复核。

原生评测与数据生产是两条独立进程链。`tools/watch_native23.py` 只等待第二条原生测试结束并保存动作一致性、日志、视频解码结果，不更改动作或成功条件。
查看其 `evidence/native23_validation.json` 时仍需确认 scope；原生失败不能当作源成功记录失败，源状态回放成功也不能当作原生任务成功。

最终五项交付中的辅助说明可列出制作记录；接收方读取 LeRobot 或运行任务不能依赖工作目录下的脚本。
原生物理结果单独记录，固定 120 Hz、4000 步；源采样时间未知时，逐记录动作执行只是该输入序列的测试，不是原时长复现。
任务包若仍未通过物理验证，必须保留待完成标记，不能随数据集读取通过而升级为任务成功。

## 2026-10-12最终称量规则版本

用户确认的`task09_readout_4_to_5_g_once_v1`取消最终连续稳定要求：有效空瓶去皮后，瓶受秤盘承托、五颗均在瓶内、显示净重在4.0–5.0g（含边界），同一步满足即可。
设备原USD的stable状态不作任务通过条件，原生计重波动仍属已知现象；不要把规则版本变更写成修复了物理稳定性。

交付候选位于制作根目录`handoff_readout_range_v1`。`offline/`仅包含task YAML、scene USD、task data三类相对覆盖路径；`metric/`为指定目录代码提交补丁；LeRobot完成后独立交付。
`readout_receiver_runtime`使用接收方原始机器人资产，排除测试用robot_usds覆盖层。实验性的`native_geometry_support_runtime`不交付。
规则迁移、补丁检查及安装身份分别在`evidence/readout_contract_migration.json`、`readout_metric_patch_check.json`和`readout_receiver_identity.json`。
先核对`evidence/readout_contract_pair.json`中的成功/漏颗对照，再核对`evidence/readout_clean_receiver_run.json`和对应原生audit；不能用候选成功替代独立安装成功。
详情见[规则版本记录](../records/2026-10-12-task09-readout-range-acceptance.md)。

最终接收方原生成功证据为`evidence/readout_receiver_validation.json`：1.0分、3191步、接受时4.01g，原始机器人资产；视频末端读数字形有清晰度限制，不能用它代替字段快照。物化后的1143个文件校验见`readout_materialized_install.json`，当前输入为60条新数采及41条历史案例，共101份metadata、111份YAML。

`evidence/readout_clean_negative_validation.json`记录最终安装中的失败对照：0.1分、4000步、仅初始放瓶计分，与原型环境0.3分的`readout_range_source105_validation.json`区分。它不是隔离最终称量条件的反例；读数边界另由规则测试覆盖。原生重执行失败不改变源成功示范及600条渲染计划。任务内容总结见`readout_task_acceptance.json`。

前四类运行内容的独立压缩包为`delivery_archives/task09_readout_range_v1_runtime_payload.zip`，CRC和SHA报告在`evidence/readout_runtime_archive.json`。它不含LeRobot数据，不能替代完整五项交付。

收尾时同时核对`handoff_readout_range_v1/MANIFEST.json`的任务内容验收和数据集状态。`tools/finalize_readout_dataset_handoff.py`只在两者通过后物化最终数据、核对600/1248020/2400和标准reader结果，再生成`READY.json`。进程记录在`evidence/final_handoff_supervisor_process.json`；已有后台进程时不要重复启动。
