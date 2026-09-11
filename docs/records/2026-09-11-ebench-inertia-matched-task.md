# 2026-09-11 EBench 惯性匹配诊断任务

## 目的与产物

EEOS 的交叉回放需要区分几何与惯性效应。ConvertAsset 已提供保持加宽几何、
使用控制组显式惯性参数的新 overlay；本次仅复用既有 native intervention 编译器，
不在 Scenario Forge 内修改资产物理或增加模型运行器。

配置：`configs/research/ebench_dish_inertia_matched.json`。
编译输出：`outputs/ebench_dish_inertia_matched_20260911_r1/`。
四个配置已安装到 GenManip 的 `eeos_evolution/dish_inertia_r1_*` 名称空间。
其中 `wide` 指加宽几何加控制组惯性；不是此前未匹配惯性的 wide 条件。
本次复用四条件编译形状，但后续首先只需要 preplaced 诊断，不意味着要额外运行四次模型。

## 验证

编译与安装均通过。EEOS 使用最终 `.usda` 入口比较旧 wide 与新 matched wide，
全部 prim 路径一致，任务 `task_data` 一致；仅以下属性不同：

- `/World/_scene/obj_spoon.physics:centerOfMass`
- `/World/_scene/obj_spoon.physics:diagonalInertia`

审计结果：EEOS `outputs/ebench_evolution/inertia_matched_scene_audit_20260911.json`。
已有 adapter 测试 2 项通过；全仓 `make check` 已通过：1003 项测试通过、1 项跳过
（341.49 秒），lint、package smoke、Phase 10.x smoke 和 `git diff --check` 均通过。
检查使用 EEOS 项目 Python，日志保留在 `/tmp/sf-inertia-r1-check.log`。
没有修改历史任务、正在运行的配对配置或通用编译器代码。

## 范围与交接

遵循 ASSET-001/002/003、VAL-003/004：此为来源绑定的诊断任务，显式标记
`compiled_not_runtime_verified`，不继承旧资产的运行资格，不作为可移植包交付。
规范无需变更，因为接口与资格规则未改变。本记录及文档索引同步记录新输入和验证范围。

EEOS 已准备 `configs/research/ebench_evolution_replay_wide_control_inertia.json`。
当前 GPU 队列结束后先做原生 reset 质量属性读回，再安排同动作回放；新任务尚未运行，
不宣称惯性匹配已在 PhysX 生效或解释了成功差异。
