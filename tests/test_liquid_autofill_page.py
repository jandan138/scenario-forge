from __future__ import annotations

from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
PAGE_ROOT = REPO_ROOT / "docs/liquid-autofill"


def test_liquid_autofill_page_teaches_the_pinned_fail_closed_workflow() -> None:
    html = (PAGE_ROOT / "index.html").read_text(encoding="utf-8")

    for fact in (
        "给任意合格容器",
        "Task 02 r10.3",
        "scenario-forge liquid inspect",
        "scenario-forge liquid add",
        "live points q95",
        "0.00582 m / 0.00594 m",
        "三次冷启动",
        "_diagnostics/",
        "没有证明",
    ):
        assert fact in html
    for section_id in ("pipeline", "recipe", "run", "failure"):
        assert f'id="{section_id}"' in html
    assert "prefers-reduced-motion" in html
    assert "repeat(2,minmax(0,1fr))" in html
    assert ".passbox code,.warning code{overflow-wrap:anywhere}" in html
    assert "/cpfs/" not in html
    assert "file:" not in html
    assert "http://" not in html
    assert "https://" not in html

    references = re.findall(r'(?:src|href)="([^"]+)"', html)
    for reference in references:
        if reference.startswith(("#", "data:")):
            continue
        assert (PAGE_ROOT / reference).resolve().exists(), reference


def test_docs_and_cylinder_tutorial_cross_link_the_autofill_page() -> None:
    docs_index = (REPO_ROOT / "docs/index.md").read_text(encoding="utf-8")
    cylinder = (REPO_ROOT / "docs/liquid-cylinder-tutorial/index.html").read_text(
        encoding="utf-8"
    )

    assert "[给任意合格容器加入初始液体](liquid-autofill/)" in docs_index
    assert 'href="../liquid-autofill/index.html"' in cylinder
