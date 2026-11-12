# SciBench 在线 test OSS 交付

状态：TRANSFER_VERIFIED_RECEIVER_INTEGRATION_PENDING。
目标：sim-oss:pjlab-bjpai-sim/wangyukai/testserver/scibench/。
基线：GenManip-Sim feature/scientific_experiments @ 4baf01cddb588b6e396077b0d73f7bcfcdddd06c。
20任务，680正式test配置/初始化metadata，340场景入口。最终8327数据文件、14272686887字节，另附README、manifest、SHA256SUMS及完成标记。排除LMDB、validation episode、历史metadata备份。符号链接在独立副本中物化为同内容文件，未改源文件或USD内容。保留首轮筛选的427个附加test材质资源，均重新核对源哈希并纳入最终manifest。

上传rclone copy采用transfers=32/checkers=64；rclone check --download采用checkers=64，8330文件匹配、0差异；最终清单调整后单独下载校验manifest和SHA256SUMS通过。完成标记最后发布。没有运行模型评测或修改公共EBench资产，204条外部/搜索路径依赖记录留给接收方验证，不能声明完整独立闭包或在线联调通过。

证据目录：/cpfs/user/zhuzihou/dev/scibench-test-delivery-20261105/，包含build.py、payload、dry-run.log、upload-final.log、check-final.log、check-manifest.log。
操作说明：docs/operations/scibench-online-test-delivery.md。
适用ASSET-002、VAL-001/002/003/004/005/007。规范无需变更：此次仅制作既有test增量交付副本，不改变物理规则或核心schema/API。未修改核心代码，无需增加包行为测试；执行了清单、哈希及下载回读验证。
