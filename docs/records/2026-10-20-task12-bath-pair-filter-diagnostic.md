# 浴液—试管接触过滤诊断与显色候选复核

状态：显色候选5条关键阶段已目视复核，形成局部显色结论；接触过滤ABBA正在GPU0运行，尚无因果结论。未交付、未全量重评。已有128条的全量共同语义复核仍未全部完成。

## 边界和失败保留

用户明确最终交付仍保留浴液—试管真实交互。以下过滤只用于私有诊断，不能进入生产USD或作为成功示范。显色提前0.75秒候选继续冻结；物理诊断从原contact_correlation2参考版派生，不混入计时、居中或扩孔修改。

关闭整个BathSystem的旧B组在初始化阶段报NpPBDParticleSystem::removeParticleBuffer错误，动作前已停止。未屏蔽错误、未修改PhysX/GenManip；运行记录、服务/worker日志及哈希另存个人repair的evidence/bath_disabled_initialization_failure。原停止队列保留，不原样重试。

远端直接用/isaac-sim/python.sh读取pxr文档失败，因为该方式未加载Kit扩展路径；不安装替代SDK。随后只读检查安装版本测试文件`/isaac-sim/extsPhysics/omni.physx.tests/omni/physxtests/tests/PhysxParticleAPI.py`，其中在particle system应用FilteredPairsAPI、过滤指定碰撞面，并检查粒子能穿过该面。此为安装版本用法依据，本轮没有执行该上游测试，不能冒称本任务过滤已生效。通用语义参考[Omni Physics pair filtering](https://docs.omniverse.nvidia.com/kit/docs/omni_physics/104.0/source/extensions/omni.physx/docs/index.html)。

## 新的私有ABBA

个人工作根R为`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/task12_liquid_color_20261012`。身份为R/evidence/bath_filter_{0_A,1_B,2_B,3_A}_identity.json。

保持浴液和样液粒子系统均enabled。A保留原25个过滤目标；B保留这25个目标，并加入试管下全部474个启用碰撞体，共499个目标。逐个核对最近RigidBodyAPI归属为obj_sample_tube，目标不扩展到烧杯、夹爪或其他对象。玻璃、保液侧壁/底部均包含，不只过滤可见外壳。

静态比较确认：归一化诊断trace路径后，两份A内容相同、两份B内容相同；A/B只差BathSystem的filteredPairs关系覆盖，系统开关、固体碰撞、质量、材料、动作、metric不变。A从引用层继承原关系，因此最初按文本占位符替换的比较未通过；修正为去除该覆盖后检查剩余完整文本一致，未放宽差异范围。见evidence/bath_filter_static.json。

相同只读测量记录每次调用的浴液/样液开关及过滤目标哈希，并每100次调用采样启用的试管碰撞体和未覆盖目标。计数是compute调用，不当作物理时间。B完成后若运行期有启用碰撞体未覆盖、哈希变化或系统被停用，则分析停止，不能作否定PBD的证据。

10.150.164.127（公网877）GPU0依次运行A→B→B→A，mixed5原动作前1200步，原生120Hz及既有chunk8/底座分段映射不变。初始监督PID3388909，分析PID3388910；权威状态`/tmp/task12_four4090_20261019/bath_filter/queue.json`，分析状态R/evidence/bath_filter_analysis/status.json。实际已看到第一条A持续step_chunk、trace中的两个系统均true、25个过滤目标及25个机器人DOF。B初始化与配对结果仍待完成。

后处理沿用精确16维状态+底座+等价物体位姿组。匹配/过滤覆盖通过也不等于获得直接粒子力测量；还须比较A/B重复与580–800原生画面。过滤无改善只能评价直接浴液—试管路径，不能排除通过烧杯/夹爪的间接作用。

## 显色候选的局部结论

evidence/completion075_visual_review/visual_review.json记录实现者目视结论与图片哈希，非独立审查。5条原生结果及运行版本3/提前量0.75的检查来自completion075_runtime_summary.json。

- 来源11、15：可见样液推进到橙红色，松爪撤手后试管保留在架内；原生均1分。来源15的下层落座深度未独立量测，不扩大到保液或连续碰撞资格。
- 来源9：显色可见且95%条件达标；回架过程中严重倾斜、落位失败，仍保留0.85分和失败，不以计时修复掩盖操作问题。
- 来源12：显色可见且95%条件达标；松爪后外观接近竖直，但原生回架条件false。落座深度/槽位几何尚未核清，保留0.85与待确认，不直接断言metric错误或已正确回架。
- mixed5：样液仍蓝且较高/倾斜，末段试管在架外桌面，保持0.15负例。

显色时间修改可作为后续合并的局部修复保留；不是水浴任务整包可交付。初始化/重置/重新随机化的统一映射已有8项辅助测试，本轮未新增完整运行时重置系列。最终文件需继续绑定冻结身份哈希。

规范依据STATE-001..004、MAT-003、VAL-001..005/008及维护流程。无核心API/schema变化；工具留在R/tools，诊断不进入接收包。过滤目标与0.75秒规则均为任务特定，不产生通用规范变化，规范无需变更。未运行核心make check，未修改机器人、SDK、GenManip核心或生产metric。
