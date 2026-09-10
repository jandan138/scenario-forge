# Articulation 场景制作规范

状态：当前。`ART-001` 至 `ART-004` 的结构要求适用于项目已验证的**固定基座 articulated Instance v2** 路线，
包括相应烘箱资产的场景导出。它不是任意 articulation 的 OpenUSD/PhysX 通用结构规定。

## 强制要求

<a id="art-001"></a>
### ART-001 — 固定基座 v2 的标准层级

```text
<existing-prefix>/<obj_root>          placement Xform + Articulation Root
└── Instance                         identity Xform
    ├── Body                         non-kinematic rigid base link
    ├── <other rigid links>           non-kinematic
    └── Joints
        └── BaseFixed                obj_root -> Instance/Body
```

`obj_*` 上有 `PhysicsArticulationRootAPI` 和启用的 PhysX articulation。
`Instance` 是 identity `Xform`；所有 `RigidBodyAPI` links 位于其下，且为 non-kinematic。
`Instance/Body` 是刚体基座。`Instance/Joints/BaseFixed` 的 body0 指向对象根，body1 指向 `Instance/Body`；
其他内部关节 body 目标位于 `Instance` 内，目标不得悬空。
生产者拥有这些物理内容，消费者检查并使用；不在 Scenario Forge 中临时添加 articulation root、切换 link 的 kinematic 属性或补固定关节。

依据：[v2 验证测试](../../tests/test_articulated_instance_layout.py)、
[问题与交付证据](../records/2026-09-04-fixed-base-articulated-instance-v2-and-oven-handoffs.md)。

<a id="art-002"></a>
### ART-002 — 区分场景摆放与资产内部装配

保留既有前缀和 `obj_*` placement root；场景摆放、GUI 移动、被契约允许的统一资产尺度与随机化由对象根拥有。
不要给 `Instance` 或各 link 叠加场景级摆放和随机偏移。
**资产内部已有的 link、关节、视觉和碰撞局部装配变换仍需保留**；本规则不要求每个 link 的局部变换都为 identity。

依据：[VR 变换保真记录](../records/2026-08-23-vr-object-materialization-and-transform-correction.md)、
[物化测试](../../tests/test_vr_object_materialization.py)。

<a id="art-003"></a>
### ART-003 — 完整注册，根级随机化

VR `task_config.py:obj_prim_list` 按确定的 USD 遍历顺序注册运行时对象根，随后注册所有刚体 link
（every `RigidBodyAPI` link）：

```text
/World/_scene/obj_device
/World/_scene/obj_device/Instance/Body
/World/_scene/obj_device/Instance/<link>...
```

关节、视觉 mesh、材质和 collider 子节点不是独立 link，不分别注册。
仅对象根进入 `layout_randomization`；links must never be randomized independently。
设备与承托车可以共享根级随机化组，但不能因此再单独随机化它们的子 link。
注册可交互路径不等于获得该子节点的场景变换所有权。

依据：[注册测试](../../tests/test_vr_articulated_registration.py)、
[注册实现记录](../records/2026-09-04-vr-articulated-link-registration.md)。

<a id="art-004"></a>
### ART-004 — 拒绝把旧布局当成 v2

旧 v1 的 `Scope Instance`、可保留 kinematic chassis 的形式仅作 legacy 兼容和历史输出解释。
进入新 v2 导出路线前，资产须由生产者生成并验证适用的新版本；不能只换标签。
v2 验证应拒绝根缺失/禁用、非 identity `Instance`、缺失或 kinematic link、错误 BaseFixed 及越界内部关节目标。

依据：[v2 负例测试](../../tests/test_articulated_instance_layout.py)。

<a id="art-005"></a>
### ART-005 — 关节值、重置与运行时一致

使用 articulated-device 能力时，按 [来源绑定接口](../design/scenario-source-bindings.md) 核对 DOF 名称、
关节类型、限制、度/弧度转换、命名状态及范围内的重置值。静态结构通过后，仍需对应目标运行时的运动/重置证据。
只检查 USD 文件或注册列表不能宣布关节交互合格。

## 推荐做法

<a id="art-006"></a>
### ART-006 — 把结构和运动证据分开记录

同时保留结构检查、目标运行时、安装前缀、实际 DOF 轨迹/状态及重置结果。
优先引用生产者已验证的 canonical、任意前缀和 VR 挂载证据，再验证最终场景；复用范围按 [VAL-002](validation-and-delivery.md#val-002)。

## 已知限制

自由基座、特殊闭环、其他关节拓扑和其他 runtime 不因本页而自动合格；缺少证据时明确写“未覆盖”。
烘箱记录中的直接场景测试与生产者继承的版本兼容证据需区分，不能称全部 runtime 都经过同样场景测试。
滴定 r1.6 验证了其自身设备和材质行为，但不能拿来证明所有固定基座 v2 布局。

变更记录：2026-09-08 将原设计文档中的制作规则迁到本页，明确固定基座范围，保留原设计路径用于解释与导航。
