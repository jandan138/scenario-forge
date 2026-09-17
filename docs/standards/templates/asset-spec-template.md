# 资产规格书模板(Asset Spec Template)

> 用法:复制本模板为 `docs/design/asset-specs/<asset-slug>.md`,逐节填写。
> 规则约束见 [GEN-002](../asset-generation.md#gen-002)(证据分级)、
> [GEN-003](../asset-generation.md#gen-003)(完整性)、[GEN-004](../asset-generation.md#gen-004)(证据与产物不进 Git)。
> 一份规格书可覆盖多个资产(见第 5 节)。尖括号 `<...>` 为占位符。

## 0. Front matter

| 字段 | 值 |
|---|---|
| asset slug | `<kebab-case-slug>` |
| 规格书版本 | `<vX.Y>` |
| 状态 | `draft` / `frozen`(冻结需人工签认,见 GEN-006) |
| 日期 | `<YYYY-MM-DD>` |
| 作者/Agent | `<who>` |
| 来源文档 | `<repo 相对路径>`,SHA-256 `<hash>`(无源文档时写"无,按 GEN-002 证据登记") |
| 生成工具链 | `<skill 名称/版本>`,source_route: `hunyuan` / `blender_procedural` |

## 1. 型号身份与使用边界(Model identity & usage boundary)

- 型号与厂商依据:`<manufacturer, model, catalog page>`
- 关键识别特征:`<区别于同族型号的特征,以及禁止照抄的特征>`
- 使用边界:`<本规格书支撑的用途;明确不支撑的用途>`

## 2. 证据等级与建模纪律(Evidence grading)

等级定义:E = 精确(官方规格/实物测量);F = 同族(同系列/同类产品);D = 推导(写明依据);U = 未知。

- **禁止从照片像素推导尺寸**;交互相关尺寸必须实测或标 U。
- 本规格书的逐字段归属表:

| 字段 | 取值 | 等级 | 来源(图片/文档编号) |
|---|---|---|---|
| `<field>` | `<value>` | E/F/D/U | `<E01 / datasheet p.3 / ...>` |

## 3. 厂商规格冻结表(Frozen manufacturer spec)

冻结值在生成迭代中不可漂移;变更需重新签认。

| 参数 | 值 | 单位 | 等级 | 来源 |
|---|---|---|---|---|
| `<e.g. 外形尺寸>` | `<value>` | mm | E | `<source>` |

## 4. 资产拆分决策(Decomposition)

哪些是独立资产、哪些是关节、哪些是静态子部件,以及理由。
多资产时写明装配契约(如 mount_frame 对齐关系):

| 单元 | 形态 | 理由 |
|---|---|---|
| `<part>` | 独立资产 / 关节 link / 静态子部件 / 组合场景 | `<why>` |

## 5. USD prim 树(Prim hierarchy)

命名与坐标约定下的建议 prim 结构:

```text
/World/<AssetId>            (default prim, kind=component)
├── Links/Base
├── Links/<LinkName>
├── Joints/<JointName>
└── Collision/...
```

## 6. 关节契约(Joint contracts)

| 关节 | 类型 | 限位 | 驱动/阻尼 | 初始状态 | 状态输出 |
|---|---|---|---|---|---|
| `<joint>` | revolute/prismatic/fixed | `<range>` | `<drive/damping>` | `<initial>` | `<angle, velocity, open_fraction, ...>` |

## 7. 建议状态量(State variables)

供评测/任务逻辑使用的推荐状态变量及阈值:

| 状态量 | 类型 | 阈值/语义 |
|---|---|---|
| `<e.g. door_angle>` | float | `<threshold semantics>` |

## 8. 交互语义(Interaction semantics)

分阶段机器人操作语义,每阶段带成功判据:

| 阶段 | 动作 | 成功判据 |
|---|---|---|
| approach / grasp / actuate / release | `<description>` | `<criterion>` |

## 9. 验证矩阵与失败模式(QA matrix & failure modes)

未执行的项标 `NOT_TESTED`;无真实运行时的静态结果标 `static_audit_only`(GEN-007)。

| 检查 | 类型(static/reopen/runtime/robot) | 结果 |
|---|---|---|
| `<check>` | `<type>` | `NOT_TESTED` |

高概率失败模式:`<list, from experience or skill references>`

## 10. 交付与命名规范(Delivery conventions)

- 文件命名:`<convention>`
- 坐标/单位/轴向:`<convention, 与 USD-001 一致>`
- 打包形式:`<entrypoint, closure expectation>`

## 11. 待测清单(Open measurements)

所有 U 级字段及首轮建模前后必须实测的项:

| 项 | 等级 | 计划如何获得 |
|---|---|---|
| `<item>` | U | `<measure / request / ...>` |

## 12. 图片清单(Image inventory)

图片只存 `external_artifacts/asset_evidence/<slug>/`(GEN-004):

| 图片 ID | 等级 | 来源 | 使用边界 | 相对路径 | SHA-256 |
|---|---|---|---|---|---|
| `<E01>` | E | `<url/doc>` | `<usage boundary>` | `external_artifacts/asset_evidence/<slug>/<file>` | `<hash>` |

## 13. 来源与许可(Sources & licensing)

- 来源登记:`<manufacturer pages, manuals, videos; 各自用途边界>`
- 许可提醒:`<brand/trademark constraints, de-branding needs, redistributability>`
