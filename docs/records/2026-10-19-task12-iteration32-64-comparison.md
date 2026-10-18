# 水浴32／64位置迭代上限完整回放对照

状态：冻结和静态检查完成；新机旧包校准已启动，六轮候选尚未运行。实际启动时间以UTC原生日志为准（2026-10-18T16时段）；本文按本轮会话日期归档。

## 用户决定和依据

用户选择最终USD尽量不加入诊断读回，metric继续只评分。历史同参数短测与完整回放曾出现显著前缀差异，32版本也有成功和失败，因此本轮不以300步偶然改善作为晋级条件。仅比较MaxPositionIterationCount32与64，各三次独立冷启动，顺序32-A、64-A、64-B、32-B、32-C、64-C。保持min1、120Hz、7000步cap、原3722帧命令及尾帧保持协议、真实液体配方、碰撞、摩擦、显色规则和metric。

当前机器人代码请求位置128／速度4，既有YAML指定机器人静/动摩擦2.5、combine=max。场景max会限制更高actor请求，这是已安装4.1 schema的语义，不是内部实际求解次数的直接读数，也不是64一定有效的证明。参考[PhysX Scene API](https://docs.omniverse.nvidia.com/kit/docs/omni_usd_schema_physics/latest/physxschema/class_physx_schema_physx_scene_a_p_i.html)和[GPU求解说明](https://docs.omniverse.nvidia.com/kit/docs/omni_physics/latest/dev_guide/simulation_control/simulation_control.html)，实际采用以本任务运行证据为准。

## 版本和边界

根目录为`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/task12_liquid_color_20261012`。`evidence/iteration32_64_manifest.json`绑定两版身份和完整顺序；来源为`support_120_identity.json`对应冻结候选。每版51份YAML／102组配置、20实际场景入口。共用repair_core是依赖层，不作为第21个入口。第一份未运行草稿因误计该依赖而被静态断言拒绝，已另建新候选，原始来源未改变。

32版全部输入字节与来源相同；64版只有YAML上限改变，USD、task data和两个metric文件字节相同。没有新增ValidationObserver。独立worktree复用逐字节一致的资产/数据，避免重复大文件；任何需要修改的文件独立复制，保留来源哈希。辅助代码在个人tools目录，不进入Scenario Forge核心或接收方运行依赖。

六项规则测试通过：只改上限、不修改输入、拒绝来源范围错误/缺配置、固定运行顺序、需要三次完整审核才能选择、重复同一attempt不能冒充重复冷启动。候选选择要求三次score1／success_rate1、动作/时钟/视频审计通过且真实目视通过；两版都满足优先32。原生结果不能自动触发交付。

## 新主机和执行

旧10.150.164.67和公网885连接超时；用户最终指定新机10.150.165.46:22，公网123.57.187.96:919。添加公钥后已连通。hostname为`dsw-529861-6cb4cb97bf-l8495`，GPU为`GPU-420b26cd-ec84-8748-1f98-62a728c069c4`，4090、驱动570.153.02；Isaac4.1.0-rc.7+4.1.14801.71533b68.gl。客户端genmanip-client0.2.0指向个人shared checkout，requests2.32.5／lmdb1.6.2／numpy1.26.4；ffmpeg/ffprobe存在，启动前GPU空闲、8087无服务、本地盘约229GB余量。

硬件身份变化，先新建旧包校准副本，绑定上次已成功旧包的输入哈希和原meta_record，使用原replay_transport_probe和chunk30语义。旧基线需原生1分、共同机器人观察误差≤1e-5、动作一致、视频完整并实际目视通过，才放行六轮。

监督进程启动PID32615。权威队列在远端`/tmp/task12_iteration32_64_20261018/queue.json`；共享镜像`evidence/iteration32_64_queue.json`。进程与时间戳联合判断，文档PID不是运行证明。监督器持有已有资源锁，每次启动检查GPU/端口空闲，单次45分钟上限；只清理本次owned进程。任务失败继续对照，基础设施/时钟/引擎错误停止。

所有日志、原生输出、receipt、阶段图片和高频运行状态先存本地盘；共享checkpoint写失败保留本地权威状态并明确记录。每轮结束自动解码视频、抽取抓持/显色/回架及终态图片，再归档输入/结果/日志并核验tar和SHA。图片准备不等于目视通过。无诊断运行没有逐粒保留率，不借用其他版本的95%证据。

## 后续门槛

三次完整回放均合格才进入两次私有保液诊断与代表来源/独立安装验证。若两版均不满足，不自动扫其他上限；根据真实成功/失败结果选择定向诊断，全部失败时各选首次失败。私有测量和无诊断版本若出现行为差异，先解决证据可信度，不能通过把观察器塞入交付USD绕过。最终仍须满足原定19条来源重复验收；水浴LeRobot延期。

规范依据MAT-003、VAL-001/002/003/004/005/008及维护流程。规范无需变更：这是未获资格的单任务参数比较，不推广默认值，不改包/schema/API契约。任务记录和操作说明同步；仿真与最终目视尚未完成。
