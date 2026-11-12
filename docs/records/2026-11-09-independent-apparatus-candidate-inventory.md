# 独立实验器材候选盘点（未完成交付）

目标目录：`/mnt/data/zhuzihou/assets/scientific_apparatus_usd_v1/`。

本轮从接收仓库20个任务族的 `seen_scene_1/scene.usd` 提取92份候选，覆盖用户指定27类。输出仅在 `candidates/`，`catalog.json` 的合格集合为空，默认入口未指定。不是正式可用发布。

`reports/candidate_inventory.json` 记录源/输出哈希与依赖根；`reports/static_audit.json` 记录两份粉末瓶悬空 PhysicsScene 关系及三份候选未解析 OmniGlass 模块。无源资产修改。

Isaac4.1 启动探索未形成有效验收证据，已主动终止；不得把 app.update 次数解释为物理步数。下一阶段须先补实际任务配置、初态、粒子归属与合格测试夹具，再做闭包迁移、预览和物理检查；还需全入口盘点与变体去重。现有脚本仅是候选探索工具。

依据 ASSET-002/003/004、USD-001/002、VAL-001/002/003/004/005。规范无需变更：未建立新规则，也未扩大原交付资格。未改核心代码，未运行 make check；新增正式提取工具前应补失败测试并按仓库流程检查。
