#!/usr/bin/env python3
"""Make the rich-tabletop r9 Task 02/07/08 release the task-page default."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import shutil
from typing import Mapping


R9_COPY = {
    2: (
        "Task 02 r9 丰富桌面液体候选包 · 960 步稳定性检查通过；EOS 脚本机器人"
        "冷启动倒液 3/3 通过；学习策略、液体 metric 与 benchmark 未验证"
    ),
    7: (
        "Task 07 r9 丰富桌面候选包 · 5 个固定房间变体均通过 960 步稳定性与"
        "多视角检查；机器人搅拌与 benchmark 未验证"
    ),
    8: (
        "Task 08 r9 丰富桌面候选包 · 试管架含 3 支管体，独立红色任务管盖保持可见；"
        "960 步稳定性通过；机器人旋紧与 benchmark 未验证"
    ),
}


def publish(index: Path, images: Mapping[int, Path]) -> Path:
    index = index.resolve()
    html = index.read_text(encoding="utf-8")
    assets = index.parent / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    asset_names: dict[int, str] = {}
    for task_number, image in images.items():
        name = f"task{task_number:02d}-r9-rich-tabletop-overview.png"
        shutil.copy2(Path(image).resolve(), assets / name)
        asset_names[task_number] = name

    r9_button = (
        '<button class="version" data-version="r9" aria-pressed="true">r9 · 丰富桌面</button>'
    )
    if 'data-version="r9"' not in html:
        html = re.sub(
            r'(<button class="version" data-version="r8" aria-pressed=")true(")',
            r"\1false\2",
            html,
            count=1,
        )
        marker = '<button class="version" data-version="r8"'
        html = html.replace(marker, r9_button + marker, 1)
    else:
        html = re.sub(
            r'<button class="version" data-version="r9" aria-pressed="true">.*?</button>',
            r9_button,
            html,
            count=1,
        )

    def add_r9(match: re.Match[str]) -> str:
        card = match.group(0)
        task_match = re.search(r"<span>Task (\d{2})</span>", card)
        if task_match is None:
            raise ValueError("task card number was not found")
        task_number = int(task_match.group(1))
        source_version = "r8" if 'data-release-version="r8"' in card else "r7"
        source_rail = re.search(
            rf'<a class="evidence-rail" data-release-version="{source_version}".*?</a>',
            card,
            flags=re.DOTALL,
        )
        source_release = re.search(
            rf'<span data-release-version="{source_version}">.*?</span>',
            card,
            flags=re.DOTALL,
        )
        if source_rail is None or source_release is None:
            raise ValueError(f"Task {task_number:02d} has no release source for r9")

        existing_rail = re.search(
            r'<a class="evidence-rail" data-release-version="r9".*?</a>',
            card,
            flags=re.DOTALL,
        )
        existing_release = re.search(
            r'<span data-release-version="r9">.*?</span>', card, flags=re.DOTALL
        )
        if task_number in R9_COPY:
            asset = asset_names[task_number]
            rail = (
                '<a class="evidence-rail" data-release-version="r9" '
                f'href="assets/{asset}"><img src="assets/{asset}" '
                f'alt="Task {task_number:02d} r9 丰富桌面场景总览" loading="eager"></a>'
            )
            release = f'<span data-release-version="r9">{R9_COPY[task_number]}</span>'
        else:
            rail = source_rail.group(0).replace(
                f'data-release-version="{source_version}"',
                'data-release-version="r9"',
                1,
            )
            source_text = re.sub(r"^<span[^>]*>|</span>$", "", source_release.group(0))
            release = (
                '<span data-release-version="r9">该任务无 r9，展示最新有效版本 · '
                f"{source_text}</span>"
            )
        if existing_rail is None:
            card = card.replace(source_rail.group(0), rail + source_rail.group(0), 1)
        else:
            card = card.replace(existing_rail.group(0), rail, 1)
        if existing_release is None:
            card = card.replace(source_release.group(0), release + source_release.group(0), 1)
        else:
            card = card.replace(existing_release.group(0), release, 1)
        return card

    html = re.sub(
        r'<article class="task-card"[^>]*>.*?</article>',
        add_r9,
        html,
        flags=re.DOTALL,
    )
    html = re.sub(r"applyVersion\('(r8|r7)'\)", "applyVersion('r9')", html)
    html = html.replace(
        "r8 目前只更新任务 2；其他任务明确回退到自己的 r7 最新有效版本。",
        "r9 更新任务 2、7、8；其他任务展示自己的最新有效版本。",
    )
    index.write_text(html, encoding="utf-8")
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--task02-image", required=True, type=Path)
    parser.add_argument("--task07-image", required=True, type=Path)
    parser.add_argument("--task08-image", required=True, type=Path)
    args = parser.parse_args()
    print(
        publish(
            args.index,
            {2: args.task02_image, 7: args.task07_image, 8: args.task08_image},
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
