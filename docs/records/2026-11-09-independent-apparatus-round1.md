# 独立实验器材第一轮改进与基础验收

用户明确将验收改为“每个USD能打开、画面、物理参数看上去没问题”，不再采用原计划的240物理步或完整任务功能门槛。

产物：`/mnt/data/zhuzihou/assets/scientific_apparatus_usd_v1/`。92份候选按属性/依赖内容保守去重为75份，覆盖27类，catalog指定默认版本。接收源未修改。

修改：补MDL模块闭包；两份粉末候选补GPU/PGS/180Hz PhysicsScene，与task14及z5配置一致；五份候选将非法contactOffset改为restOffset+0.1mm，原值/新值在round1_static.json；这是本次用户要求改进下的独立派生版本局部修正，不改变生产者或原交付、不新增通用参数规则。移除天平读数图与绑定和带入的样品；其他任务图停用；灯体不带分离灯帽。新增非物理预览灯光与相机。

验证：75/75 Isaac4.1打开并生成720x640 PNG；75/75独立复制版本目录到临时位置后，USD可打开、defaultPrim有效、关系及显式资产路径可解析且在包内，质量/密度无负值、碰撞contactOffset>restOffset。每份物理参数保存。实现者逐张复核四张最终联系表覆盖的全部预览，细玻璃对比低及蓝反应液偏暗记WARN。初轮渲染清理API误用已修复，最终75份render状态均为rendered。

限制：没有物理运行资格；未声称液体或原任务初态完全恢复；未测螺纹操作；保留源摆放；滴定管和架子仍为组合件。最终天平仅清理自定义balance关系的后续静态修改不改变图像内容，相应静态哈希已刷新。MDL依赖环境仍为Isaac4.1，不声称任意USD查看器材质一致。

证据：外部目录reports/final_static.json、final_render.json、visual_review.json、release_sha256.json与catalog.json。大型USD/图像不进Git。

规范无需变更：本轮仅对这批派生资产执行用户收窄的基础验收，不扩大ASSET-003能力继承或VAL-001证据等级，不将0.1mm间隔提升为全局参数标准。操作入口同步于docs/operations/independent-scientific-apparatus.md。

仓库检查：make check退出码0；1259 passed、1 skipped（549.60秒），ruff、package smoke、phase10x smoke与diff-check通过。另查Shader连接和AssetArray路径无问题；19份实际使用的源场景SHA256均与提取前相同。
