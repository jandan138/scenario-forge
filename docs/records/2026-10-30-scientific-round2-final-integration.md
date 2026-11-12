# 科学实验 Round2 最终联合集成

日期：2026-10-30。状态：已推送；限定范围验收完成。

## 提交拓扑

`feature/scientific_experiments` 在 `d64a80ae` 后仅新增一次提交：`97ae5e98dbc0a98cee49c289b60f3590c22284fe feat(scientific): integrate round2 validation and asset updates`。该提交由 non-bath R2 `a523e0a2`、Lift2 隔离 `73066ae3` 和水浴正常保底版的内容组成，已 fast-forward 并 push 一次；本地与远端引用一致。原 evaluation/delivery 分支保留作审计，未重写历史或强推。

## 内容与 saved 边界

最终971个 tracked 文件包含所需代码、963份科学实验 YAML 和水浴 metric。Lift2 路径迁移覆盖1926条解析后机器人配置；76份水浴 YAML 移除新增 `usd_path` 后逐字节还原水浴版本，其他887份与 Lift2 候选一致。

建通现存 saved 作为同事基线。水浴546个文件中406个新增、140个与制作基线完全一致的文件备份后替换；Lift2新增12个文件。其他 saved 字节未改。最终16357个源 saved 文件全部复验通过，54个 `saved/assets/mesh_data` 新文件只归类为运行缓存，保留供证据引用，不属于源包或 Git 内容（ASSET-002、VAL-005）。

## 验证

- 37项 unit、Black、静态变更 allowlist、YAML/资产闭包通过。
- Lift2 P2：3604步，score 1.0、SR1，原始输入前缀一致、杯体16/1、无 guarded invalid state；独立关键帧视觉 PASS。
- 水浴正常操作8项均通过详细原生审计：动作及尾帧、120Hz逐步观测、923粒样液、固定烧杯与透明无碰撞假浴水、四路视频、RRD、缓存及输入哈希。
- 两项独立安装使用实际私有代码/config/taskdata/metric/受影响资产副本和原生接收入口，无观察器或外部工具 worker 路径；source/media/RRD/cache/log 验收通过。
- 目视复核无黄格、缺资产、飞瓶或甩臂；最终落架和反应细节受遮挡/曝光限制，完成依据使用 native 接触与反应记录（VAL-001、VAL-003、VAL-004、VAL-008）。

## 交付与限制

联合包：`/mnt/data/zhuzihou/GenManip-Sim-deliveries/releases/scientific-round2-final-r1-20261030.tar.gz`，SHA-256 `99959fa06a90aa84bb17418396a221ce47c618eae896c7812171a1fb76cae0da`。`ACTIVE_DELIVERY.json` 已指向该提交，旧 R2 归档保留。

水浴仅为正常操作保底版：快动作闭壁漏液、接触报告错误、init40和热切换未合格，不宣称完整修复。完整 bad/init/hot 资格不在本次提交范围内。

本次应用既有 ASSET/VAL 规则，没有形成新的通用场景标准，因此未修改 `docs/standards`。
