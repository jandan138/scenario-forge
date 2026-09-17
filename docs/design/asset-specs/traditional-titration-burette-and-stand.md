# 资产规格书：传统滴定管与滴定支架(Traditional Titration Burette and Stand)

> 本规格书由现有参考文档《传统滴定系统资产生成参考》(Robotic Lab Asset Reference v1.0)
> 按 [资产规格书模板](../../standards/templates/asset-spec-template.md) 全 14 节转换而来,
> 覆盖 **burette.usd** 与 **burette_stand.usd** 两个交付资产及
> **titration_station_test.usd** 组合测试场景(见第 4 节装配契约)。
> 规则约束见 [GEN-002](../../standards/asset-generation.md#gen-002)(证据分级)、
> [GEN-003](../../standards/asset-generation.md#gen-003)(完整性)、
> [GEN-004](../../standards/asset-generation.md#gen-004)(证据与产物不进 Git)。

![文档封面图(D,顺序映射待人工核对)](../../../external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image1.png)

## 0. Front matter

| 字段 | 值 |
|---|---|
| asset slug | `traditional-titration-burette-and-stand` |
| 规格书版本 | `v1.0` |
| 状态 | `draft`(转换自现有参考文档,未经人工冻结签认;冻结需人工签认,见 GEN-006) |
| 日期 | 2026-09-17 |
| 作者/Agent | Claude Code(格式转换 Agent;内容来自源参考文档,非人工签认) |
| 来源文档 | `external_artifacts/incoming/from_xinyu/Traditional_Titration_Burette_and_Stand_Asset_Reference.docx`,SHA-256 `49b697f42cc9b61c26649cab50b2eb8f720e7e6d0931090bb4f825f7547bf126` |
| 生成工具链 | `hunyuan-isaac-articulation-assets`,source_route: `hunyuan` |

源文档概览:Robotic Lab Asset Reference · Version 1.0,《传统滴定系统资产生成参考》——
滴定管 articulation + 独立滴定支架,面向 Lift2 VR 示教、Isaac Sim 物理交互与 OmniGraph 显色。
模型基准(MODEL BASIS):Corning PYREX 2103-25 + BRAND 23882 / 578001。

源文档首页目标表:

| 目标 | 交付边界 | 验证重点 |
|---|---|---|
| 传统酸碱滴定动作链 | burette.usd 与 burette_stand.usd 分离;测试场景仅负责装配 | 旋塞可抓可转、尖嘴对准、流量状态可观测、烧杯假液体可变色 |

## 1. 型号身份与使用边界(Model identity & usage boundary)

- 型号与厂商依据:
  - 滴定管:**Corning PYREX 2103-25**,直孔 PTFE 旋塞,红色分度,Class A(以官方产品页字段为准)。
    官方产品页:<https://ecatalog.corning.com/life-sciences/b2c/US/en/General-Labware/Measuring-Transferring-Tools/Burets/PYREX%C2%AE-Buret,-Class-A,-Colored-Scale,-Product-Standard-PTFE-Stopcock-Plug/p/2103-25>
  - 支撑:**BRAND 23882** 底座与不锈钢立杆(<https://shop.brand.de/en/burette-support-p7223.html>)。
  - 管夹:**BRAND 578001** 单滴定管夹,压铸铝本体与 PVC 包覆夹持点
    (<https://shop.brand.de/en/burette-clamp-p7203.html>)。
  - 同族参考(BRAND 紧凑滴定管、双管夹 578000)只解决"长什么样",不替代精确尺寸。
- 关键识别特征:
  - 直管玻璃管身、No. 2 straight-bore PTFE 旋塞、蓝色双翼手柄、红色 0.1 mL 分度、尖嘴。
  - **术语纠正**:传统滴定使用的是"滴定管(burette)",不是"分液漏斗(separatory funnel)"。
    本任务选择直管、PTFE 旋塞、25 mL、0.1 mL 分度的 Class A 视觉基准。
  - **禁止照抄的特征**:Corning 官方网页照片上的圆形标牌外观看似 "PYREX B",但网页标题与
    技术字段明确为 Class A——标牌文字不得照抄(详见第 2 节关键证据警告)。
- 使用边界:
  - 本规格书支撑:Lift2 VR 示教数采、Isaac Sim 物理交互、OmniGraph 体积/显色闭环评测;
    两个交付资产 `burette.usd`(articulation)与 `burette_stand.usd`(V1 静态/刚体),
    以及仅用于装配验证的 `titration_station_test.usd` 组合场景(不是第三个交付资产)。
  - 明确不支撑(V1 范围外,可作为 V2 扩展,不应阻塞首轮数据采集):机器人安装滴定管、
    开合/调高管夹、真实读数视差与弯月面识别、真实酸碱反应或 CFD 流体、支架 articulation。

## 2. 证据等级与建模纪律(Evidence grading)

等级定义:E = 精确(官方规格/实物测量);F = 同族(同系列/同类产品);D = 推导(写明依据);U = 未知。

源文档把产品身份、尺寸、外观照片和仿真假设分开管理。任何没有厂家尺寸或实物测量支持的
交互尺寸,都不能从网页照片像素"量出来"。

| 等级 | 含义 | 能否直接定尺寸 | 示例 |
|---|---|---|---|
| E · Exact | 目标型号官方产品页/官方图片 | 产品页明确给出的字段可以 | Corning 2103-25:25 mL、0.1 mL、约 560 mm、约 Ø12 mm |
| F · Family | 同系列或相邻型号视觉参考 | 不能 | BRAND 紧凑滴定管、双管夹 578000 |
| D · Derived | 本文旋转、裁切、重绘或组合图 | 不能形成新证据 | 竖直视图、尺寸示意、USD 树、OmniGraph 流程图 |
| U · Unknown | 厂家未公布且没有实物测量 | 必须补测或用参数化占位 | 旋塞轴心、手柄跨度、管夹有效行程、底座厚度/质量 |

> **关键证据警告**:Corning 2103-25 的网页标题与技术字段明确为 Class A,但官方网页照片上的
> 圆形标牌外观看似 "PYREX B"。因此:型号、容量与尺寸按页面字段;图中结构与配色可参考;
> **标牌文字不得照抄**,最终印字需实物照片或厂家 CAD 确认。

- **禁止从照片像素推导尺寸**;交互相关尺寸(手柄跨距、轴位、夹持面)必须实测或标 U。
- 尺寸策略(源文档第 05 节):已知包络先冻结,交互尺寸参数化。560 mm 与 Ø12 mm 足以锁定
  整体比例;旋塞区域必须保留参数,直到拿到实物或 CAD。对机器人而言,手柄跨度与轴心位置
  比玻璃壁厚更重要。黄色项(待测交互尺寸)不得由照片比例替代——**must measure, not derive
  from photo pixels**。

![D-04 · 精确产品字段 + 待测交互尺寸(顺序映射,待人工核对)](../../../external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image4.png)

尺寸参数策略表(源文档第 05 节):

| 参数名 | V1 初值策略 | 更新方式 |
|---|---|---|
| overall_height | 560 mm;root 包络基准 | 若实物总高不同,整体骨架参数更新 |
| tube_outer_diameter | 12 mm | 卡尺复核 |
| handle_span / thickness | 从可抓性目标出发的参数化占位;不在文档写死毫米值 | Lift2 夹爪闭合范围 + 实物卡尺 |
| stopcock_axis_pose | 按阀体几何中心建局部 frame | CAD/实物轴心对齐 |
| tip_outer_diameter / cone | 视觉匹配,碰撞用简化 capsule | 卡尺 + 照片正交标定 |

本规格书的逐字段归属表:

| 字段 | 取值 | 等级 | 来源(图片/文档编号) |
|---|---|---|---|
| 产品号 | 2103-25 | E | Corning 官方产品页(B-E01/02/03) |
| 等级 | Class A | E | 官方标题/字段;照片印字需复核 |
| 容量 | 25 mL | E | Corning 官方产品页 |
| 分度 | 0.1 mL | E | Corning 官方产品页 |
| 容量允差 | 0.03 mL | E | Corning 官方产品页 |
| 总高 | 约 560 mm | E | Corning 官方产品页 |
| 管外径 | 约 12 mm | E | Corning 官方产品页 |
| 旋塞 | No. 2;straight-bore PTFE | E | Corning 官方产品页 |
| 底座 | 210 × 155 mm;PP;橡胶脚 | E | BRAND 23882 官方产品页/说明书(S-E01) |
| 立杆 | 505 × Ø12 mm;不锈钢 | E | BRAND 23882 官方产品页/说明书(S-E01) |
| 支架总高 | 550 mm | E | BRAND 23882 官方产品页(S-E01) |
| 单管夹材料/适配 | 压铸铝;PVC 包覆夹持;适配 ≤50 mL 滴定管 | E | BRAND 578001 官方产品页(S-E02) |
| 管夹外廓/行程 | 未公布 | U | 实物或 CAD 补测 |
| 手柄跨度/厚度 | 参数化占位 | U | Lift2 夹爪闭合范围 + 实物卡尺 |
| 旋塞轴心位置 | 按阀体几何中心建局部 frame(待对齐) | U | CAD/实物轴心对齐 |
| 尖嘴外径/锥度 | 视觉匹配 | U | 卡尺 + 照片正交标定 |
| 滴定管/支架质量与质心 | 参数化质量 | U | 称重 + 平衡法 |
| 关闭扭矩/角度—流量曲线 | 未公布;V1 用角度分段(仿真策略) | U | 力矩计/定时称重 |
| 底座厚度/脚垫摩擦 | 未公布 | U | 卡尺 + 推力测试 |
| 整体/侧向/旋塞外观 | 结构与配色参考 | E(官方图,仅视觉) | B-E01/02/03、S-E01、S-E02 |
| 传统旋塞/刻度视觉补充 | 同族外观 | F | B-F01(BRAND 紧凑滴定管) |
| 夹持滚轮与铸件语言 | 同族外观 | F | S-F01(BRAND 578000 双管夹) |
| 阀门功能/产品族、使用语境、阀门装配/支架附件 | 官方文档语境 | 官方文档(见来源总表) | D-E01、D-F01、D-F02 |
| 派生构图图(竖直视图、尺寸示意、USD 树、流程图) | 构图与实现说明 | D | D-01…D-11(本文派生图) |

## 3. 厂商规格冻结表(Frozen manufacturer spec)

冻结值在生成迭代中不可漂移;变更需重新签认(模板第 3 节纪律 / GEN-006)。

滴定管(源文档第 03 节规格冻结):

| 参数 | 值 | 单位 | 等级 | 来源 |
|---|---|---|---|---|
| 产品号 | 2103-25 | — | E | Corning 官方产品页 |
| 等级 | Class A | — | E | 官方标题/字段;照片印字需复核 |
| 容量 | 25 | mL | E | Corning 官方产品页 |
| 分度 | 0.1 | mL | E | Corning 官方产品页 |
| 容量允差 | 0.03 | mL | E | Corning 官方产品页 |
| 总高 | 约 560 | mm | E | Corning 官方产品页 |
| 管外径 | 约 Ø12 | mm | E | Corning 官方产品页 |
| 旋塞 | No. 2;straight-bore PTFE | — | E | Corning 官方产品页 |

目标外形采用 25 mL 直管滴定管;其机械交互重点不是玻璃本体,而是旋塞手柄、轴心、止挡、
尖嘴与安装姿态。

![D-01 · 由 Corning 官方图 B-E01 旋转与留白裁切得到;仅用于竖直构图,不新增尺寸证据(顺序映射,待人工核对)](../../../external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image2.jpg)

官方视图纪律(源文档第 04 节):B-E01/02/03 三张图来自同一 Corning 产品页。资产美术可据此
复刻材料分区、红色刻度、PTFE 阀体与蓝色手柄;**不可从它们反推未公布毫米尺寸**。

![D-11 · B-E01 与 B-E03 并列图版:整体结构与 PTFE 旋塞分件(顺序映射,待人工核对)](../../../external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image3.png)

支架(源文档第 12 节规格冻结):

| 参数 | 值 | 单位 | 等级 | 来源 |
|---|---|---|---|---|
| 底座 | 210 × 155;PP;橡胶脚 | mm | E | 23882 官方产品页/说明书 |
| 立杆 | 505 × Ø12;不锈钢 | mm | E | 23882 官方产品页/说明书 |
| 总高 | 550 | mm | E | 23882 官方产品页 |
| 单管夹 | 压铸铝;PVC 包覆夹持;适配 ≤50 mL 滴定管 | — | E | 578001 官方产品页 |
| 管夹外廓/行程 | 未公布 | — | U | 实物或 CAD 补测 |

支架尺寸纪律(源文档第 12 节):23882 给出底座、立杆和总高;578001 给出材料与容量适配,
但没有精确外廓。因此支架 CAD 必须把管夹外形、杆夹深度和安装高度参数化。

![D-10 · 两件官方组件并列展示;这是组合参考板,不是厂家套装照片(顺序映射,待人工核对)](../../../external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image8.png)

![D-05 · BRAND 官方目录尺寸与组合待测项(顺序映射,待人工核对)](../../../external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image9.png)

注意:支架资产把 BRAND 23882 支撑与 578001 单滴定管夹组合为一件可引用资产。这个组合
**不是厂家套装照片**;它是基于两件官方组件的明确工程装配。

## 4. 资产拆分决策(Decomposition)

**结论先行:这是两个资产,不是一个大 articulation**(源文档第 01 节执行决策)。
滴定管承担精细旋转交互与液体状态;支架承担稳定定位与安装基准。分开建模能降低关节复杂度、
便于资产复用,也让数采失败能明确归因。

| 单元 | 形态 | 理由 |
|---|---|---|
| burette.usd | 独立资产(Articulation;1 个 RevoluteJoint) | 被 Lift2 操作的核心资产;必须具备旋塞手柄、关节限位、液柱 visual、drop_origin、grasp_region、mount_frame |
| burette_stand.usd | 独立资产(V1 静态或单一 RigidBody) | 稳定支撑与对准;必须具备底座、立杆、单管夹、简化碰撞、burette_mount_frame |
| titration_station_test.usd | 组合场景(Scene composition;不是第三个交付资产) | 装配与验证场景;引用两资产、对齐安装 frame、场景层 FixedJoint、烧杯/搅拌器/触发区 |

**为什么支架 V1 不做 articulation**:当前数采动作是"旋转滴定管旋塞完成粗加—逐滴—关闭",
并不包含安装滴定管、开合管夹或调整管夹高度。把管夹做成可动关节只会引入额外碰撞、穿模和
状态初始化问题。待未来新增"安装滴定管"任务时,再派生可动版本(stand_articulated variant)。

### 装配契约:mount frame 对齐(源文档第 15 节)

两资产的唯一契约是 mount frame 对齐。**不要把滴定管网格合并进支架,也不要在 burette.usd
内写世界固定关节**。测试场景引用两资产并用 frame 对齐,然后创建场景级 FixedJoint。

| 契约项 | burette.usd | burette_stand.usd | 场景层 |
|---|---|---|---|
| 安装原点 | mount_frame:玻璃管被夹持中心 | burette_mount_frame:四个夹持点中心 | Xform 对齐 |
| 轴向 | +Z 沿滴定管向上 | +Z 沿立杆向上 | 保持同向 |
| 前向 | +X 指向旋塞手柄操作侧 | +X 指向机器人工作侧 | 手柄朝 Lift2 |
| 固定 | 不固定到 world | root 固定到台面 | FixedJoint:stand ↔ burette body |
| 尖嘴 | drop_origin 位于尖嘴中心下方 | tip_clearance_zone | 与烧杯 target zone 对齐 |

装配顺序:先解决机器人前方净空,再确定管夹高度;不要只按产品总高居中放置。

## 5. USD prim 树(Prim hierarchy)

命名与坐标约定见第 10 节(meter、upAxis = Z、snake_case)。以下 prim 结构为按源文档
第 07 节(D-06 派生图)与第 14 节(支架 Prim 表)整理的建议结构;源文档未给出文字版
burette prim 树,burette 树为按"body_link + 手柄 link + 单 RevoluteJoint"描述的
**建议结构(D 级)**,待生成阶段确认。

![D-06 · 两资产 Prim 树。测试场景在 mount_frame 处创建固定装配(顺序映射,待人工核对)](../../../external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image5.png)

burette.usd 建议 prim 结构(D 级,按源文档第 07 节描述整理):

```text
/World/Burette                  (default prim, kind=component;不固定到 world)
├── Links/body_link             (玻璃管、阀座、尖嘴;刚体根)
├── Links/stopcock_handle_link  (双翼手柄,独立 rigid link)
├── Joints/stopcock_joint       (UsdPhysics.RevoluteJoint,轴线穿过 PTFE 锥塞中心)
├── Visuals/glass_tube
├── Visuals/graduation_decals   (红色分度与数字,独立 decal/贴花)
├── Visuals/ptfe_valve_body     (锥塞、连接套、上下螺母分件)
├── Visuals/liquid_column       (内管同轴圆柱 + 独立 meniscus)
├── Visuals/branding            (可关闭的 branding variant)
├── Collision/...               (少量凸体/capsule,见第 8 节碰撞策略)
└── Annotations/{grasp_region, mount_frame, drop_origin}
```

burette_stand.usd prim 结构(源文档第 14 节):

| Prim | 用途 | V1 物理 | 未来扩展 |
|---|---|---|---|
| /BuretteStand/base | 承载/固定 | root collider | 动态质量与脚垫摩擦 |
| /rod | 高度基准 | same rigid body | 无 |
| /single_clamp | 夹持外形 | same rigid body | 杆夹 prismatic + 开合 revolute |
| /pads | 实际接触位置 | same rigid body collider | 接触传感/柔顺材质 |
| /burette_mount_frame | 滴定管安装锚点 | Xform only | 允许多高度 preset |
| /tip_clearance_zone | 碰撞/可达性检查 | debug volume | 自动布局优化 |

首版支架只有一个物理刚体。所有螺丝、弹簧和滚轮都可以保留视觉分件,但不创建关节。
未来若采集"安装滴定管",从同一视觉资产派生 stand_articulated variant。

建议 variants(支架):physics = static / dynamic_calibrated;clamp = single_578001 /
proxy_lowpoly;branding = off / presentation;collision = train / debug_high。
滴定管 variants:branding、liquid_color、collision(见第 10 节交付表)。

titration_station_test.usd:引用两资产、对齐 mount_frame、场景级
FixedJoint(stand ↔ burette body)、烧杯/搅拌器/触发区;不承担交付资产职责。

### 滴定管部件级建模规范(源文档第 06 节)

高质量感来自薄玻璃、清晰刻度、旋塞装配细节与正确透明排序,而不是过高面数。刻度与液柱
应是独立 visual,便于显隐、随机化和传感器渲染。

| 部件 | 建模建议 | 材质/纹理 | 碰撞 |
|---|---|---|---|
| 玻璃管 | 单一连续外壳;局部加厚阀座与尖嘴过渡 | 薄玻璃 PBR;IOR/透明度按渲染器测试 | Ø12 mm 简化 cylinder/capsule |
| 分度与数字 | 独立 decal/贴花或窄条 mesh;红色 | 避免透明玻璃上的 z-fighting | 无 |
| PTFE 阀体 | 锥塞、连接套、上下螺母分件 | 微粗糙白色 PTFE | 低面数凸体/圆柱 |
| 双翼手柄 | 独立 rigid link;抓取面轻微倒角 | 深蓝塑料;统一 roughness | 凸体;抓取面局部细化 |
| 液柱 visual | 内管同轴圆柱;上表面独立 meniscus | 可调透明液体;不参与刚体 | 无 |
| 滴液/细流 | 对象池或粒子;由 flow 状态启用 | 颜色继承滴定液 | V1 无;用触发区判定 |

> **视觉优先级**:先把旋塞、手柄、尖嘴、红刻度和液柱做对;品牌标识最后做,并保留可关闭的
> branding variant。**训练版建议去品牌化(de-branded training variant),展示版再启用**。

### 支架部件级建模规范(源文档第 13 节)

支架视觉可有倒角与金属高光,但物理代理应极简。V1 默认固定在台面或使用静态刚体;若要
模拟倾覆,必须先获得真实质量与质心。

| 部件 | Visual | Collider | Isaac 设置 |
|---|---|---|---|
| PP 底座 | 白色微粗糙塑料;圆角;橡胶脚 | 1 box + 可选脚垫 box | 默认 static;动态版再录入质量/摩擦 |
| 不锈钢立杆 | 拉丝金属;低频 roughness | 1 capsule | 与底座同一 rigid body |
| 铝合金管夹 | 压铸表面、旋钮/螺丝分件 | 2–5 个 convex hull | V1 固定到立杆 |
| PVC 夹持点 | 米白/浅灰,略软质 | 小圆柱或 capsule | 用于限制滴定管相对位姿 |
| 安装 frame | 隐藏调试 gizmo | 无 | 提供位置/旋转与 FixedJoint 锚点 |

> **固定策略**:训练和评测默认把支架根 prim 固定到台面,排除"开旋塞时整架滑动"的伪失败。
> 展示版本可启用动态底座,但必须先用称重与推力测试标定质量、摩擦和质心。

## 6. 关节契约(Joint contracts)

唯一主动关节:PTFE 旋塞手柄(源文档第 07 节)。旋塞手柄是独立 rigid link,绕锥塞轴心建立
RevoluteJoint。玻璃管、阀座与尖嘴都属于 body_link。滴定管资产本身保持可复用,不在内部
固定到世界。

| 关节 | 类型 | 限位 | 驱动/阻尼 | 初始状态 | 状态输出 |
|---|---|---|---|---|---|
| stopcock_joint(旋塞手柄) | UsdPhysics.RevoluteJoint;轴线穿过 PTFE 锥塞中心 | 0°–90° 设计目标;实际关闭零点、可转范围需实测 | 弱阻尼或无位置驱动;保留摩擦(让 VR 操作体现旋转动作,避免强伺服抢控制) | 0° · CLOSED;每条 episode 可确定复位 | angle、angular_velocity、open_fraction(供 OmniGraph 与评测读取) |

其他 Joint 属性:break force 默认不启用破坏(固定装配的破坏只在专项测试中开放)。
支架 V1 无任何关节;手柄 link 与 body_link 之间仅允许旋转,关闭不必要自碰撞对。

## 7. 建议状态量(State variables)

### 阀门状态:先离散可靠,再连续拟合(源文档第 08 节)

传统滴定最有辨识度的动作不是"打开/关闭"二值开关,而是粗加、减速、逐滴和终点关闭。
V1 可用角度分段实现可控数据,再用实测滴速替换映射曲线。**推荐角度段仅为仿真实现策略,
不声称是厂家流量曲线**。

![D-09 · 推荐角度段。角度仅为仿真实现策略,不声称是厂家流量曲线(顺序映射,待人工核对)](../../../external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image6.png)

| 状态 | 逻辑 | 可视反馈 | 任务语义 |
|---|---|---|---|
| CLOSED | Q = 0 | 无滴液;液柱静止 | 复位 / 完成 |
| DRIP | 低频单滴;每滴固定或随机小体积 | 离散 droplet | 终点精细控制 |
| FINE | 中等连续流量 | 短细流或高频滴液 | 接近终点前减速 |
| OPEN | 高流量 | 连续细流 | 初段快速加入 |

### OmniGraph 信号表:旋塞角度驱动体积、液柱、滴液与显色(源文档第 16 节)

烧杯中的假液体 mesh 变色完全可行。推荐把它留在场景图中:滴定管只输出 angle / flow /
dispensed volume,烧杯负责颜色过渡——**资产状态与场景反馈解耦**。

![D-08 · 资产状态与场景反馈解耦(顺序映射,待人工核对)](../../../external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image10.png)

| 状态量 / Signal | 类型 | 写入者 | 阈值/语义 |
|---|---|---|---|
| stopcock_angle_deg | float | joint state | 原始旋塞角 |
| valve_open_fraction | float 0–1 | mapping node | 统一控制量 |
| flow_rate_ml_s | float | flow model | 体积积分 |
| burette_liquid_volume_ml / level | float | integrator / normalized | 剩余体积并更新内液柱 |
| drop_enabled / stream_enabled | bool | state logic | 对象池或粒子显隐 |
| target_container_inside | bool | scene trigger | 确认滴液进入烧杯 |
| dispensed_volume_ml | float | scene integrator | 任务进度与评分 |
| indicator_progress | float 0–1 | task logic | 烧杯颜色插值 |

### OmniGraph 实现顺序与伪代码(源文档第 17 节)

先用确定性的体积状态机做出稳定数据闭环,再决定是否加液滴粒子。**评测应读取体积与关节
状态,不依赖像素颜色反推成功**。

推荐图节点顺序:

1. 读取 stopcock_joint position;归一化到 valve_open_fraction。
2. 按 CLOSED / DRIP / FINE / OPEN 分段或曲线计算 flow_rate_ml_s。
3. 仅当 target_container_inside 为 true 时累加 receiver 体积;否则累加 spilled_volume_ml。
4. 从 burette_liquid_volume_ml 更新内液柱高度;到 0 后强制 Q = 0。
5. 用累计体积或终点函数生成 indicator_progress;插值烧杯假液体 BaseColor/Emission。
6. 按状态启用 droplet pool 或 stream visual;它们只是反馈,不是评测真值。

核心更新逻辑:

```text
open = map_angle(stopcock_angle_deg)
Q = flow_curve(open)
dV = min(Q * dt, burette_liquid_volume_ml)
burette_liquid_volume_ml -= dV
if target_container_inside:
    dispensed_volume_ml += dV
else:
    spilled_volume_ml += dV
indicator_progress = endpoint_model(dispensed_volume_ml)
```

> **终点颜色设计**:可采用"无色 → 极浅粉 → 稳定浅粉"的短暂过渡,并把过量区设为明显深粉。
> 这样轨迹既有视觉反馈,也能把 overshoot 作为明确失败模式。颜色阈值属于任务配置,
> 不写死在滴定管资产。

## 8. 交互语义(Interaction semantics)

### Lift2 交互阶段(源文档第 09 节)

手柄面向机器人、夹体与立杆置于后侧。VR 数采应让末端从前方进入,先包络双翼手柄,再绕
旋塞轴心旋转;**不要抓玻璃管本体完成阀门动作**。

![D-07 · 顶视/侧视装配。安装高度与前方净空在 Isaac Sim 中用机器人可达性扫描最终确定(顺序映射,待人工核对)](../../../external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image7.png)

| 阶段 | 动作 | 成功判据 |
|---|---|---|
| approach | 末端沿手柄法向接近;避开玻璃管和夹体 | pregrasp_frame;clearance_min |
| grasp | 夹指包络双翼手柄;接触点位于轴心两侧 | grasp_region;contact_count |
| turn(actuate) | 围绕 stopcock_joint 轴旋转,不施加显著横向弯矩 | angle delta;off_axis_force |
| meter | OPEN → FINE → DRIP 的阶段式减速 | valve_state;flow_rate |
| close / release | 回到关闭阈值后松夹并沿原路径退出 | closed_event;release_event |

> **数采前硬门槛**:在固定机械臂基座与正式桌面高度下做 20 次单原语"抓—转—关"测试;
> 成功至少 18/20,再进入完整滴定轨迹。完整粗加—逐滴—关闭建议至少 16/20。

### VR 示教任务脚本:粗加—减速—逐滴—关闭(源文档第 18 节)

建议首版只让机器人操作旋塞;烧杯、磁力搅拌器与滴定管都在 episode 开始时就位。这样任务
新颖性集中在精细旋转与时序控制,而不是重复搬运。

| 序 | 阶段 | 动作 | 技能标签 |
|---|---|---|---|
| 1 | 定位 | 确认烧杯位于尖嘴下方、搅拌开启、旋塞关闭 | align / verify |
| 2 | 预抓 | 末端从前方接近双翼手柄 | approach |
| 3 | 夹持 | 稳定夹住手柄,避免触碰玻璃管 | grasp |
| 4 | 粗加 | 转到 OPEN,快速加入主要体积 | turn / dispense |
| 5 | 减速 | 回到 FINE,观察颜色接近终点 | meter |
| 6 | 逐滴 | 在 DRIP 区间做小幅开—关或保持低开度 | fine-turn |
| 7 | 终点 | 颜色达到目标窗口后完全关闭 | close |
| 8 | 退出 | 松开手柄并撤回至安全位 | release / retreat |

> **首版范围**:不要求机器人安装滴定管、不要求真实读数视差/弯月面识别、不模拟真实酸碱
> 反应或 CFD。以上都可作为 V2 扩展,不应阻塞首轮数据采集。

### 物理碰撞与质量策略(源文档第 10 节)

碰撞与质量:交互区精细,透明区简化。透明玻璃视觉网格不应直接用作三角网格碰撞。V1 的
稳定性来自少量凸体、合理 contact offset、关闭自碰撞和固定装配,而不是增加碰撞面数。

| 区域 | Collider | 精度 | 原因 |
|---|---|---|---|
| 长玻璃管 | 1 个 capsule/cylinder | 低 | 主要用于误碰与安全间隙 |
| 阀座与螺母 | 2–4 个 cylinder/box | 中 | 定义手柄周边障碍 |
| 手柄 | 每翼 1 个 convex hull + 中心 hub | 高 | 直接影响抓取稳定性 |
| 尖嘴 | 1 个 tapered proxy 或 capsule | 中 | 用于对准/误碰,不参与真实流体 |
| 液柱/刻度/印字 | 无 | — | 纯视觉与状态表达 |

质量与惯量:

- 若厂家未给质量:优先称量实物;在此之前使用参数化质量并记录为 U 项。
- 惯量由简化复合体计算;不得因手柄过轻导致 solver 抖动而随意把玻璃质量增大十倍。
- burette 自身可为刚体根;装入支架后由场景 FixedJoint 约束。
- 手柄 link 与 body_link 之间仅允许旋转;关闭不必要自碰撞对。

## 9. 验证矩阵与失败模式(QA matrix & failure modes)

### 任务评分与资产验收分开设计(源文档第 19 节)

资产"能稳定被操作"与任务"是否滴定到终点"是两件事。把分数拆开,才能知道失败来自几何、
物理、控制还是时序。

任务评分(时序判据):

| 时序 | 判据 | 权重建议 | 对应技能 |
|---|---|---|---|
| T1 | 夹爪进入 grasp_region 并形成双侧接触;未碰玻璃管 | 0.15 | approach / grasp |
| T2 | 旋塞进入 OPEN 或 FINE;累计加入量达到粗加下限 | 0.20 | turn / dispense |
| T3 | 终点前进入 DRIP 状态并保持至少 N 个控制步 | 0.20 | fine control |
| T4 | dispensed_volume 进入目标窗口;spilled_volume 低于阈值 | 0.25 | meter / align |
| T5 | 旋塞回到 CLOSED;液体颜色处于目标窗口 | 0.15 | close / observe |
| T6 | 夹爪安全释放;支架/滴定管无异常位移或穿透 | 0.05 | release / retreat |

资产验收 Gate:

- G0:单位/轴向正确;整体高度、管径、底座与立杆尺寸通过尺规检查。
- G1:旋塞从 0° 到 90° 无穿模;零位与方向一致;关节状态可读取。
- G2:单原语抓—转—关 ≥18/20;无非预期玻璃碰撞。
- G3:完整 OPEN→DRIP→CLOSED ≥16/20;支架根位移低于场景阈值。
- G4:固定 dt 与随机 dt 下体积积分误差均在工程容差内。

### Isaac Sim 验证矩阵(源文档第 20 节)

先在空场景验证单资产,再做装配,再加机器人,最后接 OmniGraph。每层只引入一种新变量。
截至本规格书转换日,以下各项均未执行,标 `NOT_TESTED`(GEN-007)。

| 检查 | 类型(static/reopen/runtime/robot) | 通过标准 | 失败定位 | 结果 |
|---|---|---|---|---|
| 尺度 | static(1 m world units;测量工具) | 已知尺寸误差在建模容差内 | 导入缩放/单位 | `NOT_TESTED` |
| 关节 | runtime(禁用机器人,直接驱动角度) | 限位、轴向、零位、无穿模 | pivot/joint axis | `NOT_TESTED` |
| 接触 | robot(夹爪低速闭合) | 手柄稳定、不夹入玻璃 | collider/contact offset | `NOT_TESTED` |
| 装配 | runtime(两资产 + FixedJoint) | 无爆炸、无漂移、无初始穿透 | frame/solver | `NOT_TESTED` |
| 可达性 | robot(Lift2 全工作空间采样) | 预抓、抓取、全开、关闭姿态可达 | 安装高度/朝向 | `NOT_TESTED` |
| 体积 | runtime(固定关节脚本扫角) | Q 单调、无负体积、耗尽归零 | mapping/integrator | `NOT_TESTED` |
| 显色 | runtime(体积跨越终点) | 颜色连续、可复位、过量明显 | shader/state reset | `NOT_TESTED` |
| 随机化 | reopen(光照/背景/液色变化) | 刻度、手柄、液柱仍可辨识 | 材质/曝光 | `NOT_TESTED` |

### 高概率失败模式(源文档第 20 节)

- 手柄与夹体过近:腕部或夹指先撞支架;解决:旋转管夹、增加前向偏置、抬高/降低安装点。
- 透明排序抖动:液柱与玻璃共面;解决:减小液柱半径、分离 meniscus、限制透明层数。
- 旋塞被强驱动"弹回":位置 drive 太强;解决:弱化 drive、增加可控阻尼。
- 颜色已变但体积未进入烧杯:只看视觉粒子;解决:以 trigger + volume state 为真值。
- 支架滑动造成策略作弊或失败:训练版固定根 prim;动态版单独标定。

## 10. 交付与命名规范(Delivery conventions)

交付目标是可引用、可替换、可测的资产,不只是"看起来像"。每个文件都要带 Prim 树、物理层、
语义 frame、材质与校验场景(源文档第 21 节)。

| 交付项 | burette | stand |
|---|---|---|
| 主文件 | burette.usd | burette_stand.usd |
| 层级 | visual / collision / physics / annotations | visual / collision / physics / annotations |
| 材质 | glass、marking_red、ptfe_white、handle_blue、liquid | pp_white、steel、aluminum、pvc_pad、rubber |
| 语义 | grasp_region、mount_frame、drop_origin | burette_mount_frame、clearance_zone、support_plane |
| Variants | branding、liquid_color、collision | physics、clamp、branding、collision |
| 测试 | joint sweep / robot grasp | static stability / mount alignment |

- 坐标/单位/轴向:单位 meter;upAxis = Z;+X = 机器人前方/手柄操作侧;+Y = 左侧
  (与 USD-001 一致的 Z-up 约定)。
- 命名:snake_case,禁止空格和随意编号;物理 link 与 visual mesh 分层命名。
- 所有可供 graph/评测读取的 attribute 写进 asset README 或 schema 表。
- 源网格、纹理与 USD 中使用相同资产版本号;尺寸更新不得静默覆盖。
- 打包形式:每资产一个主 USD 入口(entrypoint),引用闭合(visual/collision/physics/
  annotations 分层齐备),经 ConvertAsset 准入边界进入场景(GEN-001)。

## 11. 待测清单(Open measurements)

建模开工前与首轮后必须补的测量(源文档第 22 节):不需要等所有测量齐全才能开工,但未知项
必须是显式参数,不能藏在网格里。按对交互的影响排序:

| 优先级 | 项 | 等级 | 计划如何获得 | 阻塞内容 |
|---|---|---|---|---|
| P0 | 手柄总跨度、厚度、抓取面圆角 | U | 卡尺 + 正交照片 | Lift2 抓取与 collider |
| P0 | 旋塞轴心相对管中心/尖嘴的位置 | U | 卡尺或 CAD | joint pivot / drop_origin |
| P0 | 安装高度与手柄朝向 | U | Isaac 可达性扫描 | 完整任务 |
| P1 | 阀体、螺母、尖嘴外廓 | U | 卡尺 | 近场碰撞 |
| P1 | 管夹外廓、滚轮间距、杆夹深度 | U | 卡尺 + 拍照标定 | 支架 visual/collider |
| P1 | 滴定管与支架质量/质心 | U | 称重 + 平衡法 | 动态展示版 |
| P2 | 关闭扭矩、启动力矩、角度—流量曲线 | U | 力矩计/定时称重 | 高保真手感/滴速 |
| P2 | 底座厚度、脚垫摩擦 | U | 卡尺 + 推力测试 | 动态倾覆/滑移 |

> **建议的最小实物拍摄包**:正面、背面、左右侧、俯视、仰视、旋塞特写、管夹夹持状态、
> 带标尺的整体照;每张保持长焦和正交,避免广角畸变。

## 12. 图片清单(Image inventory)

图片只存 `external_artifacts/asset_evidence/traditional-titration-burette-and-stand/`(GEN-004);
SHA-256 取自 `MANIFEST.sha256`。`image11–image20` 与源文档来源总表中登记的原始文件哈希
**逐一相符,映射已确认**;`image1–image10` 为源文档内的派生图(D 级),按文档出现顺序经
rels 映射,标"顺序映射,待人工核对"。

| 图片 ID | 等级 | 来源 | 使用边界 | 相对路径 | SHA-256 |
|---|---|---|---|---|---|
| D-cover(顺序映射,待人工核对) | D | 源文档封面合成图 | 文档装饰/概览;不构成尺寸证据 | `external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image1.png` | `7e8a0b1e6517edade541882e1b71d7d75b1812940249e7758e6023fa2c56f121` |
| D-01(顺序映射,待人工核对) | D | 由 B-E01 旋转与留白裁切 | 仅竖直构图;不新增尺寸证据 | `external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image2.jpg` | `86cae288cf23ac8f555796783ee1feaacf25fc6708cd24ba047db180140fb0d2` |
| D-11(顺序映射,待人工核对) | D | B-E01 与 B-E03 并列图版 | 整体结构与 PTFE 旋塞分件构图;不新增尺寸证据 | `external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image3.png` | `806e512b71edd4cbeb5be9c353f4dde503197b4f8a227a201a3aa25cce35bec4` |
| D-04(顺序映射,待人工核对) | D | 精确产品字段 + 待测交互尺寸示意 | 尺寸策略说明;黄色项不得由照片比例替代 | `external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image4.png` | `241af5e9d35c54ee6c5f66babf5ab22940c409e37cdc5f7f4400189e795f9d49` |
| D-06(顺序映射,待人工核对) | D | 两资产 Prim 树示意 | 架构说明;测试场景在 mount_frame 处创建固定装配 | `external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image5.png` | `fbe8ea5d5a58b8b1c2796f7e60490855d31456af75146e333efa9109a2f6ae28` |
| D-09(顺序映射,待人工核对) | D | 推荐角度段示意 | 仿真实现策略;不声称是厂家流量曲线 | `external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image6.png` | `673dc62b637aa599d8bc2cf1fb929fa5f9ef64a154f145dd26f145bbca39eb28` |
| D-07(顺序映射,待人工核对) | D | 顶视/侧视装配示意 | 装配/净空说明;安装高度以 Isaac 可达性扫描为准 | `external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image7.png` | `3b9c7b97d57f60d2af1757789d7416542668f11e61ce81b7a674d18ea4f13276` |
| D-10(顺序映射,待人工核对) | D | 两件官方组件并列参考板 | 组合参考,不是厂家套装照片 | `external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image8.png` | `df310cab7ddce2f28cf9e7d1f1050902365c3cfc751d8e4a39a10e3c8e675304` |
| D-05(顺序映射,待人工核对) | D | BRAND 官方目录尺寸与组合待测项 | 支架尺寸策略说明 | `external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image9.png` | `bd38f9f97b2381c34b5974865ce0794f429ba6cd1452370ad096dbed7f4caac1` |
| D-08(顺序映射,待人工核对) | D | 资产状态与场景反馈解耦示意 | OmniGraph 架构说明 | `external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image10.png` | `2f373c69a3fe313a5154d485c93d93c4ac439a641570244a263fbce99b8ac57f` |
| B-E01 | E(Exact page;图片可能为代表性图) | Corning 2103-25 官方整体图 A(原始文件 `B-E01_corning_2103-25_A.jpg`) | 管身、分度、阀体与尖嘴比例;图中等级标牌不作为精确证据,标牌文字不得照抄 | `external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image11.jpg` | `ea258a53a39e42bd587b3049f9abbb2ab87917a4712e8a75f03a366595f2df03` |
| B-E02 | E(同上) | Corning 官方整体图 B(`B-E02_corning_2103-25_B.jpg`) | 相反侧视角与旋塞装配关系 | `external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image12.jpg` | `05ee65871331f4ba5393240160cde5fa501701a057fbd7f64131b77b51ce0f46` |
| B-E03 | E(同上) | Corning 官方旋塞拆分图(`B-E03_corning_2103-25_C.jpg`) | PTFE 锥塞、手柄、螺母和密封圈分件 | `external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image13.jpg` | `7c1143adc8ea323ee01f964ff009faa75b8a152338ab2ee0b78c548214fdd1f7` |
| B-F01 | F | BRAND 紧凑滴定管(`B-F01_brand_compact_burette.jpg`) | 只补充传统阀门与标记视觉;不对应 Corning 目标尺寸 | `external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image14.jpg` | `521c0d7b8b3a5e4a2f16aab8ed446645e168497e9d63711b8b43d838ea66c835` |
| S-E01 | E | BRAND 23882 支撑(`S-E01_brand_23882_support.jpg`) | 精确支架底座与立杆产品 | `external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image15.jpg` | `ba375e5bfb3cebd67184c6b14c49b99e0dd80d8c3393e3f33f3cf8d1917b7156` |
| S-E02 | E | BRAND 578001 单管夹(`S-E02_brand_burette_clamp.jpg`) | 目标单管夹外观;尺寸仍需实物/CAD | `external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image16.jpg` | `f8dd5b23d88a35382f58fbe5379e7ea9f752a988b104ea843ffd8d13e025973d` |
| S-F01 | F | BRAND 578000 双管夹(`S-F01_brand_578000_clamp.jpg`) | 同族铸件与滚轮参考;不是目标管夹 | `external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image17.jpg` | `befe262263d2ad19388ab7a829f0ddfa91025e531d6989cb6a933d01c64c2e20` |
| D-E01 | 官方文档(Official document) | BRAND 官方 datasheet(`D-E01_brand_datasheet-1.png`) | 产品族技术页;阀门功能/产品族 | `external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image18.png` | `846204f95ef21d368b36d6789c16b0a7d92a6f3f13cd81be1da20b27c0eacab4` |
| D-F02-07 | 官方文档(Official family document) | BRAND 说明书第 7 页(`D-F02_brand_manual-07.png`) | 阀门装配顺序:上下螺帽与阀体安装 | `external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image19.png` | `512488681eea8ada32863814ce3311f2e6fdfaf5cd447c991b656ed3c8bdb4ca` |
| D-F02-08 | 官方文档(Official family document) | BRAND 说明书第 8 页(`D-F02_brand_manual-08.png`) | 附件页包含 23882 支架信息 | `external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image20.png` | `ed440ca17a41ece1f3be8378d2aaff4f6b51829c0e66db643e91d412dd02cb9a` |

源文档来源图页内嵌如下(按其原顺序,带源文档 caption):

**B-E01 · Corning 官方整体图 A** — 用于管身、分度、阀体与尖嘴比例;图中等级标牌不作为精确证据。

![B-E01](../../../external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image11.jpg)

**B-E02 · Corning 官方整体图 B** — 用于相反侧视角与旋塞装配关系。

![B-E02](../../../external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image12.jpg)

**B-E03 · Corning 官方旋塞拆分图** — 用于 PTFE 锥塞、手柄、螺母和密封圈分件。

![B-E03](../../../external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image13.jpg)

**B-F01 · BRAND 同族滴定管** — 只补充传统阀门与标记视觉,不对应 Corning 目标尺寸。

![B-F01](../../../external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image14.jpg)

**S-E01 · BRAND 23882 支撑** — 精确支架底座与立杆产品。

![S-E01](../../../external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image15.jpg)

**S-E02 · BRAND 578001 单管夹** — 目标单管夹外观;尺寸仍需实物/CAD。

![S-E02](../../../external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image16.jpg)

**S-F01 · BRAND 578000 双管夹** — 同族铸件与滚轮参考;不是目标管夹。

![S-F01](../../../external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image17.jpg)

**D-E01 · BRAND 官方 datasheet** — 产品族技术页。

![D-E01](../../../external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image18.png)

**D-F02-07 · BRAND 说明书第 7 页** — 阀门装配顺序:上下螺帽与阀体安装。

![D-F02-07](../../../external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image19.png)

**D-F02-08 · BRAND 说明书第 8 页** — 附件页包含 23882 支架信息。

![D-F02-08](../../../external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image20.png)

## 13. 来源与许可(Sources & licensing)

来源总表与使用边界(源文档附录 A;原始网页、PDF、图像、SHA-256 与 manifest 收录于源文档
随附 sources.zip;本仓库侧证据图片与哈希见第 12 节与 `MANIFEST.sha256`):

| 编号 | 来源 | 等级 | 本文用途 |
|---|---|---|---|
| B-E01/02/03 | Corning 2103-25 官方产品页与三张图 | Exact page;images may be representative | 规格/整体/旋塞 |
| B-F01 | BRAND compact burette | Family | 传统旋塞/刻度视觉补充 |
| S-E01 | BRAND 23882 burette support | Exact | 底座/立杆/尺寸 |
| S-E02 | BRAND 578001 one-burette clamp | Exact | 单管夹外观/材料/容量 |
| S-F01 | BRAND 578000 two-burette clamp | Family | 夹持滚轮与铸件语言 |
| D-E01 | BRAND burette datasheet | Official document | 阀门功能/产品族 |
| D-F01 | BRAND burette brochure p.10 | Official family document | 传统滴定管使用语境 |
| D-F02 | BRAND manual pp.7–8 | Official family document | 阀门装配/支架附件 |
| D-01…09 | 本文派生图 | Derived | 构图、架构与实现说明 |

官方入口:

- Corning 2103-25:<https://ecatalog.corning.com/life-sciences/b2c/US/en/General-Labware/Measuring-Transferring-Tools/Burets/PYREX%C2%AE-Buret,-Class-A,-Colored-Scale,-Product-Standard-PTFE-Stopcock-Plug/p/2103-25>
- BRAND 23882:<https://shop.brand.de/en/burette-support-p7223.html>
- BRAND 578001:<https://shop.brand.de/en/burette-clamp-p7203.html>

许可提醒:网页与产品图片的版权归原权利人所有;来源包用于内部建模参考与证据追踪。
**对外发布 3D 资产前应检查品牌标识与图像再分发权限**;训练版资产建议去品牌化
(branding = off variant),展示版再启用品牌标识,且 Corning 照片中的 "PYREX B" 标牌文字
不得照抄(见第 2 节)。

## 附录 A · 一页式开工顺序(源文档附录 B · HANDOFF)

如果资产团队只看这一页,请按以下顺序推进。任何一步失败,不进入下一步。

| 阶段 | 名称 | 完成定义 |
|---|---|---|
| 01 | 阻挡建模 | 按 560 mm / Ø12 mm 与 210×155 / 505×Ø12 / 550 mm 建比例;旋塞和管夹未知尺寸参数化。 |
| 02 | 交互代理 | 先做手柄 link、旋塞 joint、玻璃/阀体/尖嘴 collider;不做刻度与透明材质。 |
| 03 | 装配可达 | 用 mount frames 组合;让手柄朝 Lift2,扫描抓取、全开、逐滴、关闭姿态。 |
| 04 | 物理稳定 | 固定支架根;完成 20 次单原语测试;修正轴心、碰撞和阻尼。 |
| 05 | 视觉精修 | 玻璃、刻度、PTFE、液柱与材质;解决透明排序与可读性。 |
| 06 | 状态闭环 | 接 OmniGraph:角度→流量→体积→液柱/滴液→烧杯显色。 |
| 07 | 完整采集 | 完成粗加—减速—逐滴—关闭;建立体积、洒漏、最终关闭和支架稳定评分。 |

> **最终建议(源文档原文)**:这个任务成立,而且足够 "fancy":它同时包含精细旋转控制、
> 分阶段流量、末端视觉反馈、装配约束与长时序闭环。首版的成功关键是把旋塞做成可靠的
> 机器人交互关节,而不是先追求真实流体。
