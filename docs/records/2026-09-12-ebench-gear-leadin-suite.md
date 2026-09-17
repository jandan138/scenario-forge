# 2026-09-12 EBench 齿轮入齿几何配对任务

EEOS 从原齿轮轨迹与邻齿碰撞诊断提出下缘引导几何。ConvertAsset 已用 Blender
生成原尺寸对照与 2 mm 退让变体，并写入同一原始齿轮运行时惯性参照。
本仓库负责保持原任务语义并接入这两份生产者资产，不实现几何转换或模型执行。

## 编译变化

`intervention_suite.compile_suite` 新增 `ebench-native-scene-variants-build/v1`
输入分支：仅生成 `full` 条件，完整保留原 `task_data`，不调用 dish 预放置逻辑。
必须声明 `task_prefix`、`base_default_prim`，以及含 `control` 的生产者变体集合。
复用现有输出结构、哈希检查和禁止覆盖的安装器；原四条件 dish 行为保持原样。

先新增非 dish fixture 测试，确认旧实现因未知 schema 失败；实现后共五项适配器
测试通过，Ruff 通过。完整 `make check` 已启动，其终态以 EEOS 保存的验证日志为准：
`outputs/ebench_evolution/validation_20260912/scenario_forge_gear.log`。

## 实际产物

输入：EEOS `configs/research/ebench_evolution_gear_leadin_suite.json`。
输出：`outputs/ebench_gear_leadin_r3_20260912/`，包含两项任务：

- `eeos_evolution/gear_leadin_r3_control_full`
- `eeos_evolution/gear_leadin_r3_leadin_full`

已通过脚本编译并注册到 `/cpfs/shared/simulation/zhuzihou/dev/GenManip`，没有覆盖
旧任务。EEOS 使用 USD 检查最终组合后的 `/World/_scene/obj_04`，确认质量、重心、
惯性声明一致，且没有继承前次诊断的碰撞过滤关系。运行时质量读回正在依次进行；
这些编译结果尚未声明通过动态、渲染或策略评测。

后续 EEOS 已完成两个 reset：实际 PhysX 质量、重心和惯性矩阵都与同一原始参照
精确一致，实际源层哈希匹配各条件生产者层。结果见 EEOS
`outputs/ebench_evolution/gear_leadin_mass_comparison_20260912.json`。
原尺寸对照回放已启动；本项质量读回不替代策略或完整场景渲染验证。

完整 `make check` 后续正常结束：1007 passed、1 skipped（312.35 s），lint、
package smoke、phase10x smoke 和 diff check 均通过。

EEOS 随后发现原尺寸对照已改变原固定动作结果。为分离网格处理与显式惯性写入，
复用本入口编译并注册 `outputs/ebench_gear_native_mass_r1_20260912/` 的两条件：
`gear_native_mass_r1_control_full` 与 `gear_native_mass_r1_mass_authored_full`。
后者来自 ConvertAsset 的原网格质量属性叠加层，未修改网格；运行检查尚待执行。
本次仅新增配置产物，没有再更改编译代码或通用规范。

## 规范与交接

适用 ASSET-001/002/003、USD-001/002、STATE-001/004/006、VAL-002/003/004。
按维护流程同步原生适配器设计文档及本记录。规范无需变更：新增的是局部原生编译
入口，资产资格、运行范围、来源绑定和角色边界未变。产物仍依赖外部源路径，不能
按可移植包交付。后续物理属性核对、实际帧检查及配对回放由 EEOS 执行。
