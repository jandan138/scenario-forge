# 水浴：保液配置接入独立接收方候选

候选身份：`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/task12_liquid_color_20261012/evidence/receiver_retention95_candidate_identity.json`。状态仅为静态准备完成，尚未做该接收方版本的机器人回放、正常机位视觉或独立安装验收；不是交付包。

以干净timing-v2接收方为来源，仅迁移已做静置/位姿压力测试的样液PBD参数与规则初态，并取消碰壁加热否决。原桌面、试管/烧杯刚体碰撞几何、质量、粒子数、YAML、时间阈值及动作LMDB保持。生产metric文件与来源完全相同，没有附加诊断代码。

20个场景逐组合属性审计通过：每个仅11项差异，限定为样液6个PBD参数、points/velocities及canonical对应初态、嵌入脚本的碰壁加热门禁。prim类型/schema/关系及其它属性保持。初态按实际容器与粒子prim变换映射，不把世界坐标点直接错误挪到局部空间。11项实际控制器/呈现/重置/回架判定契约测试通过，不作为物理运行资格。

## 任务初态审计的更正

此前只检查了`initial_prim_attributes`，其中未发现粒子初态键；这个结论不能推广到整份task data。进一步检查发现全部41份metadata另有`initial_particle_states.SampleParticles.points`，原版加载器`restore_initial_particle_states`会恢复这些点并清零速度。单改USD确实会被旧初态覆盖。

新审计证明，用原试管初始布局变换重建旧样液点位，与41份原数据相符，最大误差约2.98e-8m。候选据此更新了这41个样液点位数组。递归语义对照确认每份metadata只改变该字段，浴水、布局、任务规则及其它字段保持。未修改原版加载器或任何核心代码；旧记录原样保留。证据为`particle_initial_states_mapping_audit.json`、`receiver_retention95_static_audit.json`、`receiver_retention95_scene_semantics.json`，均在上述个人目录evidence下。

## 后续门槛

过程视频当前仍在运行。只有运动数值、喷射/持续失液视觉审查通过后才启动该候选的原动作回放。运行时还要验证初始化确实恢复新点位、重复reset一致、原动作不变、正常机位完整显色及回架。最终按既定19组各两次、原有坏例及干净接收方独立安装门槛完成，不以这次静态通过代替。

适用STATE-001/002/003/006、VAL-002/008。规范无需变更：现有重置与证据范围规则已覆盖此问题；此次补全GenManip具体初态恢复通道的操作检查，不新增核心包/API合同。运行/转换脚本继续留在个人诊断目录，不作为同事运行依赖。

## 首条干净接收方诊断已启动

显示同步压力视频完成，显示/live位置误差为0；每步保留率最低98.0223%。原v2报告留有2条未确定回落事件，保留原FAIL；同一v3几何规则复核384次已记录退出均与口部退出兼容。两路完整视频解码通过，主实现者按render-visual-reviewer清单查看131个时间采样裁切及原尺寸关键帧：提起/返回有管内晃动，持管时可辨认蓝色样液柱，抽查未见宏观口部喷流或持续排液。总览裁切、初帧跟随构图、管架遮挡及玻璃反射保留WARN；这是主实现者审查，不是独立第三方或逐帧证明，也不验证反应显色。

机器可读门槛 `evidence/retention95_motion_visual_gate.json` 仅放行首条原生诊断，绑定候选identity哈希；评审 `evidence/retention95_sync_motion_review.json`。`receiver_retention95_h13_a` 使用干净metric、原case13动作和校准协议，不含metric观察器。该次回放的保液、实际显色、回架、重复性及最终独立安装仍需后续证据，不能把压力测试结论扩大到机器人。
