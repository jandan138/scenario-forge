# 第二轮湿实验修复：续执行与证据边界

范围沿用飞书 revision7210：朱子厚负责 task10/11/12/13/18 的26例。
本记录不表示正式交付，不修改飞书、建通目录、核心评测代码或公共机器人资产；本轮不更新 LeRobot。

## 本轮核对

- task10 两条异常：用户没有历史启动/版本资料，接受保留未复现。不得标为已经修复。
- task11 评分 r2：复核 ZIP CRC、payload/rollback 哈希及原始证据；2个 metric、40个 metadata，41个原文件回滚及新增 helper 的受保护删除。坏例两次0.8/SR0、正例两次1/SR1；包不含失败的物理候选。
- task11 腕部20Nm候选：改善交接挤压，但正常正例降为0.4，关门失败，右腕 joint5 同帧误差约1.80rad。候选不交付，不继续扫力矩。
- task12 试管质量2倍：完整7000步仍在脱手后翻出。负责人复核视频90秒在杯内、100秒已在桌面；不能以短窗口留杯宣称修复。停止继续加重。
- task12/task18 的27g正例：各0.85，已显色，但最终横躺管架，属于回架未完成，不是完整成功。
- task13 新示范生成：4856步、1分/SR1，真染液1476颗；保存实际解析后的关节命令。独立关节回放5500步为0.95/SR0，反应链通过，量筒直立项失败。主助手亲看第2000帧量筒已横倒、末段仍横倒；没有据此确定倒下的物理根因。

task13 独立关节回放没有反馈策略/位姿观察器，但使用外部回放客户端。
其 receipt 明记 `standard_client_unmodified=false` 和 `acceptance_eligible=false`。
它不能替代原装 LMDB 客户端的独立安装验收；后者需完成可移植文件闭包及动作语义核对后另行验证。

## 证据与后续

外部记录根目录：`/cpfs/user/zhuzihou/dev/scientific-round2-repair-20261026`。

- `control/CONTINUATION_20261027.md`：本轮分工、主机检查与边界。
- `control/root_blue_baked_visual_review.json`：主助手截图复核及图像哈希。
- `tray_contact/evidence/metric_r2_closeout_recheck_20261027.json`：评分包复核。
- `tray_contact/TASK11_SCOPE26_DELIVERY_STATUS.md`：评分和物理问题分别列状态。
- `blue/reports/feedback_r2_success.json`：示范生成结果；其中历史“待回放”字段不能代替后续回放 receipt。
- `blue/evidence/runs/blue_baked_feedback_r2_20261026T145411_591105Z/receipt.json`：独立关节回放真实结果与资格限制。

后续优先完成蓝瓶组件和可移植闭包；水浴分析脱手后翻出临界窗口，不重复质量扫描；夹爪接触结合实际驱动/约束和双臂目标兼容性做机制诊断。没有有效新假设不重复长回放。

规范依据为当前验证与交付规则 VAL-002、VAL-008 及维护流程。规范无需变更：这里记录特定运行时、特定候选的结果和证据边界，不形成通用质量、力矩、offset或PBD默认值。未改变包、schema或适配器契约，因此无对应设计/API变更；实验工具继续保存在仓库核心之外。
