# 资产规格书:IKA OVEN 125 control-dry(实心门)

> 本规格书是对 `external_artifacts/incoming/from_xinyu/IKA_OVEN_125_reference.docx`
> (ASSET REFERENCE PACK — IKA OVEN 125 control-dry,LIFT2 实验室烘箱资产重建与操作接口参考,
> 自包含母版,2026-08-28)的逐节格式转换,依据
> [资产规格书模板](../../standards/templates/asset-spec-template.md) 与
> [GEN-001..007](../../standards/asset-generation.md) 填写。内容忠实转录源文档,
> 未新增任何未经源文档支撑的数值;不可核验项一律进入第 11 节待测清单。

## 0. Front matter

| 字段 | 值 |
|---|---|
| asset slug | `ika-oven-125` |
| 规格书版本 | `v1.0` |
| 状态 | `draft`(转换自现有参考文档,未经人工冻结签认;冻结需人工签认,见 GEN-006) |
| 日期 | 2026-09-17 |
| 作者/Agent | Claude Code(格式转换 Agent) |
| 来源文档 | `external_artifacts/incoming/from_xinyu/IKA_OVEN_125_reference.docx`,SHA-256 `c4338164e43123d09102865b295cd5ab04dd238aa186a373d92ae7362562ec21` |
| 生成工具链 | `hunyuan-isaac-articulation-assets`,source_route: `hunyuan` |

源文档交付结论(封面转录):DOCX 与 PDF 均已将清单中的每张图片真正嵌入;ZIP 额外保留独立原图、派生裁切与机器可读来源清单。本仓库仅持有 docx;图片证据已抽取至 `external_artifacts/asset_evidence/ika-oven-125/`(见第 12 节)。

## 1. 型号身份与使用边界(Model identity & usage boundary)

- 型号与厂商依据:**IKA OVEN 125 control-dry,实心门(solid door)版本**。主商业标识以 2025 产品册和经销商页中的 **Ident No. 0020003991** 为准;不同电压/地区可能出现其他 Ident. No.。
- 目标文档:LIFT2 实验室烘箱资产重建与操作接口参考。
- 关键识别特征(源文档"关键辨识"表,逐字转录):

| 对象 | 允许用途 | 禁止误用 |
|---|---|---|
| E 系列 | 目标实心门型号的几何、材质、交互接口 | 不同来源压缩图不应被当成新视角 |
| G 系列 | 共用机身、控制面板、内胆隐藏结构的辅助判断 | 不能把玻璃窗、玻璃门厚度照搬到目标 USD |
| D 系列 | 由 E02/E03 原图裁切的操作局部 | 不是独立拍摄,也不能用于绝对尺寸标定 |

- 使用边界:
  - 支撑(源文档"最终建议"):现有图片足够制作**外观级 USD、门关节、把手抓取区、内胆层架和控制面板的第一版**。
  - 不支撑:若要做**接触稳定、力控开门和真实成功阈值**,仍需第 11 节列出的关键尺寸实测;在实测补齐前,相关交互尺寸一律标 U,不得从照片像素推导(GEN-002)。

## 2. 证据等级与建模纪律(Evidence grading)

模板等级定义:E = 精确(官方规格/实物测量);F = 同族(同系列/同类产品);D = 推导(写明依据);U = 未知。

**源文档分级到模板等级的映射**:源文档图片按 E / F / G / D 四个系列分级,语义与模板不同,按下表归并:

| 源文档分级 | 源文档语义 | 映射到模板等级 |
|---|---|---|
| E 系列(EXACT,绿色) | 目标实心门型号或同目标替代图(含官方产品册内目标面板图、经销商同型号图) | 几何/外观证据按 **E** 使用;但禁止从照片像素推导尺寸,尺寸值仍以官方规格/实测为准 |
| F 系列(FAMILY) | Oven 125 系列参考,控制面板非目标 control-dry | **F**(同族),不能作为 exact-model 证据 |
| G 系列(SIBLING / SIBLING-SHARED,橙色) | control-dry glass 玻璃门同系列 / dry glass 视频帧 | **F**(同族),仅用于共用机身、控制面板或内胆隐藏结构判断;玻璃窗、玻璃门厚度与质量禁止复制 |
| D 系列(DERIVED) | 由 E02/E03 原图裁切的操作局部 | **D**(派生),不是独立拍摄,不能用于绝对尺寸标定 |

建模纪律(源文档与 GEN-002 共同约束):

- **禁止从照片像素推导尺寸**;交互相关尺寸必须实测或标 U。
- 现有图以 3/4 视角为主,透视不能替代实物测量(源文档:内胆"照片透视不能替代实物测量")。
- 本规格书的逐字段归属表:

| 字段 | 取值 | 等级 | 来源(图片/文档编号) |
|---|---|---|---|
| 外形尺寸 W×H×D | 700 × 825 × 650 mm | E | IKA/Pipette 产品数据表 |
| 内胆工作区 W×D×H | 550 × 525 × 450 mm | E | IKA/Pipette 产品数据表 |
| 内胆容积 | 125 L | E | IKA/Pipette 产品数据表 |
| 目标版本重量 | 82 kg(实心门 control-dry,含两层架) | E | IKA/Pipette 产品数据表 |
| 工作温度 | 室温 +5 °C 至 300 °C | E | IKA/Pipette 产品数据表 |
| 层架 | 最多 6 层;每层最大 30 kg | E | IKA/Pipette 产品数据表 |
| 门最大开启角 | 约 180°;门铰链方向可换 | E | IKA Oven 125 control 操作手册 |
| 控制接口 | 双 TFT、旋转/按压旋钮、软键、USB-B、RS 232 | E | IKA 2025 Oven 125 产品册 / E11 |
| 门重(换门向操作语境) | 约 15 kg | E | IKA Oven 125 control 操作手册 |
| 设备与墙体最小距离 | 150 mm,并要求防倾倒固定件 | E | IKA Oven 125 control 操作手册 |
| 当前参考配置铰链侧 | 右侧铰链、门向观察者右侧打开 | E(图示) | E01;手册明确支持换向 |
| 门/把手/控制区整体几何与比例 | 见 E01–E05 | E(图示,禁止像素推尺寸) | E01–E05 |
| 背面结构(通风孔、电源入口、穿线/风道、风扇通风区) | 见 E03 | E(图示) | E03 |
| 控制面板布局(双 TFT、软键、Back/Menu、Light/Lock、旋钮) | 见 E11 | E(官方产品册图) | E11 |
| 门体、内胆与开启姿态交叉核验 | 见 F01 | F | F01(系列图,面板非目标) |
| 共用机身/控制区/内胆隐藏结构 | 见 G01–G03 | F | G01–G03(玻璃门同系列) |
| 抓取方向、门厚层次、碰撞体拆分局部 | 见 D01/D02 | D | D01/D02(E02 裁切) |
| 严格左右侧正视/侧板细节 | — | U | 待测清单 #1 |
| 把手截面与离门距离 | — | U | 待测清单 #2 |
| 铰链轴线位置与门质量参数 | — | U | 待测清单 #3 |
| 旋钮直径/按压行程 | — | U | 待测清单 #4 |
| 层架高度与前缘净空 | — | U | 待测清单 #5 |
| 机身固定方式(防倾倒支架与台面/墙体约束) | — | U | 待测清单 #6 |
| placement surface 边界与安全内缩 | 默认先选中层、靠中心的可达区域 | D(推导:由内胆净工作区与任务可达性推导,源文档明确建议) | 源文档第 2 节"容器放置区域" |

## 3. 厂商规格冻结表(Frozen manufacturer spec)

冻结值在生成迭代中不可漂移;变更需重新签认。下表逐字转录源文档第 1 节规格表:

| 参数 | 值 | 单位 | 等级 | 来源 |
|---|---|---|---|---|
| 外形尺寸 W × H × D | 700 × 825 × 650 | mm | E | IKA/Pipette 产品数据表 |
| 内胆工作区 W × D × H | 550 × 525 × 450 | mm | E | IKA/Pipette 产品数据表 |
| 内胆容积 | 125 | L | E | IKA/Pipette 产品数据表 |
| 目标版本重量 | 82(实心门 control-dry,含两层架) | kg | E | IKA/Pipette 产品数据表 |
| 工作温度 | 室温 +5 至 300 | °C | E | IKA/Pipette 产品数据表 |
| 层架 | 最多 6 层;每层最大 30 | kg/层 | E | IKA/Pipette 产品数据表 |
| 门最大开启角 | 约 180;门铰链方向可换 | ° | E | IKA Oven 125 control 操作手册 |
| 控制接口 | 双 TFT、旋转/按压旋钮、软键、USB-B、RS 232 | — | E | IKA 2025 Oven 125 产品册 |

规格来源(源文档登记的三份官方文档,URL 见第 13 节):

- 来源:IKA/Pipette 产品数据表
- 来源:IKA 2025 Oven 125 产品册
- 来源:IKA Oven 125 control 操作手册

## 4. 资产拆分决策(Decomposition)

源文档第 5 节"USD 资产拆分建议"逐字转录;拆分形态与理由如下:

| 单元 | 形态 | 关键属性 | 理由(评测用途) |
|---|---|---|---|
| `oven_body` | 静态子部件(rigid/static) | 700 × 825 × 650 mm 外包络;固定基座 | 防止拉门时机身滑动/倾覆 |
| `door` | 关节 link(rigid) | 实心门;独立质量与碰撞体 | open/close 状态与接触 |
| `door_hinge` | 关节(revolute) | 竖直轴;0–180°;阻尼/限位 | 门角、保持、推拉轨迹 |
| `handle` | 静态子部件(door child collider) | 竖直可抓取区域;简化胶囊/盒碰撞 | grasp target 与手-门约束 |
| `shelf_0..5` | 静态子部件(rigid/static child) | 可插拔层架;明确 placement surface | 容器放置与稳定性 |
| `control_knob` | 关节(revolute + prismatic/button) | 旋转与按压双自由度/复合交互 | setpoint 与 start/stop |
| `mains_switch` | 关节(toggle/rocker) | 左上小拨杆;独立状态 | power_on/off(可选) |
| `display` | 静态子部件(visual/state surface) | actual/set temperature、timer、status | 可观察任务状态 |

补充决策依据(源文档各节):

- **铰链建议**(源文档第 2 节):将门定义为单自由度 revolute joint。默认右侧竖直转轴,角度范围 0°(闭门)至约 180°(完全打开);碰撞体必须覆盖门板、把手和前框,避免机器人手臂穿透。
- **可直接建模**(源文档第 2 节):箱体近似长方体;控制箱位于门体上方;当前参考配置为右侧铰链、门向观察者右侧打开。由于手册明确支持换向,**USD 应允许通过配置改变铰链侧**。
- **容器放置区域**(源文档第 2 节):对 LIFT2 任务,不应把整个内胆都设为一个模糊目标区。应为每层架建立明确的 placement surface、边界和安全内缩;默认先选择中层、靠中心的可达区域。
- 单资产覆盖:本规格书覆盖一个资产(烘箱本体及其子部件),无多资产装配契约。

## 5. USD prim 树(Prim hierarchy)

命名与坐标约定下的建议 prim 结构(由第 4 节拆分表推导;坐标/单位/轴向与 [USD 布局规范](../../standards/usd-layout.md) 一致):

```text
/World/ika_oven_125              (default prim, kind=component)
├── Links/oven_body              (固定基座;700×825×650 外包络)
│   ├── shelf_0 .. shelf_5       (可插拔层架;各带 placement surface)
│   ├── control_knob_link        (面板右侧旋钮)
│   ├── mains_switch_link        (面板最左侧 rocker)
│   └── display                  (双 TFT 状态面;visual/state surface)
├── Links/door                   (实心门;独立质量与碰撞体)
│   └── handle                   (door child collider;竖直可抓取区)
├── Joints/door_hinge            (revolute,竖直轴,0–180°,阻尼/限位,可配置左右侧)
├── Joints/control_knob_rot      (revolute,连续或离散 detent)
├── Joints/control_knob_press    (prismatic/button,与旋转同一旋钮)
├── Joints/mains_switch_toggle   (toggle/rocker)
└── Collision/...                (门板、把手、前框、机身、层架碰撞体)
```

## 6. 关节契约(Joint contracts)

| 关节 | 类型 | 限位 | 驱动/阻尼 | 初始状态 | 状态输出 |
|---|---|---|---|---|---|
| `door_hinge` | revolute(竖直轴,默认右侧,可配置换向) | 0°(闭门)至约 180°(完全打开) | 设置合理惯量、阻尼、限位与接触;门不得做成无质量或无阻尼的轻质板(手册:门重约 15 kg,开关门存在夹伤风险) | 0°(闭门) | `door_angle`(0–180°)、closed/open/held 判定 |
| `control_knob_rot` | revolute(连续旋转关节或离散 detent) | 源文档未给限位(U,见待测清单 #4) | 待定 | idle | `temperature_setpoint` 变化;观测屏幕 setpoint |
| `control_knob_press` | prismatic/button(与旋转同一旋钮的按压动作) | 按压行程 U(待测清单 #4) | 按压后状态切换 | 未按压 | `heating_enabled`(idle → heating) |
| `mains_switch` | toggle/rocker(面板最左侧独立开关) | 两态 | 小尺度按压或拨动 | 任务未明确要求时不启用 | `mains_power`(on/off) |
| `shelf_0..5` | fixed(可插拔,静态 child) | — | — | 按参考配置含两层架 | 各 shelf 的 placement surface 接触状态 |

关节建模约束(源文档):碰撞体必须覆盖门板、把手和前框,避免机器人手臂穿透;不要额外虚构独立 Start 按钮(启动 = 按压同一旋钮);mains switch 与 start/stop 分开建模。

## 7. 建议状态量(State variables)

供评测/任务逻辑使用的推荐状态变量(源文档第 5 节"建议状态量"逐字转录):

| 状态量 | 类型 | 阈值/语义 |
|---|---|---|
| `door_angle` | float | 0–180°,同时提供 closed/open/held 判定阈值 |
| `door_grasped` | bool | 辅助臂与把手的有效抓取约束是否成立 |
| `container_on_shelf` | bool | 容器底面与目标 shelf surface 的稳定接触 |
| `temperature_setpoint` | float | 目标温度数值;由旋钮动作改变 |
| `heating_enabled` | bool | 按压旋钮后进入加热;与 `mains_power` 分离 |
| `mains_power` | bool | 总电源拨杆状态;仅在任务明确要求开/关机时启用 |

## 8. 交互语义(Interaction semantics)

### 8.1 控制面板 → 动作映射(源文档第 3 节,逐字转录)

![E11 控制面板特写](../../../external_artifacts/asset_evidence/ika-oven-125/image6.png)

E11 — 双 TFT、下方软键、Back/Menu、Light/Lock 与右侧旋转/按压旋钮。

| 任务语义 | 物理接口 | USD/评测建议 |
|---|---|---|
| 转动设置温度 | 右侧 rotary/push knob | 连续旋转关节或离散 detent;观测屏幕 setpoint |
| 按下启动 | 同一个 rotary/push knob 的按压动作 | 不要额外虚构独立 Start 按钮;按压后状态切换 |
| 开/关机 | 面板最左侧独立 rocker mains switch | 与 start/stop 分开建模;需要小尺度按压或拨动 |
| 菜单/返回 | 右侧小矩形 Menu / Back 按钮 | 可选交互;不是基础烘干流程的必要接口 |
| 照明/锁定 | Light / Lock 按钮 | 可作为 UI 扩展,不应混入基础任务成功条件 |

对原任务脚本的修正(源文档逐字):"转动旋钮设置温度 → 按下启动按钮"在这台设备上应解释为:转动同一旋钮改变设定值,再按压该旋钮确认/启动。若脚本末尾要求"关机按钮",应明确是停止加热还是拨动左侧总电源开关,两者不是同一动作。

### 8.2 LIFT2 分阶段操作语义(源文档第 4 节,逐字转录)

| 阶段 | 动作 | 成功判据 |
|---|---|---|
| approach/grasp(抓) | 辅助臂从把手中段建立稳定包络抓取 | 不得抓门板边缘;抓取后手-把手相对位姿稳定 |
| actuate-pull(拉) | 沿门的瞬时切向拉动,随铰链圆弧更新末端 | 不是直线平移;门角持续增加且机身不移动 |
| hold(保持) | 辅助臂保持门角和避障位姿 | 操作臂进入内胆时不与门/把手碰撞 |
| place(放置) | 操作臂将容器放到指定层架 placement surface | 容器底面稳定、位于边界内、无穿透 |
| actuate-push(推关) | 从门外侧/把手施力,沿反向圆弧闭合 | 门角回到阈值内;锁扣/门封接触成立 |
| set/start(设温/启动) | 转动并按压右侧旋钮 | 设定值达到目标;状态由 idle 切换到 heating |

安全与动力学(源文档逐字):手册指出更换门向时门重约 15 kg,并警告开关门存在夹伤风险。仿真不应把门做成无质量或无阻尼的轻质板;应为关节设置合理惯量、阻尼、限位与接触。

场景约束(源文档第 2 节):手册要求设备与墙体至少保持 150 mm 距离,并安装防倾倒固定件。若任务涉及拉门,仿真中至少应固定机身底座,最好加入防倾覆约束。

### 8.3 精确型号主视图(源文档第 2 节,建模与交互的几何依据)

闭门前右 3/4(E01 — 主几何参考:外壳、顶板、门体、左侧竖直把手、顶部控制箱):

![E01 闭门前右 3/4](../../../external_artifacts/asset_evidence/ika-oven-125/image1.png)

开门状态,articulation 主证据(E02 — 实心门打开;同时可见门厚、外侧把手、内胆口、层架与前框):

![E02 开门前左 3/4](../../../external_artifacts/asset_evidence/ika-oven-125/image2.png)

背面结构(E03 — 背面上部通风孔、电源入口、穿线/风道部件与下部风扇通风区):

![E03 背面右侧 3/4](../../../external_artifacts/asset_evidence/ika-oven-125/image3.png)

内胆正视与斜视(E04/E05;主要可见结构:侧壁多级层架导轨、后部风扇罩、内胆灯、圆形穿线/风道盖、黑色门封和前框;内胆净工作尺寸 550 × 525 × 450 mm,但照片透视不能替代实物测量):

![E04 内胆正视](../../../external_artifacts/asset_evidence/ika-oven-125/image4.png)
![E05 内胆斜视与门边](../../../external_artifacts/asset_evidence/ika-oven-125/image5.png)

### 8.4 LIFT2 操作局部(源文档第 4 节)

![D01 把手与门边裁切](../../../external_artifacts/asset_evidence/ika-oven-125/image7.png)
![D02 门框/扣件裁切](../../../external_artifacts/asset_evidence/ika-oven-125/image8.png)

D01 把手与门边裁切;D02 门框/扣件裁切。两张局部图均由 E02 裁切,**不是新的测量视图**。它们只帮助确定抓取方向、门厚层次和碰撞体拆分;绝对尺寸仍需 CAD、实测或已知外形尺寸配合标定。

## 9. 验证矩阵与失败模式(QA matrix & failure modes)

本规格书为格式转换稿,生成管线尚未执行;全部检查项按 GEN-007 标 `NOT_TESTED`,不得留空或写成通过。

| 检查 | 类型(static/reopen/runtime/robot) | 结果 |
|---|---|---|
| 静态契约检查(skill `check_articulation_usd.py`,GEN-005) | static | `NOT_TESTED` |
| USD 重开/渲染外观检查(对照 E01–E05) | reopen | `NOT_TESTED` |
| 门铰链 0–180° 行程、阻尼、限位 | runtime | `NOT_TESTED` |
| 机身固定/防倾覆约束下拉门机身不移动 | runtime | `NOT_TESTED` |
| 把手中段包络抓取稳定性 | robot | `NOT_TESTED` |
| 切向拉门圆弧轨迹(非直线平移) | robot | `NOT_TESTED` |
| 容器放置于层架 placement surface(稳定、边界内、无穿透) | robot | `NOT_TESTED` |
| 旋钮旋转改 setpoint、按压切换 idle→heating | runtime | `NOT_TESTED` |
| mains switch 独立两态(与 start/stop 分离) | runtime | `NOT_TESTED` |

高概率失败模式(由源文档约束与既有经验归纳):

- 机器人手臂穿透门板/把手/前框(碰撞体未覆盖三者)。
- 门被做成无质量或无阻尼的轻质板,导致力控开门与保持失真(手册:门约 15 kg、夹伤风险)。
- 拉门做成直线平移而非随铰链圆弧的切向运动。
- 拉门时机身滑动/倾覆(底座未固定、无防倾覆约束;手册要求 150 mm 墙距与防倾倒固定件)。
- 抓取落在门板边缘而非把手中段。
- 虚构独立 Start 按钮(本机启动 = 按压同一 rotary/push knob);混淆"停止加热"与"拨动总电源开关"。
- 把玻璃门同系列(G01–G03)的玻璃窗、门厚、质量照搬到实心门目标。
- 把不同来源压缩图(E06–E10)当成新视角引入几何冲突。
- 由 D01/D02 裁切图标定绝对尺寸(裁切图不是独立拍摄)。
- 整个内胆设为单一模糊目标区,未建逐层 placement surface 与安全内缩。

## 10. 交付与命名规范(Delivery conventions)

- 文件命名:资产 slug `ika-oven-125`;prim 命名见第 5 节(`oven_body` / `door` / `door_hinge` / `handle` / `shelf_0..5` / `control_knob` / `mains_switch` / `display`)。
- 坐标/单位/轴向:与 [USD 布局规范](../../standards/usd-layout.md)(USD-001)一致;尺寸一律以第 3 节冻结表(mm)为准,禁止从照片像素推导。
- 打包形式:生成产物只经 ConvertAsset 准入边界进入场景(GEN-001/ASSET-001);生成的 USD、证据图片与检查报告只存 `external_artifacts/` 并登记哈希(GEN-004/GEN-005)。entrypoint 与 closure 细节在首轮生成时按准入要求确定(当前无已生成产物)。
- 证据存放:图片只存 `external_artifacts/asset_evidence/ika-oven-125/`(GEN-004),索引见 [external_artifacts README](../../../external_artifacts/README.md)。

## 11. 待测清单(Open measurements)

所有 U 级字段及首轮建模前后必须实测的项(源文档第 8 节"建模前仍需补拍/实测"逐字转录):

| 项 | 等级 | 计划如何获得 |
|---|---|---|
| 严格左右侧正视(现有图以 3/4 视角为主,透视无法给出侧板细节) | U | 相机与侧板平行拍摄,包含标尺 |
| 把手截面与离门距离(决定 LIFT2 抓取包络和碰撞体) | U | 卡尺量外径、净空、上下安装点 |
| 铰链轴线与门质量参数(决定门的圆弧轨迹、力矩和保持难度) | U | 测轴线位置、门质量/开启阻力 |
| 旋钮直径/按压行程(决定 rotate/press 接触几何) | U | 正视 + 侧视微距,标尺或卡尺 |
| 层架高度与前缘净空(决定容器可达性和放置容差) | U | 逐层测量导轨高度、层架尺寸 |
| 机身固定方式(双臂开门会对箱体施加反力) | U | 记录防倾倒支架与台面/墙体约束 |

源文档最终建议(逐字):现有图片足够制作外观级 USD、门关节、把手抓取区、内胆层架和控制面板的第一版;若要做接触稳定、力控开门和真实成功阈值,仍需上述关键尺寸实测。

## 12. 图片清单(Image inventory)

图片只存 `external_artifacts/asset_evidence/ika-oven-125/`(GEN-004)。抽取文件与 docx 内嵌媒体经 SHA-256 逐字节比对**全部一致**(18/18),故 docx 图片 ID 到抽取文件的映射按其文档内位置(标题上下文)确定,置信度高;唯 E06–E10 等"同视角替代图"的映射依赖文档顺序,标注"顺序映射,待人工核对"。

| 图片 ID | 等级 | 来源 | 使用边界 | 相对路径 | SHA-256 |
|---|---|---|---|---|---|
| E01 | E(EXACT 目标实心门型号) | Pipette exact-model page | 外形主参考:整体比例、外壳、门、把手、控制区 | `external_artifacts/asset_evidence/ika-oven-125/image1.png` | `6076b4ea89378556a0860e2cbd9c4146572fbe1ddfe32893427c56afcf13ec8d` |
| E02 | E(EXACT 目标实心门型号) | DirectIndustry exact-model gallery | articulation 主证据:门铰链、门厚、开启方向、内胆关系 | `external_artifacts/asset_evidence/ika-oven-125/image2.png` | `a19453cc33ec01a0502e2faeb9cc67a31f81e00b84b9e6f4bfbe408b694d48fd` |
| E03 | E(EXACT 目标实心门型号) | Pipette exact-model page | 背板、通风孔、电源接口、穿线孔 | `external_artifacts/asset_evidence/ika-oven-125/image3.png` | `661163302b1d20aba6559e256ac9e1e5aaa583e4927ec1f25129de5c6f503508` |
| E04 | E(EXACT 目标实心门型号) | Pipette exact-model page | 层架导轨、风扇罩、灯、密封圈、内胆 | `external_artifacts/asset_evidence/ika-oven-125/image4.png` | `1ccf3fab419d6bbd8828459bb827629dbc83679f5fb2a1a5710499ebe2d5694b` |
| E05 | E(EXACT 目标实心门型号) | Pipette exact-model page | 内胆深度、侧导轨、门框、密封条 | `external_artifacts/asset_evidence/ika-oven-125/image5.png` | `98abb6ec5c7dc989d448a6fc636301a810c867266d110d025c4a52164ca7ca11` |
| E06 | E(EXACT 同目标替代压缩图) | DirectIndustry exact-model gallery | 轮廓交叉核验(与 E01 同视角,来源交叉核验;顺序映射,待人工核对) | `external_artifacts/asset_evidence/ika-oven-125/image13.png` | `b3b4b68dfc85fb53b7e4a8ac6c1738a7e19f8087e4a8b5539ea37679b53106ee` |
| E07 | E(EXACT 同目标替代压缩图) | DirectIndustry exact-model gallery | 背面轮廓交叉核验(与 E03 同构图;顺序映射,待人工核对) | `external_artifacts/asset_evidence/ika-oven-125/image14.png` | `307332c154a4c2e4cf1f54893879e3e898fef15dd7f3efd88d1d88e3cac14376` |
| E08 | E(EXACT 同目标替代压缩图) | DirectIndustry exact-model gallery | 内胆结构交叉核验(与 E04 同构图;顺序映射,待人工核对) | `external_artifacts/asset_evidence/ika-oven-125/image15.png` | `83c6928fa2f384e32feb535a7d965969a13f05bba372d5a4a1b0a25a55d4ac21` |
| E09 | E(EXACT 经销商页面同型号) | Medsolut 经销商页 | 整体轮廓交叉核验(800 px,信息增量有限;顺序映射,待人工核对) | `external_artifacts/asset_evidence/ika-oven-125/image16.png` | `b6b736d6c9ae2360de34f7ab75483b02ff03289f78e36d39870802dbecbe1da7` |
| E10 | E(EXACT 经销商页面同型号) | LabFriend 经销商页 | 材质色调与总体轮廓(色彩偏冷,几何与 E01 一致;顺序映射,待人工核对) | `external_artifacts/asset_evidence/ika-oven-125/image17.png` | `b4dd3a61a67660ca1842d748d82a293792028197965cf8deb988cf7fdb30f3f1` |
| E11 | E(EXACT 官方产品册内目标控制型面板) | IKA 2025 Oven 125 产品册 control-dry 页面 | 旋钮、屏幕、软键、按钮布局 | `external_artifacts/asset_evidence/ika-oven-125/image6.png` | `403ae43fcc37f13215356316a6dbe30dfd711248aa36bfa3a6586980febdefdc` |
| F01 | F(FAMILY 实心门系列参考) | IKA 2025 Oven 125 产品册(系列产品册提取) | 仅用于门体、内胆与开启姿态交叉核验;面板 UI 非目标 control-dry,不能作为 exact-model 证据 | `external_artifacts/asset_evidence/ika-oven-125/image18.png` | `d9e0cfa2e218f216377e970278cc0d2c939e247b1362cf661fc451286901042f` |
| G01 | F(SIBLING control-dry glass,非目标门体) | Pipette control-dry glass 产品页 | 仅供共用机身与控制区参考;不得用其玻璃门外观替代目标实心门 | `external_artifacts/asset_evidence/ika-oven-125/image9.png` | `c1ee122784d23c868ec3f87c39044d3a84aa05eb70ca9391035bb9c19ebf1228` |
| G02 | F(SIBLING control-dry glass,非目标门体) | Pipette control-dry glass 产品页 | 门框隐藏结构和内胆照明辅助参考;内胆大体共用,门体结构不可照搬 | `external_artifacts/asset_evidence/ika-oven-125/image10.png` | `7f92a318d87da7b545390fe186efa657ad805a494347856841476602448b952e` |
| G03 | F(SIBLING/SHARED dry glass 视频帧) | DirectIndustry 产品页(dry glass 视频帧) | 屏幕 UI 与旋转/按压旋钮辅助参考;控制面板可作共享子系统参考 | `external_artifacts/asset_evidence/ika-oven-125/image11.png` | `4337c1749c7d7f1cc4192e3a0605433764d50e5f4083c95caccb515ccb31d13a` |
| D01 | D(DERIVED,由 E02 裁切) | 由 E02 原图裁切 | 把手与门边局部;确定抓取方向、门厚层次、碰撞体拆分;非独立拍摄,不能用于绝对尺寸标定 | `external_artifacts/asset_evidence/ika-oven-125/image7.png` | `c1ada8f06217dc23bf3e2b2aee4a62479fdd56e702180168db1b851fbdd75acd` |
| D02 | D(DERIVED,由 E02 裁切) | 由 E02 原图裁切 | 门框/扣件局部;同上 | `external_artifacts/asset_evidence/ika-oven-125/image8.png` | `54cd43b91908d49abeb51b06a73546e1d2c331278e3acd15f6421ffcd58209a8` |
| (总览拼版,无 ID) | —(E/F/G 分类总览) | 源文档生成的 15 张来源图拼版 | 全部采集图总览;请按 E / F / G 分类边界使用;不作独立建模证据 | `external_artifacts/asset_evidence/ika-oven-125/image12.png` | `eb669bcabffdadbc4a40c74c699c666abd5f0f4d0e2cfdfaca5480c9c5b93016` |

玻璃门同系列辅助参考(源文档第 6 节警告,逐字):G01–G03 不是目标实心门版本。只允许用于共用机身、控制面板或内胆隐藏结构判断;任何玻璃窗、门板厚度和质量都不能直接复制。

![G01 玻璃门同系列闭门](../../../external_artifacts/asset_evidence/ika-oven-125/image9.png)
![G02 玻璃门同系列内胆](../../../external_artifacts/asset_evidence/ika-oven-125/image10.png)
![G03 控制面板视频帧](../../../external_artifacts/asset_evidence/ika-oven-125/image11.png)

### 12.1 docx 登记的像素尺寸与源文件哈希(保真转录)

源文档第 7 节逐图目录为每张来源图登记了像素尺寸与 SHA-256。该哈希与 docx 内嵌副本(= 本仓库存放文件)的 SHA-256 **不一致**,应理解为原始下载源文件的哈希;本仓库以上表 MANIFEST 哈希为准(GEN-004)。

| 图片 ID | 像素(docx 登记) | 源文件 SHA-256(docx 登记) |
|---|---|---|
| E01 | 1000 × 960 | `f348ebb2ca8df28bd3ae00f6ce0fc0c6cf628efb3236eba02537cf8d6732487f` |
| E02 | 1000 × 1000 | `2860a820d041c54e75f0834b3103f3de6ffe42bc82d5a10324c2ee4f929f5a22` |
| E03 | 1000 × 1000 | `a8ebdfc1ef9edfd9fde1cf3eb52c44cd24741b1d361a9658006fa01118232f66` |
| E04 | 1000 × 1000 | `711baa676918dd1ebf071958c86d497c2acea3c9872ffd5bee94ee72fcfe5977` |
| E05 | 1000 × 947 | `2688f79164974e2e8b51852737a9b5608951e062763a457b04b94bca71631d1c` |
| E06 | 898 × 898 | `ea0f47fa0037caeb30e9be0b493654c105f2d515be010f668f81ff0a3239d37c` |
| E07 | 1000 × 1000 | `044844405cfdc44fbcba4812e36ce96808853f2065282b932d5ede1e5d5e5f74` |
| E08 | 1000 × 1000 | `6a6d32264cec0bb86263b28ff7f628d8697484211eea56d407aea7704fa03b41` |
| E09 | 800 × 800 | `d1631d07609485013aeb67dcc82798c1d5bbaa70235bb44a1b20ced48f14736c` |
| E10 | 1000 × 1000 | `1adc304ca15f27a7f2df318e5764a291148f00539079b43e3fb0bf64a6c3e3d5` |
| E11 | 459 × 209 | `f878d5192fd12cfebbd55c22bcc77f4b308ab1539ef40985d976b2186aa1ce3e` |
| F01 | 480 × 435 | `6813d8430f3341a7270f8b96a430536109d3bfc7de3a32d7d711e724bbe0e2bc` |
| G01 | 1000 × 960 | `0e35a3864e35ab49ea19fe5869d47a0d984a25557a1f51484f2f81c1a5bcdb4a` |
| G02 | 1000 × 1000 | `b9533882811229f5b1d3e65e4df7d6b9503545b04a8209271cb4acbb044c320c` |
| G03 | 720 × 406 | `ac04d1ddc428c041f14005bd5018b76835eb34fc75ad4538f3b626f5c432782f` |
| D01 / D02 / 总览拼版 | docx 未登记 | docx 未登记 |

源文档完整性说明(逐字):共 15 张来源图。绿色 E 为目标或同目标替代图;橙色 F/G 为系列、相似型号或共享子系统参考。后续逐图目录会把每一张来源图作为独立媒体嵌入 DOCX;ZIP 同时保留独立文件、来源 URL、像素尺寸和 SHA-256。

### 12.2 逐图身份卡片(源文档第 7 节,逐字转录)

| 图片 ID | 标题 | 身份与用途说明 |
|---|---|---|
| E01 | 闭门前右 3/4 | EXACT — 目标实心门型号:目标型号主视图;作为外形主参考。建模用途:整体比例、外壳、门、把手、控制区 |
| E02 | 开门前左 3/4 | EXACT — 目标实心门型号:目标实心门打开状态;对 articulation 最关键。建模用途:门铰链、门厚、开启方向、内胆关系 |
| E03 | 背面右侧 3/4 | EXACT — 目标实心门型号:高分辨率背面参考。建模用途:背板、通风孔、电源接口、穿线孔 |
| E04 | 内胆正视 | EXACT — 目标实心门型号:内胆正投影;用于内部结构和 shelf slot。建模用途:层架导轨、风扇罩、灯、密封圈、内胆 |
| E05 | 内胆斜视与门边 | EXACT — 目标实心门型号:开门局部;可见右侧门内缘。建模用途:内胆深度、侧导轨、门框、密封条 |
| E06 | 闭门正侧替代图 | EXACT — 同一目标型号的替代压缩图:与 E01 同视角,保留用于来源交叉核验。建模用途:轮廓交叉核验 |
| E07 | 背面替代图 | EXACT — 同一目标型号的替代压缩图:与 E03 同构图,色调与压缩不同。建模用途:背面轮廓交叉核验 |
| E08 | 内胆替代正视 | EXACT — 同一目标型号的替代压缩图:与 E04 同构图,保留不同图源版本。建模用途:内胆结构交叉核验 |
| E09 | 闭门经销商图 | EXACT — 经销商页面同型号:800 px 经销商图,信息增量有限但身份明确。建模用途:整体轮廓交叉核验 |
| E10 | 闭门高质量替代图 | EXACT — 经销商页面同型号:1000 px 图,色彩偏冷;几何信息与 E01 一致。建模用途:材质色调与总体轮廓 |
| E11 | 控制面板特写 | EXACT — 官方产品册内目标控制型面板:从 2025 IKA Oven 125 产品册的 control-dry 页面提取。建模用途:旋钮、屏幕、软键、按钮布局 |
| F01 | Oven 125 系列开门视图 | FAMILY — 实心门系列参考,控制面板不是目标 control-dry:从系列产品册提取;UI 与目标控制面板不一致,不能作为 exact-model 证据。建模用途:仅用于门体、内胆与开启姿态交叉核验 |
| G01 | 玻璃门同系列闭门 | SIBLING — control-dry glass,非目标门体:不得用其玻璃门外观替代目标实心门。建模用途:仅供共用机身与控制区参考 |
| G02 | 玻璃门同系列内胆 | SIBLING — control-dry glass,非目标门体:内胆大体共用;门体结构不可直接照搬。建模用途:门框隐藏结构和内胆照明辅助参考 |
| G03 | 控制面板视频帧 | SIBLING/SHARED — control-dry glass 视频帧:画面明确写有 dry glass;控制面板可作共享子系统参考。建模用途:屏幕 UI 与旋转/按压旋钮辅助参考 |

## 13. 来源与许可(Sources & licensing)

- 来源登记(docx 内"打开来源页面"超链接逐一解出,按用途区分边界):

| 来源 | URL | 用途边界 |
|---|---|---|
| IKA/Pipette 产品数据表 | <https://cdn.pipette.com/docs/ika/Data_Sheet_IKA_OVEN_125_control_-_dry_Drying_oven.pdf> | 冻结规格数值(E 级) |
| IKA 2025 Oven 125 产品册 | <https://cdn.pipette.com/docs/ika/20250904_Oven_210x280_IWW_EN_websingle.pdf> | 型号身份(Ident No. 0020003991)、E11 面板图、F01 系列图 |
| IKA Oven 125 control 操作手册 | <https://cdn.pipette.com/docs/ika/20000023854a_EN_Oven%20125%20control_082021_web.pdf> | 门开启角/换向、门重约 15 kg、150 mm 墙距与防倾倒、夹伤风险 |
| Pipette exact-model page(control-dry) | <https://pipette.com/product/ika-works-oven-125-control-dry-drying-oven-0020003991.html> | E01、E03、E04、E05 |
| DirectIndustry exact-model gallery | <https://www.directindustry.com/prod/ika/product-28268-2000065.html> | E02、E06、E07、E08、G03(视频帧) |
| Medsolut 经销商页 | <https://medsolut.com/en/p/ika-drying-oven-oven-125-control-dry/> | E09 |
| LabFriend 经销商页 | <https://www.labfriend.com.au/ika-drying-oven-125-control-dry-max-300c-incl-two-shelves> | E10 |
| Pipette control-dry glass 产品页 | <https://pipette.com/product/ika-works-oven-125-control-dry-glass-drying-oven-0020003997.html> | G01、G02(仅同系列辅助参考) |

- 许可提醒(源文档逐字):图片来自 IKA 产品资料及公开经销商/行业目录页面,仅用于本项目内部资产重建、几何核验与评测设计。对外发布或商业再分发前,应另行确认图片使用权与品牌标识要求。
- 补充:生成 USD 不得复制 IKA 商标/品牌标识用于对外再分发;品牌相关呈现需求在准入前另行确认。
