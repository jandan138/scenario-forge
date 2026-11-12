# 第二轮修复范围调整：飞书 revision 7210

状态：执行中的范围更新；不是整体交付完成。

用户要求继续执行，同时按最新飞书文档删项和建议修改计划。
本次只读获取第二轮 revision 7210，并成功获取 revision 7173 做历史对照；没有写飞书。

## 当前范围

负责人仍为朱子厚的 task10、11、12、13、18。
必修视频案例从29减到26：task12撤出Pi05 mixed_2、mixed_4、unseen_prospect_2，
只保留OpenWAM mixed_6和unseen_instruction_1的水浴翻出。
旧诊断保留并标记撤项，不作为已修复；不再新增仅服务于撤项的实验。

task13的Pi05 mixed_1新增“盘子表面异常，能看到桌面”说明。
它与暗背景可读性分别验收，检查盘底几何、相对桌面高度、法线/可见性以及材质透明/反射。
这增加同一视频的问题子项，不增加视频案例数。

其他变化：task06新增离心管尖头额外mesh线索，task14新增勺子与白罐穿模怀疑；
task02、14、15、16有撤项，task04、16明确由李欣宇负责。这些不扩入本人的五任务范围。
第一轮已划掉的历史建议不当作本轮新待办恢复。

## 执行计划与证据位置

外部根目录：`/cpfs/user/zhuzihou/dev/scientific-round2-repair-20261026`。

- `control/REPAIR_PLAN_REV7210.md`：完整现行计划。
- `control/current_scope.json`：范围和计划入口。
- `control/active_cases_revision7210.json`：26条当前案例，包含新增托盘子项。
- `control/withdrawn_cases_revision7210.json`：三条撤项及保留政策。
- `control/scope_revision7210.json`：逐行文字/负责人差异、原始XML哈希。
- `control/feishu_round2_revision_7210.json`及`feishu_revision7173_fetch_attempt.json`：成功读取的原始版本证据。

评分修复、USD回调清理、真实动态成功示范与物理坏例修复分别记录。
任务成功路径不能替代坏例修复，撤项不能计为修复成功。
异常后的30步尾录与真正缓存故障快照需按原生执行顺序校准，不能简单按动作数索引判失稳起点。

## 交付约束不变

只交任务YAML、场景USD、task data和指定科学实验metric；本轮不更新LeRobot。
不改GenManip核心、公共机器人资产和原动作，不以冻结或关闭液体反作用制造成功。
测试辅助脚本不成为接收端依赖；不写飞书、不改建通目录、不commit/push。

规范无需变更：本次是任务范围及证据状态更新，没有建立新的通用物理参数或包契约。
继续适用VAL-001/002/003/004/008、STATE-001/002/003及相关材质/液体规则。
