# 2026-09-12 EBench COM／惯性分项任务

复用现有编译器与两个新生产者 overlay，未新增消费者物理修改逻辑。
配置为 `configs/research/ebench_dish_component_com.json` 和
`configs/research/ebench_dish_component_tensor.json`，已编译并注册独立任务前缀。
每个 suite 沿用四 cell 结构；研究当前只使用两个 wide/preplaced 条件，不把八个
编译配置误报成八次实验。

EEOS 对最终入口进行实际静态比较：分别只有 COM 或对角惯性变化，任务数据相同。
对应审计在 `outputs/ebench_evolution/inertia_component_preflight_20260912.json`。
EEOS 随后完成两项读回与回放：运行时字段匹配通过，两个 1000 步窗口均未达到
勺子目标。结果范围见 EEOS 的同日分项记录，不提升为在线模型分数或资产完整资格。

ASSET-001/002/003、VAL-003/004 的职责与资格范围保持不变，通用规范无需修改。
新任务仍是来源绑定的诊断 prototype，不作为完整可移植包交付。
