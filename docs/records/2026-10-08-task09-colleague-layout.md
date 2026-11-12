# 2026-10-08：task_09 按同事目录样式发布

## 位置与内容

用户要求的 `/shared/smartbot_new/chenjiantong/scene_usd` 在本机映射为
`/mnt/data/chenjiantong/scene_usd`。发布到：

```text
/mnt/data/chenjiantong/scene_usd/zzh_fixed/task_09_solid_weighing/
├── scene.usd                 # Isaac 4.1，二进制 USDC 0.8
├── scene_isaac45.usda        # Isaac 4.5，同目录兼容覆盖入口
└── SubUSDs/
    ├── materials/           # isaac41、isaac45 下按 task09、task14 保留完整 MDL 树
    └── textures/
```

共享目录只有两个场景入口及资源，无 README、视频、仓库包骨架或验证环境。
原始 task_09、task_14 和已交付任务包未修改。视频与完整原交付仍位于
`outputs/task09_solid_weighing_r1_20261008/handoff/`。

## 导出行为

唯一来源为已验证的 `scientific_workbench_solid_weighing_task09_r1`。
默认入口按 USD 组合结果展开；4.5 入口只覆盖节点类型及版本相关 MDL 引用。
复用已收集的生产者材料闭包，模块及纹理按字节复制，无材质／网格转换或物理重调。
五颗质量总计仍为 4.558739893 g，显示 4.56 g，保留去皮、支持图计重和完成条件。

原独立 `runtime41/45.usda` 入口没有 authored 单位／轴向，单独读取会得到 USD 默认 0.01 m、Y。
新入口显式使用原主场景和实际验证环境的 1 m、Z、1 kg；不将缺省元数据冒充已验证配置。
匿名源组合层完成该设置，不向原文件写入。根与 defaultPrim 都是 `/World`。
没有添加 PhysicsScene、灯光、背景或机器人。

USD 标准 Flatten 略去一个原本 inactive 的 `/World/obj_graduated_cylinder`；
它不在原有效物理／可见场景中。映射报告明确记录此项，所有活动对象的属性、连接、
关系、API schema、时间采样、插值、变换、质量和脚本文本均做等价检查。
资源路径通过实际文件 SHA 比较，允许目录迁移但不允许更换资源内容。

导出工具为 `scripts/export_task09_colleague_layout.py`。拒绝覆盖现有输出目录，
使用目标父目录下的暂存副本，检查全文件 SHA 后再重命名发布；没有新增核心 schema/API。

## 证据与边界

证据根：`outputs/task09_colleague_layout_20261008/validated/`。

- `export.json`：来源、版本差异覆盖、路径映射及全部 71 个文件的 SHA。
- `run41/report.json`、`run45/report.json`：两个导出入口各自完整运行通过，含去皮、五颗、
  逐颗卸载、负皮重、重置、悬空反例和静置／释放稳定性；没有只用旧包报告替代。
- `publication_receipt.json`：实际目标目录、全部文件哈希及发布后检查结果。
- `runtime_fixture`：仓库中的私有验证包装，含 PhysicsScene 和验证器所需文件名别名。
  其中场景／资源字节与发布目录一致；这些包装文件没有复制到共享目录。
- `make-check.log`：本次仓库全量检查输出。

检查结果：导出定向测试 3 项通过；`make check` 为 1221 passed、1 skipped，
Ruff、package smoke、Phase 10.x smoke 和 diff 检查全部通过。发布后逐文件复核 71 个 SHA 一致，
原任务包场景及其 ZIP 的哈希也保持原交付收据中的值。

发布前后以及移到目标父目录的暂存副本后，两个入口均无缺失或目录之外的依赖。
4.1 入口只有一层；4.5 入口只有覆盖层与同目录主场景两层。
原有 PathTracing 视觉证据按几何、材质、纹理字节等价复用；本次没有改外观或重新制作视频。
仍不宣称独立受力计量、机器人操作或实时渲染器的盐材质颜色资格，详见上一份称量记录。

规范依据：`90295bcb6d17fe0061e300d3a5f47ac15763cf25` 基线下的 ASSET-001/002、
USD-002、STATE-001/002/005、VAL-001/002/003/005/006/007 与维护流程。
规范无需变更：本次只改变交付布局与显式入口元数据，没有新增通用场景制作规则。
操作指南同步共享位置；历史任务包和已有交付哈希保持原样。
