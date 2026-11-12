# Task10 粒子与显色：离线 HTML 教程

面向首次接触本任务的读者，解释四组粒子、受控出液、真实接收判定、名义剂量、独立材质和连续显色。
包含液滴归属练习、剂量与成功锁定检查器、三张已验证场景图、伪代码、排查顺序和小测验。

生成：

```bash
python scripts/build_task10_color_tutorial.py
```

交付单文件：`outputs/task10_color_tutorial_20261010/task10-liquid-color-tutorial.html`。
直接用浏览器打开，无 CDN、外部字体、网络请求或相邻资源文件依赖。

本目录保留小型 HTML 模板；包含内嵌截图的完整 HTML、浏览器截图、打印检查 PDF 与 audit.json 留在 outputs。
截图来源为已交付 task10 VR 包的 `preview_replay/frame_00000.png`、`frame_00003.png`、`frame_00005.png`。

页面交互是教学模型，不执行 PBD 或化学模拟。显色函数按当前 Python 策略的运算顺序移植，
并由真实浏览器对照 10 个 Python 参考点（含阈值两侧）检查。
保持时间、成功锁定与过量历史使用简化的规则演示；滑块设值不是实际出液或物理倒流。
场景图是合格粒子状态回放，初始/终点与重置后的过量试验已在图注区分。
