# task09 天平 articulation 配置修复

日期：2026-10-31。状态：已提交并 push；8项 validation 完整回放完成。

## 原因与修改

`d64a80ae` 新增的 task09 validation 配置把部件映射写成 `Chassis: Chassis`，但当前20个 USD 场景均只有 `Instance/Body`，导致 reset 的 `Accessed schema on invalid prim`。test 配置此前已在 `f67879b5` 改为 `Chassis: Body`，validation 漏同步。

本次仅修改 task09 的8份 validation YAML，在 demonstration 和 evaluation 两处共16行把 `Chassis: Chassis` 改为 `Chassis: Body`。未改 USD、test 配置、metric 或其他任务。

## 验证与提交

- 8份 YAML 和20个场景命名检查通过；37项 unit 和 Black 通过。
- `mixed_1` 原生 reset 通过。
- 全部8个 validation 原生完整回放完成，四路视频均可解码，无 `invalid prim` 或新增配置错误。
- 结果：unseen_background_2、unseen_instruction_2、unseen_prospect_2 各1分；mixed_1 0.6、mixed_2 0.3、unseen_background_1 0.3、unseen_instruction_1 0.7、unseen_prospect_1 0.3。分数如实保留，不把完整运行写成全部满分。

提交 `40ebb02006f5565f93762278b569e570668bb2b8 fix(task09): align balance articulation paths` 已 push 到 `feature/scientific_experiments`。交付包 `/mnt/data/zhuzihou/GenManip-Sim-deliveries/releases/task09-validation-fix-r1-20261031.tar.gz`，SHA-256 `6706ead88c0f8efd5c4e3be79e32529df64acd1a1295aef94713cce7b8f93314`。

本次是特定配置路径修复，不需要修改通用 standards。
