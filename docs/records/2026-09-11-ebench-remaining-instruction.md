# 2026-09-11 EBench 预放置任务的剩余目标指令干预

## 研究目的

EEOS 重复实验中出现勺子完全未移动的轨迹，促使 Astra 重新检查指令中的已完成子目标。
本次为预放置条件准备可分离的语言干预：将原指令缩短为
`Put the spoon into the small basket.`，其余四个对象已按来源演示终态放入大篮子。
原来的五个原生目标判据全部保留，不靠删减判据提高分数。

## 实现

`adapters/ebench/intervention_suite.py` 新增可选 `preplaced_instruction`。
只对 preplaced 条件生效，full 条件保留原指令，避免尚未放置盘子却只要求处理勺子。
`task_data.instruction` 与顶层 `language_instruction` 一致更新；每个 cell 记录原文、
生成指令与是否改变。默认不改变旧任务语义，历史输出不重写。

配置：`configs/research/ebench_dish_remaining_instruction.json`。
输出：`outputs/ebench_dish_remaining_instruction_20260911_r1/`。
任务已安装至独立 `eeos_evolution/dish_remaining_r1_*` 名称空间，但尚未执行模型。
沿用四条件编译结构，EEOS 当前只计划使用 control/preplaced 的新指令条件。

## 验证

先运行新增约束测试，确认旧实现未更新指令而失败；实现后两项 adapter 测试通过，
Ruff 检查通过。静态比较实际 control/preplaced 场景，全部 prim、schema、属性值、
关系与连接相同，`task_data` 仅 instruction 不同。审计文件位于 EEOS：
`outputs/ebench_evolution/remaining_instruction_scene_audit_20260911.json`。
完整 `make check` 已通过：1003 项测试通过、1 项跳过，耗时 317.49 秒；lint、
package smoke、Phase 10.x smoke 和 diff 检查通过。日志原位为
`/tmp/sf-remaining-r1-check.log`，并已连同哈希归档至 EEOS 的
`outputs/ebench_evolution/validation_20260911/`。

## 规范与交接

遵循 ASSET-001、STATE-001/004/006、VAL-003/004；本次没有改变物理资产、状态机或
成功算法，现有规范不需更新。新增语义与验证范围在本记录及索引同步说明。
编译结果仍是来源绑定的 native prototype，不是已完成运行验证的可移植交付包。

EEOS 预测记录为 `configs/research/ebench_evolution_remaining_instruction_hypothesis.json`。
若实测出现差异，只支持当前设置下的指令敏感性；不能单独推断模型内部注意力或记忆原因。
实际 reset 观测中的指令、初态和判据还需与静态配置核对后再解释模型结果。
