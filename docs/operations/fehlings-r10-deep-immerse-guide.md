# 斐林水浴 r10：试管插到接近杯底再隔着假水看变色

从 r9 派生。目标运行时 Isaac Sim 4.5。规范依据 MAT-001～006。
假水 `water:profile_m` 与 `fill_height_ratio=0.8` 不变，贴壁薄壳与 OmniGlass 清水也不变。
试管、8 mL 五层和 30 秒策略不变。只把**加热回放**从液面下 6 mm 改成竖直插到接近杯底。

## 问题

r9 正视机位方向对，但颜色回放用的是浅插（先 55° 再竖直，管底只低于液面约 6 mm）。
8 mL 样液大半在水面以上。fill=0.8 时烧杯装不下整根 150 mm 管子；能做到的是把约 44 mm 样液全部没入。

## 加热姿态

规定夹具：烧杯局部 xy 居中、倾角 0°、管底约在假水底部以上 1.5 mm。
`tilted_contact` / `shallow_contact` 仍只测接触语义，不当变色镜头。

## 验收

必须看正视 `t3/t15/t21/t30_front_bath.png` 和试管**留在水里**的变色 MP4。
水面以下要能叫出蓝/绿/黄/橙红/砖红；样液顶须低于液面。出水图只作不回退。

视频（Git 外）：`outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r10_20260914/r10_front_bath.mp4`
