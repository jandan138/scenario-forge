# 2026-09-17 资产生成管线方法论与 skill 接入

规范依据:2026-09-08 规范库基线 + 本变更同步新增的 [GEN-001..007](../standards/asset-generation.md)。
涉及规则:GEN-001、GEN-002、GEN-003、GEN-004、GEN-005、GEN-006、GEN-007;交叉引用 ASSET-001、ASSET-002、ASSET-006、VAL-001、VAL-005。

## 变化

把 IKA OVEN 125 与滴定管两个复杂资产的人工生成流程正式化为半自动 Agent 管线方法论
(A 需求 → B 证据检索 → C 资产规格书 → D skill 驱动生成 → E 现有 ConvertAsset 准入),
只进 skill 与方法论,不含任何管线代码,不改 `src/`、`tests/`、`scripts/`:

- skill `hunyuan-isaac-articulation-assets` 原样解压至 [skills/](../../skills/README.md)(生产者角色工具,
  不被 `src/` 导入,不进任何仓库自动检查)。本地修订 2026-09-17:Hunyuan3D 不可用时允许纯 Blender
  程序化建模回退路线,增加迭代轮次,已标注 `local amendment`,整目录更新时须重打。
- 新规范 [asset-generation.md](../standards/asset-generation.md)(GEN-001..007):证据分级 E/F/D/U、
  规格书完整性、证据与产物不进 Git、生成静态门禁、阶段人工签认、证据类型分层。
- 新模板 [asset-spec-template.md](../standards/templates/asset-spec-template.md)(14 节)。
- 两个种子规格书(对现有参考 docx 的格式转换,未经人工冻结签认,状态 draft):
  [ika-oven-125](../design/asset-specs/ika-oven-125.md)、
  [traditional-titration-burette-and-stand](../design/asset-specs/traditional-titration-burette-and-stand.md)。
- 设计文档 [agent-driven-asset-generation-pipeline](../design/agent-driven-asset-generation-pipeline.md)
  与操作手册 [generate-articulated-asset](../operations/generate-articulated-asset.md)。

## 来源与哈希

- skill 归档 `external_artifacts/incoming/from_xinyu/hunyuan-isaac-articulation-assets.7z`
  SHA-256 `d112b48cb2d5a855d313af51f13a23376548f9521ae915ba624ce233a0ea59cb`;`7z t` 通过;
  解压文件哈希与 provenance 见 `external_artifacts/incoming/from_xinyu/provenance.json`。
- 参考文档 `IKA_OVEN_125_reference.docx`
  SHA-256 `c4338164e43123d09102865b295cd5ab04dd238aa186a373d92ae7362562ec21`;
  `Traditional_Titration_Burette_and_Stand_Asset_Reference.docx`
  SHA-256 `49b697f42cc9b61c26649cab50b2eb8f720e7e6d0931090bb4f825f7547bf126`。原件保持不可变。
- 证据图片:`external_artifacts/asset_evidence/ika-oven-125/`(18 张,catalog digest
  `90d6b591634617264285de3e813ca01238effaf1521061cfcebe961a6f0a2886`)、
  `external_artifacts/asset_evidence/traditional-titration-burette-and-stand/`(20 张,catalog digest
  `68af1981b7c07a446fc19d2e60faabf1ac5f2e42344b7385112a7c15438f7e65`);逐图哈希见各目录 `MANIFEST.sha256`。

## 验证

- `7z t` 归档完整性通过;解压文件清单与归档一致(8 文件 4 目录)。
- `git check-ignore -v` 确认证据图片被 `external_artifacts/*` 规则覆盖;无图片/USD/docx 进入 Git。
- `make check` 保持绿(纯文档与 skill 落位变更;`src/`、`tests/`、`scripts/` 零改动)。
- pytest 收集范围(`testpaths = ["tests"]`)不覆盖 skill 内测试;ruff 目标(`src tests scripts`)不含 `skills/`。
- 规范同步:`GEN` 前缀已注册进 [maintenance.md](../standards/maintenance.md);
  [standards README](../standards/README.md) 阅读地图与变更记录已更新;
  [asset-intake](../standards/asset-intake.md) ASSET-006 已加交叉引用。

## 限制或例外

- 管线尚未按 GEN 规则端到端执行过;GEN 规则重申已有硬边界与 skill 自身契约,
  不宣称该管线能产出合格资产。已验证案例表不增加行。
- 两个种子规格书是文档格式转换,不构成生成资产已合格的证据;其中图片 ID 到提取文件的映射
  为顺序映射,标注"待人工核对"。
- skill 的静态门禁脚本需要 Isaac Kit Python,本记录未执行该门禁;资产的运行时资格仍归
  ConvertAsset 准入路径。

## 同步内容

同一变更内更新:[maintenance.md](../standards/maintenance.md) 前缀注册、
[standards README](../standards/README.md)、[asset-intake.md](../standards/asset-intake.md)、
[architecture.md](../design/architecture.md) 外部工具边界段、
[AGENTS.md](../../AGENTS.md) Directory Ownership、[external_artifacts README](../../external_artifacts/README.md)
三条索引、[docs/index.md](../index.md)。
