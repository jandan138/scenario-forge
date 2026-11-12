# 科学实验 Round2 最终联合交付

## 当前入口

- 分支：`feature/scientific_experiments`
- 当前接收与远端代码：`8bb1df4355a0bf1afeba506304e1c7a23425eacb`（validation对齐与请求追踪兼容修复均已交付）。
- 当前交付记录：[2026-11-05 validation对齐交付](../records/2026-11-05-validation-alignment-delivery.md)，含28份初始化数据安装与回滚清单。
- 联合交付基线：`97ae5e98dbc0a98cee49c289b60f3590c22284fe`；下列联合包为该基线归档，task09后续增量见本页后续记录。
- 联合目录：`/mnt/data/zhuzihou/GenManip-Sim-deliveries/releases/scientific-round2-final-r1-20261030/`
- 联合包：`/mnt/data/zhuzihou/GenManip-Sim-deliveries/releases/scientific-round2-final-r1-20261030.tar.gz`
- 包 SHA-256：`99959fa06a90aa84bb17418396a221ce47c618eae896c7812171a1fb76cae0da`
- 构建与验证证据：`/cpfs/user/zhuzihou/dev/scientific-round2-final-integration-20261030/`
- 活动入口：`/cpfs/user/zhuzihou/dev/scientific-round2-delivery-validation-20261029/ACTIVE_DELIVERY.json`

## 验收范围

37项 unit 通过；963份科学实验 YAML、1926条机器人路径正确。水浴正常8项和两项独立安装均通过原生动作、反应、媒体、RRD、缓存和日志审计。task11 P2 为3604步、score 1.0、SR1，输入前缀不变且关键帧通过。

16357个源 saved 文件哈希已复核。54个 `mesh_data` 文件属于运行缓存，不能误计入源资产或同事改动。212个被替换文件的安装前备份位于 `/cpfs/user/zhuzihou/dev/scientific-round2-final-integration-20261030/receiver_backup/`。

## 不变边界

- 目标分支在 `d64a80ae` 后只有一次提交，本地和远端一致；未 rebase、未强推。
- 同事既有 saved 除水浴546个和 Lift2 12个白名单路径外未改。
- 水浴是正常操作保底版，不包含完整 bad、init40 或热切换资格。
- 快动作漏液、接触报告错误和视觉遮挡/曝光限制均保留，不能改写成完整物理修复或逐帧零穿透证明。

本次仅应用现有 ASSET/VAL 规则，未修改通用 standards。

## 后续原生冒烟

task11/task12 原装回放和同 worker 连续两回合均通过；第二 seed 使用相同000 task data 的001测试夹具。20个任务族初始化中19个直接通过，task09 的测试映射通过。证据位于 `/cpfs/user/zhuzihou/dev/delivery-native-smoke-20261030/`。

后续已正式修复 task09 配置：`40ebb02006f5565f93762278b569e570668bb2b8` 将8份 validation YAML 的两处 `Chassis: Chassis` 均改为 `Chassis: Body`，并 push。全部8个 validation 完整回放通过，视频完整；实际分数为3个1分，以及0.6、0.3、0.3、0.7、0.3，未把完整运行写成全部满分。交付包为 `/mnt/data/zhuzihou/GenManip-Sim-deliveries/releases/task09-validation-fix-r1-20261031.tar.gz`，SHA-256 `6706ead88c0f8efd5c4e3be79e32529df64acd1a1295aef94713cce7b8f93314`。

## 2026-11-04 validation 与最终 test 对齐候选

已发现共享USD之外的加载配置、goal与初始化恢复漏同步，正在独立目录修复和验证；参见[对齐记录](../records/2026-11-04-validation-test-alignment.md)。当前接收版本仍为40ebb020，候选未安装。10月30日smoke中的task09配置故障是历史结果，已被10月31日修复记录替代；不可将旧smoke字段作为当前未修复结论。

2026-11-05：validation对齐候选的28例回放、112路视频解码、原动作一致性和关键帧收尾检查完成，限制见对应记录及外部CLOSEOUT.json。候选提交478874d1与reviewed-r2增量包仍未安装/推送；当前接收入口不变。远端认证需恢复，接收目录新增task07未提交修改须保留。

2026-11-05最终状态：实际安装、四类原生reset与远端push回读均已完成。前述“认证缺失、尚未安装”的段落属于历史准备阶段，已由本页当前入口和最终交付记录替代。
