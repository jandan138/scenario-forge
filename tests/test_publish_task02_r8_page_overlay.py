from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts/publish_task02_r8_page_overlay.py"
)


def _module() -> object:
    spec = importlib.util.spec_from_file_location("task02_r8_page", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_overlay_makes_r8_default_and_keeps_r7_switch(tmp_path: Path) -> None:
    html = '''<button class="version" data-version="r7" aria-pressed="true">r7</button>
<article class="task-card"><a class="evidence-rail" data-release-version="r7" href="task01.png"><img src="task01.png" alt="Task 01 r7"></a><div><span>Task 01</span><span data-release-version="r7">task 01 r7</span></div></article>
<article class="task-card"><a class="evidence-rail" data-release-version="r7" href="old.png"><img src="old.png" alt="Task 02 r7"></a><div><span>Task 02</span><span data-release-version="r7">old release</span></div></article>
<script>applyVersion('r7');</script>'''
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
    assert "Task 02 r8 液体诊断原型" in result
    assert "该任务无 r8，展示 r7 最新有效版本 · task 01 r7" in result
    assert result.count('data-release-version="r8"') == 4
    assert (tmp_path / "assets/task02-r8-static-overview.png").is_file()
