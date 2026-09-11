# 2026-09-12 EBench 互补惯性诊断任务

复用现有 native intervention 编译器，新增配置
`configs/research/ebench_dish_reverse_inertia.json`，消费 ConvertAsset 的 control
几何／wide 惯性 overlay。没有在消费者中修改物理属性或引入模型执行器。

输出为 `outputs/ebench_dish_reverse_inertia_20260912_r1/`，四个任务已注册至
GenManip 的独立 `dish_reverse_inertia_r1_*` 名称空间；当前只使用 control/preplaced
进行互补诊断，不把编译数量当成评测数量。

实际静态场景比较确认相对旧 control/preplaced 只改变勺子的 COM 与对角惯性，
`task_data` 完全一致。EEOS 已完成新条件读回并进入回放；最终结果仍待解释。
源与产物哈希保存在 suite/build/installation 记录及 EEOS 的 reverse inertia preflight。

本次仅使用既有编译功能与新配置，通用规范无需变化。遵循 ASSET-001/002/003 和
VAL-003/004，区分参数读回、回放窗口结果与可移植交付资格，不改写旧任务。

## Git 收尾复核

此配置在全工作树收尾期间新增，作为独立补充批次处理。复用已提交编译器在临时目录
重新编译四个入口，USD加载和临时注册均通过，每个入口2886个 prim，且均有预期勺子节点。
本次静态复核不执行下游模型或重写原注册，编译记录仍为 `compiled_not_runtime_verified`。
配置 SHA256：`885a0822b56d82559be8e15d95c027e3a0a24daf861f59e90045432fa75218d4`。
日志：`outputs/worktree_closeout_20260911/reverse_inertia_build_check.log`。
