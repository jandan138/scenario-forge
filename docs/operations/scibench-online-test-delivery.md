# SciBench 在线 test 修复交付

目标：`sim-oss:pjlab-bjpai-sim/wangyukai/testserver/scibench/`。修复 r2 已完成本地限定范围验收、上传及下载回读核验。当前完成标记为 `TRANSFER_VERIFIED_SMOKE20_PASSED_WITH_RUNTIME_LIMITS`，见同目录 `DELIVERY_COMPLETE.json`。

代码：`feature/pioneer` @ `7939a4c88b5348b45b827e1d684fc560b134fce2`；客户端子模块 `61202ccc1419d1e1427ea750bfdeb44309862386`。实际验收主机10.150.168.71，Isaac4.1.0。

## 同步内容

将远端 `saved/` 的内容按相对路径合并到接收方 saved 根（例如 `/nas/EBench/`），不要再套一层saved。保留其他EBench文件；公共同路径文件若哈希不同先比对。

- 原三个目录：`assets/robot_usds/lift2_scientific_experiments`、`assets/scene_usds/scientific_experiments`、`tasks/scientific_experiments`。
- 新增必需目录子集：`assets/_dependencies`、`assets/materials/static_bath`、`assets/miscs/mdl/ebench/mdl`、`assets/miscs/curobo/R5a`。
- `_dependencies`来自2026-10-30水浴/银镜交付的实际USD引用链，不是可忽略缓存。保持目录层级与文件内容，不自行删掉subLayer或改物理参数。

新必需清单8734个文件；相对首版增加834文件、178226224字节，重叠文件哈希未改。当前远端逐文件列举恰好8734个数据文件，缺失0、额外0；scene_usds/scientific_experiments为7559、tasks为680、专用robot_usds为2。首版清单中的427个附加材质路径在当前远端未列出，已有接收目录可能仍保留这些文件（合并后场景文件数会为7986）；见RETAINED_LEGACY_FILES.json。本次未执行远端delete或sync，计数以实际manifest及远端列举为准。

数据仅含正式test初始化及资产，没有LMDB或validation episode。原始test配置和metric由对应Git提交提供，不上传诊断配置。

## 验收范围

- 全部680配置、680 metadata、340 `.usda` 入口静态检查通过。
- 全新仓库仅使用交付saved副本；20类任务各1例reset、10步保持动作、数值评分返回通过。诊断配置唯一变化为num_steps=10；原始test配置不改。
- 原失败task_z1 mixed_1/2/3另做原配置10步回归通过。用户要求停止全量运行，不能宣称680例全部原生通过。
- 20组起止相机画面由实现者复核；暗玻璃、遮挡等限制保留，不属于独立评审。
- 日志仍有接触偏移、非根关节状态恢复、ScriptNode释放与Camera删除等引擎错误；未阻断本次短测，不代表零错误、完整策略成功或长时稳定。详见VALIDATION_REPORT.json。

运行前后8734文件SHA256一致。传输采用rclone copy（transfers32/checkers64），下载回读check采用checkers64和one-way以保留目标端旧附加文件。完成标记最后发布。

证据目录：`/cpfs/user/zhuzihou/dev/scibench-test-repair-20261105/`。首版问题与修复过程见2026-11-05-scibench-online-test-repair.md；源建通仓库和saved未改。
