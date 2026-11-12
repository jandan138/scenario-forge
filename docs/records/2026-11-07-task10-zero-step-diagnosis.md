# Task 10 step-0 失败诊断（2026-11-07）

本轮诊断已完成；历史 NaN 未复现，根因未定。已确认评测初始化检查及异常结果分类存在缺口，不能将本 episode 归为普通操作失败，也不能据此认定滴定 USD 有错。本记录不构成 USD 或运行环境的无错误认证。

## 对象与证据位置

原始 episode：`pi05_all14_100000_noaug_task07fix_20261105T072804Z/scientific_experiments/task_10_titration_experiment/unseen_background_2/000`。

原始数据根：`/mnt/data/chenjiantong/GenManip-Sim/saved/eval_results/scientific_experiments/`。

本轮证据根：`/mnt/data/zhuzihou/GenManip-Sim-diagnostics/t10-zero-step-20261107/`。所有探针、重建运行目录、截图及日志均在此目录；未向 `/mnt/data` 根目录散放文件，未修改原始 USD、任务数据或评测成绩。

- [结构化结论](/mnt/data/zhuzihou/GenManip-Sim-diagnostics/t10-zero-step-20261107/DIAGNOSIS.json)
- [全部实验结果](/mnt/data/zhuzihou/GenManip-Sim-diagnostics/t10-zero-step-20261107/RUN_SUMMARY.json)
- [原始状态审计](/mnt/data/zhuzihou/GenManip-Sim-diagnostics/t10-zero-step-20261107/HISTORICAL_TARGET_STATE_AUDIT.json)
- [原始 worker 日志片段](/mnt/data/zhuzihou/GenManip-Sim-diagnostics/t10-zero-step-20261107/historical_worker_excerpt.log)
- [原生日志扫描](/mnt/data/zhuzihou/GenManip-Sim-diagnostics/t10-zero-step-20261107/FINAL_ENGINE_LOG_SCAN.json)
- [输入完整性复核](/mnt/data/zhuzihou/GenManip-Sim-diagnostics/t10-zero-step-20261107/INPUT_INTEGRITY_FINAL.json)

## 已确认的失败链路

1. 原始 `meta_record.pkl` 的第一帧观测已含 NaN。全部 32 帧中的双臂（32×12）、夹爪（32×4）、底座（32×3）状态均非有限。
2. 原始 worker 在 `2026-11-06 05:36:47.977` 报告 `Invalid robot state detected at step 0: non_finite_arm_state`。执行计数日志显示一次动作尝试，随后记录 30 帧异常尾部。
3. 对应环境代码先在 `reset()` 采集初始观测并返回，未做有限性检查；第一次 `step()` 的异常检查发生在 `_step_cnt += 1` 之前。因此结果为 `steps=0`，并不表示从未尝试执行动作。
4. 记录中的 `model_output` 是解析后的关节目标，不能当作模型原始输出。初始状态在该动作之前已异常；不能由该动作中的 NaN 或 `policy_avg_inference_time_ms=-1` 推断模型是起因，或推断没有调用推理。
5. `result_info.json` 没有保存 `termination_reason`，仅留下 0 分、0 步，使环境无效 episode 容易与普通策略失败混合。

最早有确证的异常位置是初始机器人状态读取/观测。原始日志缺少初始化各阶段的底层状态快照，无法进一步区分物理解算、状态读取或场景生命周期的具体触发点。同一 worker 的前后相邻 episode 均有有限状态；后续同类滴定 episode 成功，故不是已证实的持续损坏或全场景必现故障。

## 执行与结果

共完成 9 个独立进程实验，覆盖目标场景 10 次初始化检查及邻近场景 1 次检查，均未复现 NaN。

| 实验 | 数量 | 结果与限制 |
| --- | --- | --- |
| 目标冷启动 | 3 次 | 初始化及逐 World.step 读取均未发现 NaN |
| 同进程连续 reset | 3 次，1 个进程 | 三次目标初始化正常 |
| 邻近背景冷启动 | 1 次 | 初始化正常 |
| 紧邻 T09 的完整记录动作 → T10 | 3 次 | T10 均正常；T09 得分分别为 0.3、1.0、0.3，只有中间一次对齐历史成功结果 |
| 原 worker 六段前置任务 → T10 | 1 次 | 完整 24,700 条动作，六段得分与历史一致；T10 上层、底层关节及记录首帧均有限 |

完整序列为 T06 `unseen_prospect_3` → T07 `unseen_background_8` → T08 `mixed_2` → T08 `unseen_background_8` → T09 `mixed_7` → T09 `unseen_prospect_3` → 目标 T10。六段执行长度分别为 4,500、4,500、4,154、5,000、4,000、2,546；得分分别为 0.6、0.5、1.0、0.8、0.0、1.0。实际传入关节目标数组与历史记录逐条一致，但这不代表完整物理轨迹逐帧一致。

静态检查未发现目标场景和机器人已写入的 NaN 属性、非有限世界变换或缺失关节目标；9 个恢复对象的位置有限、四元数有效。搅拌子 `rotateZ` 默认值为空，但 241 个时间采样值有限，不能误报为 NaN。静态检查未覆盖所有动态碰撞和运行条件。

历史和完整回放均出现跨场景交错的 `FIVE_ITEM_NATIVE_CLOCK` 计数。当前回放出现该模式而未出现 NaN；日志缺少订阅实例标识，不能据此证明回调残留是 NaN 原因。

## 原生错误及不可扩大解释的边界

完整历史回放原生日志记录了 84 条 Error：前置离心机/烘箱阶段有非根 articulation link 速度设置错误、机器人碰撞 contact/rest offset 错误，场景切换还有 `/Camera does not exist` 和 ScriptNode `release_instance` / `release` 错误。三次短 T09→T10 回放各有 3 条场景释放相关 Error。另有大量 PhysX 材质面索引 Warning。详情见 `FULL_HISTORY_ENGINE_ERRORS.json` 和 `FINAL_ENGINE_LOG_SCAN.json`。

这些错误需要独立调查，不能以得分对齐判定运行合格；也不能在缺少因果实验时归为本次初始 NaN 的根因。早期 `CURRENT_ENGINE_ERRORS.json` 仅为阶段性扫描，最终以 `FINAL_ENGINE_LOG_SCAN.json` 为准。

重建代码基线为 `4baf01cd`，来自运行命名及提交时间推断，未取得原始启动 hash 凭据。资产使用当前挂载的相关文件，而非已认证的历史不可变快照。27 个冻结输入文件的哈希在结束时全部一致。

运行主机 `10.150.168.71`，Isaac Sim `4.1.0-rc.7+4.1.14801.71533b68.gl`，RTX 4090，驱动 `570.153.02`；详细版本见 `ENVIRONMENT.json`。原 Ray 节点不可访问，本轮直接调用相同环境类，未还原原 Ray 调度、异步视频保存及可能的同 GPU 多 worker 并发。细粒度探针可能影响时序，另做低频读取对照；两种模式都存在前置结果差异，不能单独归因于探针。

早期依赖导入失败及诊断脚本模块命名冲突均在进入实验前失败，详见 `HARNESS_NOTES.json`，不计为目标复现。未找到可复现的目标 NaN 因素，故未执行盲目参数扫描或宣称因果修复。所有自有模拟进程已正常退出，最后 GPU 检查无计算进程。

## 归因与后续建议

- **已确认责任范围：评测环境入口与结果记录。** 建议在 reset 返回观测/调用策略之前检查机器人状态有限性；保存初始化失败、运行中无效状态等原因，并与正常策略失败分开统计。本轮只诊断，未实施上述生产改动。
- **USD 是否是 NaN 起因：未证实。** 不能向资产作者定责；静态阴性和兼容环境回放阴性也不能证明 USD 在原条件下绝对无问题。
- **进一步定位的最短路径：** 在原 worker 启动条件下记录代码/资产 hash、Kit 原生日志、GPU/worker 对应关系，在 scene initialize、post_initialize、布局恢复、预热、首帧返回及首动作前保存高层和底层机器人状态。捕获首次 NaN 后，再对实际触发因素做单因素对照及恢复验证。

## 规范与仓库范围

适用 [VAL-001、VAL-002、VAL-003、VAL-004、VAL-005、VAL-008](../standards/validation-and-delivery.md)，范围仅限本次历史 episode 的诊断证据、回放校准及限制声明。仓库基线 `d077659c6de17e9ed8cdab2fad6e1b52ebce75ed`，工作区已有其他改动，本轮保持不动。

规范无需变更：未实施场景/包/API 改动，也未形成新的通用物理规则或已验证修复。历史任务包不重写。仓库仅新增本记录；大型产物、诊断脚本和运行目录留在外部目录，未引入核心 episode runner 或 benchmark reporting。只对本记录做文档检查，不运行与该文档变更无关的 `make check`。
