# 水浴：碰壁不再阻断加热

2026-10-15，用户明确提出取消“试管碰到烧杯就停表”。这是任务规则变更，不是对旧失败结果的重新评分，也不证明液体或回架已经修好。

适用规则：STATE-001/002/003/006、VAL-002/008。规范无需变更：碰壁是否允许继续受热属于此任务的操作语义，不是通用场景标准。包/API/design 合同未变；同步了水浴操作说明，历史资产和报告保持原样。

独立候选由 timing-v2 复制，20 个场景入口的嵌入控制器只删除 heating_gate 中 wall_contacts 导致拒绝的分支。保留碰壁遥测、入水判定、液体有效性、姿态/承托条件、真实物理步累计、离水暂停和重置。接触查询若发生运行错误仍显式报错，未悄悄忽略引擎异常。

全部脚本及运行证据在个人目录：
`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/task12_liquid_color_20261012/`。
新增 `tools/test_task12_wall_policy.py` 从实际 USD 抽取函数，验证碰壁仍加热、干态碰壁不加热，并复用累计/重复渲染/暂停/重置/呈现检查。旧候选先跑出现一个预期失败，见 `evidence/wall_policy_red.log`。旧测试保留。

候选制作第一次误匹配 repair_core/scene.usda，因其无场景入口路径而停止；未启动仿真。限制为 seen/unseen 场景入口后以新目录重建，未覆盖失败目录。

候选身份与哈希：`evidence/wall_policy_native_identity.json`。GPU 诊断会在独立 metric 追加只读观察代码，正式评分代码不合入该观察器；最终必须另用干净 metric 验收。全量成功、保液、回架和独立安装资格仍待完成，规则测试不能替代这些证据。

本次 CPU 验证：11 项通过（`evidence/wall_policy_green.log`）。远端已启动 `wall_policy_h13_a`，使用校准后的 case13 原动作；GPU 结果尚待产出。

静态语义审计通过：20 个场景逐层恢复原控制器文本后与来源完全一致，证明场景层仅改变该脚本；候选继承的其它文件由身份哈希约束。另已审计 solver-only 诊断的 51 份 YAML：204 个值仅为迭代范围 64/128→1/255，没有其它 YAML 语义变化。见 `evidence/wall_and_solver_semantic_audit.json`。

串行队列 `evidence/wall_then_solver_queue.json` 等待当前回放完整结束并验收后，分析其位姿，再启动 solver-only 对照。该对照故意保留历史加热规则以隔离物理参数；不代表恢复旧交付规则。任一前置异常即停队列，不重启旧任务。启动后已验证当前回放进入动作执行阶段（至少171帧）。
