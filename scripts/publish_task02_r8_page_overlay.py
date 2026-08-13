#!/usr/bin/env python3
"""Overlay the blocked Task 02 r8 diagnostic on the generated r7 directory."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import shutil


def publish(index: Path, image: Path) -> Path:
    index = index.resolve()
    image = image.resolve()
    html = index.read_text(encoding="utf-8")
    asset = index.parent / "assets/task02-r8-static-overview.png"
    asset.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(image, asset)

    r8_button = (
        '<button class="version" data-version="r8" aria-pressed="true">'
        'r8 · 液体诊断原型（blocked）</button>'
    )
    if 'data-version="r8"' not in html:
        html = html.replace(
            '<button class="version" data-version="r7" aria-pressed="true">',
            r8_button
            + '<button class="version" data-version="r7" aria-pressed="false">',
            1,
        )
    html = html.replace(
        "r7 目前只更新任务 2、7、8；其他任务明确回退到自己的最新有效版本。",
        "r8 目前只更新任务 2；其他任务明确回退到自己的 r7 最新有效版本。",
    )

    found_task02 = False

    def add_r8_view(match: re.Match[str]) -> str:
        nonlocal found_task02
        card = match.group(0)
        if 'data-release-version="r8"' in card:
            found_task02 = found_task02 or bool(
                re.search(r'<span>Task 02</span>', card)
            )
            return card
        rail = re.search(
            r'<a class="evidence-rail" data-release-version="r7".*?</a>',
            card,
            flags=re.DOTALL,
        )
        release = re.search(
            r'<span data-release-version="r7">.*?</span>', card, flags=re.DOTALL
        )
        if rail is None or release is None:
            raise ValueError("task card r7 release elements were not found")
        if re.search(r'<span>Task 02</span>', card):
            found_task02 = True
            r8_rail = (
                '<a class="evidence-rail" data-release-version="r8" '
                'href="assets/task02-r8-static-overview.png">'
                '<img src="assets/task02-r8-static-overview.png" '
                'alt="Task 02 r8 静态构图；液体物理 blocked" '
                'loading="eager"></a>'
            )
            r8_release = (
                '<span data-release-version="r8">Task 02 r8 液体诊断原型 · '
                '视觉 mesh convexDecomposition GPU 粒子碰撞 blocked</span>'
            )
        else:
            r8_rail = rail.group(0).replace(
                'data-release-version="r7"', 'data-release-version="r8"', 1
            )
            r7_text = re.sub(r"^<span[^>]*>|</span>$", "", release.group(0))
            r8_release = (
                '<span data-release-version="r8">该任务无 r8，展示 r7 最新有效版本 · '
                f"{r7_text}</span>"
            )
        card = card.replace(rail.group(0), r8_rail + rail.group(0), 1)
        return card.replace(release.group(0), r8_release + release.group(0), 1)

    html = re.sub(
        r'<article class="task-card"[^>]*>.*?</article>',
        add_r8_view,
        html,
        flags=re.DOTALL,
    )
    if not found_task02:
        raise ValueError("Task 02 card was not found")
    html = html.replace("applyVersion('r7')", "applyVersion('r8')")
    index.write_text(html, encoding="utf-8")
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    args = parser.parse_args()
    print(publish(args.index, args.image))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
