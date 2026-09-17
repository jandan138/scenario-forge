# 资产生成规范

状态：当前。适用范围：由 Agent 驱动的关节/复杂资产**生产**阶段(需求 → 证据 → 资产规格书 →
迭代生成),以及生产结果移交现有 ConvertAsset 准入管线的边界。
不覆盖:ConvertAsset 内部的转换与资格化(归 [资产接入](asset-intake.md))、场景组装与任务制作。

## 强制要求

<a id="gen-001"></a>
### GEN-001 — 生成是生产者角色,仓库只拥有契约

关节/复杂资产的生成由 Agent 使用外部 skill(如 `skills/hunyuan-isaac-articulation-assets/`)
在生产者角色下完成;Scenario Forge 只拥有各阶段的输入/输出契约:资产规格书格式、证据与哈希策略、
准入请求。`skills/` 下的工具不被 `src/` 导入,不进入任何仓库自动检查;纯包层不得导入模拟器 SDK。
skill 的存在不构成任何资产的资格;生成资产只能经过现有 ConvertAsset 准入边界进入场景。
依据:[项目边界](../../AGENTS.md)、[边界测试](../../tests/test_architecture_boundaries.py)、
[ASSET-001](asset-intake.md#asset-001)、[skills/README](../../skills/README.md)。

<a id="gen-002"></a>
### GEN-002 — 证据分级与逐字段归属

资产规格书中的每个声明必须带证据等级与来源:E(精确,官方规格/实物测量)、F(同族,
同系列或同类产品)、D(推导,有写明依据的工程推导)、U(未知)。
**禁止从照片像素推导尺寸**;交互相关尺寸(手柄跨距、轴位、夹持面)必须实测或标 U。
U 级字段进入待测清单,不得静默填充;推导字段必须写明推导依据。
依据:两份证据分级参考文档(索引见 [external_artifacts README](../../external_artifacts/README.md))、
[资产规格书模板](templates/asset-spec-template.md)。

<a id="gen-003"></a>
### GEN-003 — 资产规格书完整性

进入生成阶段前,资产规格书必须完整实例化
[模板](templates/asset-spec-template.md) 的全部章节:型号身份与使用边界、证据分级、厂商规格冻结表、
资产拆分决策、USD prim 树、关节契约、建议状态量、交互语义、验证矩阵与失败模式、交付命名规范、
待测清单、图片清单。一份规格书可以覆盖多个资产(例如滴定管与支架两个资产 + 装配契约),
拆分决策必须说明理由。规格书经人工签认后冻结;生成阶段的规格变更必须重新签认。
依据:[模板](templates/asset-spec-template.md)、
[生成管线设计](../design/agent-driven-asset-generation-pipeline.md)。

<a id="gen-004"></a>
### GEN-004 — 证据与产物不进 Git

证据图片、参考 docx 原件、原始与生成的 USD 一律只存于 `external_artifacts/` 下;
提交进 Git 的文档以仓库相对路径引用,并把对应 SHA-256 登记进
[external_artifacts 索引](../../external_artifacts/README.md)。
证据只能放 `external_artifacts/` 子树——部分图片格式不在扩展名忽略规则内,
安全性依赖存放位置而非文件类型。
依据:[VAL-005](validation-and-delivery.md#val-005)、`.gitignore`、
[external_artifacts README](../../external_artifacts/README.md)。

<a id="gen-005"></a>
### GEN-005 — 生成资产静态门禁

向 ConvertAsset 提交准入请求前,生成的 USD 必须在 Isaac Kit Python 下通过 skill 自带的
静态契约检查(如 `skills/hunyuan-isaac-articulation-assets/scripts/check_articulation_usd.py`,
一律用全路径调用,不接进 `make check` 或任何仓库自动检查)。任何 FAIL 阻断交付。
检查报告存于 `external_artifacts/` 并登记哈希。静态通过不代表运行时验收,
不替代 [ASSET-002](asset-intake.md#asset-002) 的资格要求,不得写成"物理/交互已通过"。
依据:skill `references/validation-and-acceptance.md` 的静态/运行时分层、
[ASSET-002](asset-intake.md#asset-002)。

## 推荐做法

<a id="gen-006"></a>
### GEN-006 — 阶段人工签认

半自动流水线中,Agent 在单个阶段内自主执行,阶段之间设人工签认点:
A(需求清单确认)、C(规格书签认 = 冻结)、D(静态门禁报告复核)。
签认不新增审批系统,由任务记录中的签认说明承担。
依据:[生成管线设计](../design/agent-driven-asset-generation-pipeline.md) 的阶段门禁表。

<a id="gen-007"></a>
### GEN-007 — 区分静态、重开与运行时证据

生成阶段的验证结论必须标明证据类型:静态契约检查、重开/渲染检查、PhysX 运行时回放、
机器人接触验证,四者不互相替代。无真实运行时执行的结果标 `static_audit_only`;
未执行的检查项标 `NOT_TESTED`,不得留空或写成通过。
依据:skill `references/validation-and-acceptance.md`、
[VAL-001](validation-and-delivery.md#val-001) 的证据范围纪律。

## 已知限制与变更记录

本页规则重申已有硬边界(Git 策略、生产者/消费者职责、哈希纪律)与 skill 自身契约,
不宣称该管线能产出合格资产;管线尚未按本页规则端到端执行过。
两个种子规格书(IKA 烘箱、滴定管)是对已有参考文档的格式转换,不构成生成资产已合格的证据;
已验证案例表不因此增加行。

变更记录:2026-09-17 建立资产生成主题,落地 skill 与 A–E 阶段方法论;
同步 [maintenance](maintenance.md) 前缀注册与 [资产接入](asset-intake.md) 交叉引用。
