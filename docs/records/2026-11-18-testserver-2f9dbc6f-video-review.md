# `testserver/2f9dbc6f7c83459c85b7413f64d78f83` 评测视频物理与 USD 审核记录

日期：2026-11-18。范围仅限 `sim-oss:pjlab-bjpai-sim/wangyukai/testserver/2f9dbc6f7c83459c85b7413f64d78f83/` 下既有评测录像与状态记录的视觉及元数据审核；普通操作失败、未抓稳、正常倾倒/泼洒、动作停滞及策略得分均不作为物理或 USD 缺陷。

## 自包含交付入口

产物与临时下载媒体统一存放在外部工作目录 `/mnt/data/zhuzihou/reviews/testserver_2f9dbc6f_20261118/`，未加入 `scenario-forge` 核心代码或 Git 仓库：

- 自包含 HTML：`/mnt/data/zhuzihou/reviews/testserver_2f9dbc6f_20261118/download/review_selfcontained.html`
- 大小：**59,115,707 bytes**（约 56.4 MB）
- SHA-256：`6ae5e05e5f6d94a915a66683aa96b92e1abf6b64118c2370bca6e5e35d0b2971`
- 内嵌内容：4 段问题相关原视频（VP8 WebM 封装、点击播放时按需解码为 Blob）、4 张四视角密集帧拼图（含 1 张复核排除案例），以及全部 340 例原始 `result_info.json` 评分与元数据。

## 覆盖与审核方法

- **分级拉取**：首轮拉取全部 340 个 episode（20 个 `scientific_experiments` 任务）的 `overlook_camera.mp4`、`result_info.json`、`meta_record.pkl` 及顶层 `result.json` / `progress.json`（共 1,022 个文件、2.317 GiB）；对筛选出的 4 条候选异常按需补拉 `top_camera.mp4`、`left_camera.mp4`、`right_camera.mp4`（共 12 个文件、131.63 MiB）。
- **主视角规模**：340 条 `overlook_camera.mp4` 合计 **12.86 小时**、**1,389,210 帧**。
- **状态扫描**：解析全部 340 份 `meta_record.pkl` 与 `result_info.json`，检出 1 例 `non_finite_state`（`task_z2_key_steps_in_mof/mixed_11`）。
- **全量目视覆盖**：全部 340 条主视角视频按 1 fps + 末帧抽取并保持原始比例拼接为 **4,021 页**时间线图，由 6 个并行视觉审核代理逐页实际查看并经 `COVERAGE_VALIDATION.json` 门禁校验（`expected_pages: 4021`、`viewed_pages: 4021`、`missing_count: 0`、`duplicate_count: 0`）。

## 审核结论（确认 3 例，复核排除 1 例）

### 确认物理 / 状态异常（3 例）

1. **`ISS-001` · `task_01_pour_flask_to_cylinder/unseen_instruction_10`**（`t=47s–72s`，物体异常飞射与穿模）：量筒在桌面受碰后高速飞射撞脱上方玻璃盒/架，玻璃盒滑过桌面撞倒烧瓶后，于 `t=65–71s` 穿模穿过左臂夹爪与桌面并完全消失。
2. **`ISS-002` · `task_07_insert_centrifuge_tubes/unseen_prospect_10`**（`t=43.0s–44.5s`，接触冲量导致物体弹飞）：左夹爪在蓝色离心管架上方夹取红盖离心管时，管体在 `t=43.6–44.0s` 受异常接触冲量向斜上方高速弹飞越过离心机并飞出画面（`left_camera` 与 `overlook_camera` 均清晰可见）。
3. **`ISS-003` · `task_z2_key_steps_in_mof/mixed_11`**（`step 1589` / `t≈52.97s–53.97s`，机器人仿真状态发散）：抓取白色洗瓶后，`meta_record.pkl` 记录 `joint_positions` 与 `base_positions` 从 step 1589 起连续 29 步出现 `NaN/Inf`，episode 于 step 1587 异常终止并追加 30 帧尾帧；四路相机画面在 `t=52.93s–53.00s` 突变为纯白/灰黑虚空。

### 多视角复核排除（1 例）

- `task_z6_evaporative_crystallization_prep/mixed_11`（`t=124s–133.37s`）：主视角初期疑为“容器消失与黄色液体悬空爆炸”，经 `left_camera` 与 `top_camera` 密集帧复核，透明深色玻璃烧杯仍在左夹爪内未消失，黄色液体为倾倒泼洒在黑色桌面上，不计为物理/USD 缺陷。

## 验证与规范边界

- **隔离离线 Chromium 验收**：仅复制 `review_selfcontained.html` 至临时空目录并禁用外部网络请求，在 `1440×1000`、`768×1024`、`390×844` 三种视口下通过：零横向溢出、零外部请求、零 JS 报错，4/4 内嵌图片解码成功，4/4 内嵌 WebM 视频可按需转 Blob 播放并跳转至异常时刻，340 条表格与筛选/重置/JSON 弹窗交互正常。验收截图与报告保存于 `evidence/browser_audit/browser_audit.json`。
- **局限性与规范**：本次基于 1 fps + 末帧时间线目视与状态扫描，不保证零漏检，且确认异常现象不等于已定位 USD 或求解器代码根因。遵循 `VAL-001`–`VAL-007` 与仓库目录边界，未修改核心包、场景资产或标准文档，无需运行核心 `make check`。
