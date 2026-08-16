from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/publish_task02_r8_page_overlay.py"


def _module() -> object:
    spec = importlib.util.spec_from_file_location("task02_r8_page", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_overlay_makes_r8_default_and_keeps_r7_switch(tmp_path: Path) -> None:
    html = """<button class="version" data-version="r7" aria-pressed="true">r7</button>
<article class="task-card"><a class="evidence-rail" data-release-version="r7" href="task01.png"><img src="task01.png" alt="Task 01 r7"></a><div><span>Task 01</span><span data-release-version="r7">task 01 r7</span></div></article>
<article class="task-card"><a class="evidence-rail" data-release-version="r7" href="old.png"><img src="old.png" alt="Task 02 r7"></a><div><span>Task 02</span><span data-release-version="r7">old release</span></div></article>
<script>applyVersion('r7');</script>"""
    source = tmp_path / "index.html"
    source.write_text(html, encoding="utf-8")
    image = tmp_path / "r8.png"
    image.write_bytes(b"png")

    _module().publish(source, image)

    result = source.read_text(encoding="utf-8")
    assert 'data-version="r8" aria-pressed="true"' in result
    assert 'data-version="r7" aria-pressed="false"' in result
    assert "applyVersion('r8')" in result
    assert 'data-release-version="r8"' in result
    assert "Task 02 r8.7 动态装液起始候选包" in result
    assert "580 粒子三次动态冷启动均保持在量筒内" in result
    assert "eBench 加载、复位与 8 秒零动作运行通过" in result
    assert "EOS 脚本机器人倒液 3/3 通过" in result
    assert "学习策略、液体 metric 与 benchmark 未验证" in result
    assert "该任务无 r8，展示 r7 最新有效版本 · task 01 r7" in result
    assert result.count('data-release-version="r8"') == 4
    assert (tmp_path / "assets/task02-r87-scene-overview.png").is_file()
    assert 'href="../liquid-cylinder-tutorial/"' in result
    assert "量筒液体修复教程" in result


def test_overlay_upgrades_existing_r83_card_and_keeps_it_in_history(tmp_path: Path) -> None:
    html = """<button class="version" data-version="r8" aria-pressed="true">r8.3 · GPU-PBD 倒液候选包</button>
<button class="version" data-version="r7" aria-pressed="false">r7</button>
<article class="task-card"><a class="evidence-rail" data-release-version="r8" href="assets/task02-r83-scene-overview.png"><img src="assets/task02-r83-scene-overview.png" alt="Task 02 r8.3"></a><a class="evidence-rail" data-release-version="r7" href="old.png"><img src="old.png" alt="Task 02 r7"></a><div><span>Task 02</span><span data-release-version="r8">Task 02 r8.3 GPU-PBD 倒液候选包</span><span data-release-version="r7">old release</span><details><summary>5 packages</summary><ul><li><a href="assets/task02-r83-scene-overview.png">scientific_workbench_task02_r83_20260815 — room</a></li><li>old</li></ul></details></div></article>
<script>applyVersion('r8');</script>"""
    source = tmp_path / "index.html"
    source.write_text(html, encoding="utf-8")
    image = tmp_path / "r87.png"
    image.write_bytes(b"png")

    _module().publish(source, image)

    result = source.read_text(encoding="utf-8")
    assert "r8.7 · 动态装液起始候选包" in result
    assert "task02-r87-scene-overview.png" in result
    assert "6 packages" in result
    assert "scientific_workbench_task02_r87_20260816" in result
    assert "scientific_workbench_task02_r83_20260815" in result
    assert result.count('data-release-version="r8"') == 2
    assert result.count('href="../liquid-cylinder-tutorial/"') == 1

    _module().publish(source, image)

    repeated = source.read_text(encoding="utf-8")
    assert repeated.count("scientific_workbench_task02_r87_20260816") == 1
    assert "6 packages" in repeated
    assert repeated.count('href="../liquid-cylinder-tutorial/"') == 1
