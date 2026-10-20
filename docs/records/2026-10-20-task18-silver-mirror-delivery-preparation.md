# Task18银镜交付准备

状态：候选制作及原版协议对照进行中，未安装、未发布。文档Task18对应task_z4_silver_mirror_reaction，20场景/20配置，9条坏例原记录均存在。

用户确认：复用Task12物理修复；银镜取消碰壁单独停表，其他加热守卫保留；保留银镜30–60秒、120Hz7000步，完整成功示范可待补，不通过缩短反应制造成功。本轮不更新LeRobot；只交付YAML/USD/task data/指定metric，核心SDK机器人资产不改。候选通过后才备份安装建通并同步飞书。

制作根`/cpfs/user/zhuzihou/dev/task18-silver-delivery-20261020`。candidate为建通HEAD9490df9a隔离clone，正式目录未改。20场景迁移前核对试管、烧杯、管架、加热器位置/朝向/尺寸一致；选择性迁移物理属性、PBD及碰撞子树、桌面碰撞几何和加热桥接，保留原银镜五层壁面材质、外观函数与原反应时序。Bath2320/Sample923颗粒，样液约4mL，采用水浴生产参数，尚无银镜运行资格。

20任务元信息按各自initial_layout重建粒子初态，原始timing_seconds逐条相等，启用架孔几何metric。20场景依赖闭包静态通过，7项纯规则测试通过。后补粒子系统/颗粒材质一致性测试发现SampleSystem仍绑定斐林样液材质而SampleParticles已透明，测试失败；待本次运行结束后修复，不将初版当交付候选。

初次Sdf.CopySpec因payload父prim未在root layer显式存在而失败，在隔离候选中创建override父spec后恢复；未改变接收源。重复运行遇到已有公共资产符号链接，检查后改为幂等创建。Usd.Flatten提示hide_in_stage_window编辑器元数据未知，已记录；不可据此忽略运行时物理错误。

远端10.150.164.127，dsw-536365-78bdb944c8-q99ff。监督PID3860558，GPU2新候选mixed17原生1步启动检查，GPU0原版Pi05 mixed17完整回放chunk30，GPU1原版OpenWAM mixed20完整回放单步接口。原Pi05日志最终executed22/6922步与chunk30一致，底座原目标为零；OpenWAM原日志为单步Episode done，7000帧底座幅度约5.9e-9。协议仍需结合观察状态与画面校准，不能先宣布完全复现。当前源只读、原记录保留。

权威状态为制作根evidence/initial_probes.json；每次run记录实际GPU、输入hash、配置和核心源码校验。原版异常用于校准，不自动放行新版；本轮候选还需受控动态/银镜视觉资格、9坏例与接收验证，未生成READY。

规范依据STATE-001..004、MAT-001..006、VAL-001..008及维护流程。任务特定迁移不建立通用物理参数准则，暂无通用规范变更；工具在仓库外，不改变Scenario Forge包/schema/API。

## 首轮画面发现与修正

v1 mixed17原生1步启动完成、无引擎错误，但目视发现浴液为黑色颗粒团，故不计视觉通过。另一个材质问题是SampleSystem仍绑定斐林样液材质，修正为与BathSystem透明材质一致，独立测试由失败转通过。v2候选mixed20完整回放启动后，在初版画面复核中定位更根本问题：通用USD的GetAppliedSchemas仅返回已注册schema，遗漏本机不认识的PhysxParticleSetAPI、Isosurface及RigidBody扩展。迁移器曾据此写回apiSchemas，导致这些标记丢失。

已保存各版hash，停止v2回放并保留输出，不算有效坏例验收。原版两条对照继续。SIGINT未使nohup继承环境中的helper退出，单独8190服务kill请求返回500，随后仅向本次receipt绑定的client/server进程组发SIGTERM；核对GPU3释放，未影响GPU0/1。

修复为读取原始apiSchemas listOp并保留未注册扩展，不依赖本机SDK识别结果；20场景迁移完成。新增原始PhysX标记回归测试先失败后通过，当前共9项规则/结构测试通过。v3重新做mixed17启动和视觉检查，监督PID3884243，GPU3；未通过视觉前不继续批量候选评测。该问题是制作迁移错误，不是银镜本身的物理结论。

9条坏例动作输入均有限且16维，来源、原分数、动作帧数与底座幅度存于nine_badcase_sources.json；尚未批量放行。No READY。
