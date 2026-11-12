# OpenWAM 2026-10-22 离线录像审核

本轮只审核 `openwam_all20_100000_new_20261022`，不包含 Pi05。用户授权并行审核，由主助手复核、合并；没有重新运行仿真，也没有修改接收仓库的 USD、配置、metric、task data 或 LeRobot 数据，没有写入飞书。

## 交付入口

大型产物在个人 GenManip 目录，未加入 Scenario Forge 核心代码或 Git 大文件：

```text
/mnt/data/zhuzihou/GenManip-Sim/saved/reviews/scientific_experiments/openwam_all20_100000_new_20261022/
  openwam_all20_100000_new_20261022_overlook_all680.7z
  download/review.html
  download/ISSUE_LIST.txt
  download/issues.csv
  download/README_REVIEW.txt
  FINAL_SOURCE_CHECK.json
  FINAL_COVERAGE_CHECK.json
  PRIMARY_REVIEW.json
  REVIEW_COMPLETE.json
  browser/audit.json
```

原始视频包为 4,311,268,047 字节，包含 680 条未经重编码的 overlook 视频、680 个原始 `result_info.json`、来源索引和校验清单。视频名包含运行批次、任务、场景和 seed。

压缩包 SHA256：`d31731c64b7fcd9bdb33516e532c7c8fd93db7df489271a2d69bfb1888b70af7`。

HTML 单独交付，与解压后的 `videos/`、`results/` 放在同一级。截图和审核数据内嵌，播放原视频依赖旁边的视频目录；不依赖服务器或网络。最终报告及配套文件哈希见产物目录的 `DELIVERY_SHA256SUMS`。

## 覆盖与结论

- 20 个任务、680 个 episode、约 24.74 小时 overlook 录像。
- 全部 2,672,241 帧完成全局和局部运动自动扫描；扫描信号不是语义认证。
- 3,138 张时间线图全部实际目视，时间线以每视频秒一帧构成；疑点另查连续帧及其他机位。每例实际范围在 `coverage.csv` 和 `reviewer/*_review.json`。
- 8 个确认案例归为 3 类：滴定机器人状态突变并异常终止 2 例、MOF 锥形瓶穿入桌面 1 例、蓝瓶分离液体同步变色 5 例。
- 14 个疑似案例归为 4 类：水浴/银镜松手后试管上移出杯 11 例、漏斗反弹 1 例、定量称量颗粒喷散 1 例、托盘边缘放置仍满分的评分语义疑点 1 例。

确认指原画面或原记录支持异常现象，不代表已经定位物理或源码根因。未确认独立的 metric 误分；所有 680 例最终分项到总分的算术重算一致，这不构成评分语义全部正确的证明。

滴定两例可绑定原始 `arm_state_jump_too_large` 日志；异常检测触发终止并追加尾部录像，不能倒置为“正常终止后才因尾录制出错”。原始日志索引在 `sources/invalid_robot_termination_evidence.json`。

称量 15 条满分案例有原生有效读数 4.01–4.18 g 日志，见 `sources/task09_recorded_readout_pass.json`；末帧显示屏重影不能单独证明误分。已记录的 `stable=false` 不违反此前取消连续稳定要求的任务口径。

## 验证与限制

`7z t` 通过。全部 680 源视频、680 源 JSON 和各自下载副本重新计算 SHA256，与打包基线一致。源视频大小和修改时间一致；源 JSON 没有打包前的修改时间基线，只能证明字节匹配及本次读取前后稳定。

HTML 在 Chromium 中检查桌面、平板和手机视口，无页面横向溢出或已加载证据图损坏；验证任务筛选、图片弹窗、原视频播放及问题时间点跳转。浏览器审计保留媒体跳转导致的取消请求，只有后续媒体成功读取时才将其与加载错误区别处理。

本轮不能保证零漏检，也没有对全部帧进行人工式语义审核。透明材质、微小液体/颗粒、遮挡和未执行的操作会限制判断。最终评分 JSON 不提供每一步给分时间；视频秒数不直接等于仿真秒数。当前安装的 goal/源码只作为审计参考，不能自动当作历史评测版本的绑定证据。

## 规范处理

遵循 VAL-001/002/003/004/005/007 的证据层级、验证范围、内容绑定、限制披露及大型产物边界；本轮未执行回放，不新增 VAL-008 的协议验证结论。审阅时仓库 HEAD 为 `4f1b6a69c711773119fd5870c47e8093a1d105b7`，工作树已有其他变更，不把该 HEAD 等同于所有审阅文件的内容版本。

规范无需变更：这里只对既有录像出具带范围限制的审核记录，没有形成新的通用物理参数、资产制作方式或包/schema/API 契约。本记录与外部交付说明同步保存；历史交付记录及其他工作树内容保持原样。本次不新增 episode runner 或 benchmark reporting 层，不运行与这些离线产物无关的核心包测试。

## 同日追加：真正自包含 HTML

用户选择将 22 条问题案例的完整主视角视频内嵌到单个 HTML。新增 `download/openwam_review_selfcontained.html`，295,406,721 字节；旧报告与原始 7z 保留。

新文件包含 22 条未经重编码的视频、157 张证据图、全部 680 条原始评分 JSON 和审核记录。其余 658 条不显示播放按钮，明确标注完整视频在原 7z。视频按需解码为 Blob，关闭播放器时释放；评分在页面内查看，无外部 JSON 文件依赖。

将 HTML 单独复制到临时空目录，在 Chromium 网络禁用模式下验证：22/22 视频能加载、定位问题起点、实际播放并跳到末尾；157/157 图像解码成功；680 条评分完整；任务筛选、类型汇总导航和评分/图片弹窗通过。桌面、平板、手机视口无页面横向溢出。快速关闭再打开视频的异步关闭事件冲突已修正并通过全量复测。浏览器证据在 `browser_selfcontained/audit.json`，内容校验在 `SELFCONTAINED_CONTENT_CHECK.json`，清单在 `SELFCONTAINED_MANIFEST.json`。

SHA256：`1ab9d53495b440ffe9b9830830c722139bd6ee33f628b635ad4ba02114525d7b`。本次只改变报告封装和浏览交互，不改变审核结论或证据适用范围，规范无需变更。
