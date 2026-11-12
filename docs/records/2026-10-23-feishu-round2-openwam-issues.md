# 飞书第二轮 OpenWAM 问题登记

用户明确表示已人工复核原审核报告中的14个疑似案例，全部确认为问题，并授权将22个案例写入飞书4.2第二轮。负责人按用户要求暂时留空。原机器初审报告及HTML保留，不将用户复核结论伪装成新的自动诊断或根因证明。

目标：[湿实验数采 Todo · 第二轮](https://aicarrier.feishu.cn/wiki/Og5Hw2fGGi8pIyk0SpBcrkGCnjf#DZFJd0yivo1n2ixmge3cmzoinSg)。文档ID `Ad41dB1IxobdSfxIk1ucUTgSnCd`，本次从revision7143更新到7152。

按第一轮格式，仅在8个任务的“修复内容”单元格写入问题现象、评测批次、case、seed、原视频时间与完整overlook路径：task04×1、task10×2、task11×1、task12×2、task13×5、task14×1、task16/code z2×1、task18/code z4×9。第二轮标题后追加一次人工确认说明。负责人和同步事项列保持空白；没有添加已修复删除线、分派任务、发送IM或上传大文件。

逐单元格更新并回读，使用当前revision和block ID，不替换整张表。前6行写入后，zero_shot单元格的文字拼接导致本地任务键解析失败，执行在第7行写入前停止；修正为提取task数字前缀，重新回读并跳过6个已完成单元格，再完成剩余两行及说明，未重复写入。

完整回读核对22个问题编号各出现一次、22个原视频路径齐全、20行结构保留、所有非目标单元格与初始快照一致、第一轮XML正文完全不变。

快照、逐行XML、dry-run、写入回执和最终核对结果：

```text
/mnt/data/zhuzihou/GenManip-Sim/saved/reviews/scientific_experiments/openwam_all20_100000_new_20261022/feishu_round2/
  round1_before.json / round1_after.json
  round2_before.json / round2_after.json
  planned_updates.json
  task_*.xml / task_*_receipt.json
  summary.xml / summary_receipt.json
  VERIFICATION.json
```

读取时继承代理发生EOF，后续仅为CLI子进程移除代理变量并直连成功，没有改系统代理或保存认证信息。用户链接中的一次性登录参数不进入请求、记录或交付链接。

本次为文档登记，不改变源码、USD、metric、数据集或既有审核结论。依VAL-003/004保留证据来源及人工确认边界；无新增通用制作或验证规则，规范无需变更。
