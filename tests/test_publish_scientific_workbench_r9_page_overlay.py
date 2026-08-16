from __future__ import annotations

from pathlib import Path

from scripts.publish_scientific_workbench_r9_page_overlay import publish


def test_r9_overlay_updates_three_tasks_and_preserves_fallbacks(tmp_path: Path) -> None:
    cards = []
    for number in (1, 2, 7, 8):
        cards.append(
            '<article class="task-card"><a class="evidence-rail" '
            f'data-release-version="r8" href="task{number}.png"><img '
            f'src="task{number}.png"></a><div><span>Task {number:02d}</span>'
            f'<span data-release-version="r8">Task {number:02d} r8</span>'
            "</div></article>"
        )
    index = tmp_path / "index.html"
    index.write_text(
        '<button class="version" data-version="r8" aria-pressed="true">r8</button>'
        + "".join(cards)
        + "<script>applyVersion('r8');</script>",
        encoding="utf-8",
    )
    images = {}
    for number in (2, 7, 8):
        image = tmp_path / f"source-{number}.png"
        image.write_bytes(b"png")
        images[number] = image

    publish(index, images)

    result = index.read_text(encoding="utf-8")
    assert 'data-version="r9" aria-pressed="true"' in result
    assert 'data-version="r8" aria-pressed="false"' in result
    assert "applyVersion('r9')" in result
    assert "Task 02 r9 丰富桌面液体候选包" in result
    assert "Task 07 r9 丰富桌面候选包" in result
    assert "Task 08 r9 丰富桌面候选包" in result
    assert "该任务无 r9，展示最新有效版本 · Task 01 r8" in result
    assert result.count('data-release-version="r9"') == 8
    for number in (2, 7, 8):
        assert (tmp_path / f"assets/task{number:02d}-r9-rich-tabletop-overview.png").is_file()
