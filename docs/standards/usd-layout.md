# USD 场景组织规范

状态：当前。适用于场景集成；VR r10.1、固定基座 v2、EBench tabletop 规则分别限定到相应导出路线。

## 强制要求

<a id="usd-001"></a>
### USD-001 — 先选接口和运行时

声明所用场景/导出契约、目标运行时与资产版本，再组织 USD。
编译器输入输出、单位及 `up_axis` 字段按 [USD 编译器契约](../design/usd-scene-compiler.md)，
overlay 顺序按 [overlay 接口](../design/scene-asset-overlays.md)。不得根据渲染大小猜测单位或局部补缩放来掩盖来源不明。
场景导出的 `/World` 约定不能强加到所有源资产的 defaultPrim 上。

<a id="usd-002"></a>
### USD-002 — 可迁移引用与有效路径

交付入口、material binding、关系、关节和 Shader 连接必须能解析到预期目标。
最终包依赖按 [VAL-003](validation-and-delivery.md#val-003) 检查闭包；
可移植交付中的 USD、MDL、纹理依赖使用包内相对路径，不依赖制作者机器上的绝对路径。
通过关系查找业务目标是推荐接口；改名或合并 Prim 后须更新所有实际引用和读取方。

依据：[滴定单材质改造](../records/2026-09-07-titration-r16-single-material.md)、
[对应测试](../../tests/test_titration_r16.py)、[包闭包测试](../../tests/test_package_closure.py)。

<a id="usd-003"></a>
### USD-003 — VR 源路径与挂载路径分离

r10.1 scientific-workbench VR 直接打开入口为 `/World`，`defaultPrim` 对应根 `World`；
源文件不预建 `/World/_scene`。前者含 `background`、`table`、`obj_*`，以及
`vr_direct_open_light`（无纹理白色 DomeLight，intensity 750）。
`_scene` 由 VR loader 挂载，因此 config 注册路径是 `/World/_scene/obj_*`。
普通对象与 context prop 按对应导出契约注册；关节对象按 [ART-003](articulation.md#art-003)。

普通注册路径对应源场景中其可移动的 `obj_*` Xform；注册的 articulation links 则位于对应对象根下。
每个普通 `obj_*` 恰好注册一次并进入一次根级布局分组；该 r10.1 默认局部 XY 随机化范围为各 ±0.01 m、yaw 为零。
需要保持关系的对象共组。PBD runtime 等非 `obj_*` helper 是否随组移动以已验证任务的具体绑定为准，不能随意独立随机化。

依据：[VR 导出操作说明](../operations/export-vr-teleop-package.md)、
[物化记录](../records/2026-08-23-vr-object-materialization-and-transform-correction.md)。

<a id="usd-004"></a>
### USD-004 — 物化保持组合结果

上述 VR 路线将发布的 tabletop `obj_*` 完整对象子树物化，不在其内保留 references、payloads 等 composition arcs。
房间、桌子、机器人、灯光和 PBD helper 不自动属于这条物化要求。
保持组合后的变换、材质、碰撞及物理内容；不要求重写为统一 xform 栈，也不能清空合法资产内部变换。
记录 source/runtime 路径、物化范围、非变换内容指纹与变换等价性，并绑定到交付证据。

依据：[物化测试](../../tests/test_vr_object_materialization.py)、[ART-002](articulation.md#art-002)。

<a id="usd-005"></a>
### USD-005 — 标准桌子的 VR 呈现覆盖

标准工作台 VR 导出隐藏组合 tabletop 的 `Surface/Source/mesh` 视觉，保持 active、变换、材质和碰撞。
已支持 canonical `/World/table/Surface/Source/mesh` 和 legacy `/World/table/table/Surface/Source/mesh`；
两者都找不到时该标准桌路线不能假装覆盖成功。自定义 VR 生成器也要在哈希/打包前调用
`apply_standard_workbench_vr_presentation`。这不是 EBench 导出的全局隐藏规则。

依据：[VR 操作说明](../operations/export-vr-teleop-package.md)、[标准桌测试](../../tests/test_scientific_workbench_standard_table.py)。

<a id="usd-006"></a>
### USD-006 — 桌面放置按适用的域策略验收

`scientific_workbench.robot_facing_tabletop.v1` 适用于声明桌面初始支撑的任务设备，不包括房间、桌子、机器人和纯背景物。
完整视觉 footprint 距所有桌边至少 0.10 m。面向机器人一半由桌面中心到 robot.spawn 的水平向量确定，不硬编码世界轴。
不在该半边的对象需提供非空 `tabletop_placement_exception` 理由；它只能豁免选边偏好，不能豁免 0.10 m 边距。
使用组合后的世界 bounds，记录桌面、机器人、footprint、边距和例外；不能凭对象 origin 断言摆放合格。

域 pack ID、证据路径和集成接口见 [tabletop 设计](../design/scientific-workbench-tabletop-placement.md)。
验证依据还包括 [tabletop 放置测试](../../tests/test_tabletop_placement.py)。
本规则只证明初始摆放，不证明可达、抓取、无碰撞轨迹或任务成功。

## 推荐做法

<a id="usd-007"></a>
### USD-007 — 用已有适配器处理布局与物化

先引用已验证的组装、物化和呈现工具；需要新策略时提交设计与对应验证，避免每个任务新增隐式坐标修补。
迁移后同时核对直接打开与目标导入的对象定位；不要把 GUI 看起来对齐当作变换等价证明。

## 已知限制与变更记录

不同导出配置的灯光、物理设置和随机化数值可能不同；上面的 r10.1 数值不推广到所有场景。
2026-09-08 汇集既有制作约束，保留编译器/overlay/域 pack 的 API 定义位置。
