#!/usr/bin/env python3
"""Compose Lab2Sim Figure 2 (scene plate) and Figure 3 (evidence → contract → USD).

Both figures are laid out at the final ICLR text width (5.5 in) with real point
sizes, so the type that appears in the paper is the type that is set here.
Raster sources come from ``source/`` and are staged by
``scripts/prepare_lab2sim_result_assets.py`` with source/asset hashes.
"""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "source"
OUT = ROOT

TEXT_WIDTH_IN = 5.5
PNG_DPI = 600
MIN_FONT_PT = 7.0
FONT_PT = {
    "header": 8.5,
    "title": 8.0,
    "body": 7.5,
    "label": 7.0,
    "meta": 7.5,
}

INK = "#172033"
MUTED = "#3F4855"
BLUE = "#2F6B99"
ORANGE = "#C96A0A"
TEAL = "#0E7C6B"
HAIRLINE = "#C5CFDA"
SURFACE = "#FFFFFF"

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Liberation Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": FONT_PT["body"],
    }
)


class ResultCase(NamedTuple):
    title: str
    action: str
    station: str
    detail: str
    revision: str
    status: str = "current_delivery"


class TraceCase(NamedTuple):
    title: str
    spec: str
    evidence: str
    usd: str
    contract: tuple[str, str, str, str]
    admission: str
    accent: str


def fig2_cases() -> tuple[ResultCase, ...]:
    return (
        ResultCase(
            "Stopper removal",
            "remove stopper",
            "fig2_stopper_station.png",
            "fig2_stopper_detail.png",
            "r11",
        ),
        ResultCase(
            "Glass-rod rack",
            "rack glass rod",
            "fig2_glassrod_station.png",
            "fig2_glassrod_detail.png",
            "r10.1",
        ),
        ResultCase(
            "Stir-bar insertion",
            "insert stir bar",
            "fig2_stirbar_station.png",
            "fig2_stirbar_detail.png",
            "r5",
        ),
        ResultCase(
            "Tube water bath",
            "heat tube in bath",
            "fig2_waterbath_station.png",
            "fig2_waterbath_detail.png",
            "r1",
        ),
    )


def fig3_cases() -> tuple[TraceCase, ...]:
    return (
        TraceCase(
            "IKA OVEN 125",
            "ika-oven-125",
            "fig3_oven_real.png",
            "fig3_oven_usd.png",
            (
                "envelope 700 × 825 × 650 mm",
                "door_hinge: revolute, 0–180°",
                "handle: door-child collider",
                "shelves: placement surfaces",
            ),
            "ConvertAsset · promoted · Isaac 4.1",
            ORANGE,
        ),
        TraceCase(
            "Burette stopcock",
            "titration-burette-and-stand",
            "fig3_burette_real.png",
            "fig3_burette_usd.png",
            (
                "tube 560 mm, Ø12 mm",
                "stopcock: revolute, 0–90°",
                "handle: grasp_region",
                "mount_frame: stand FixedJoint",
            ),
            "ConvertAsset · promoted · Isaac 4.5",
            BLUE,
        ),
    )


# --------------------------------------------------------------------------- helpers


class Canvas:
    """Place artists in inches on a figure of fixed physical size."""

    def __init__(self, width_in: float, height_in: float):
        self.width = width_in
        self.height = height_in
        self.fig = plt.figure(figsize=(width_in, height_in), facecolor=SURFACE)

    def frac(self, x: float, y: float, w: float, h: float):
        return (x / self.width, y / self.height, w / self.width, h / self.height)

    def image(self, x, y, w, h, path: Path, dpi: int = 400) -> None:
        image = Image.open(path).convert("RGB")
        pw, ph = max(2, round(w * dpi)), max(2, round(h * dpi))
        scale = max(pw / image.width, ph / image.height)
        resized = image.resize(
            (round(image.width * scale), round(image.height * scale)),
            Image.Resampling.LANCZOS,
        )
        left = max(0, (resized.width - pw) // 2)
        top = max(0, (resized.height - ph) // 2)
        axis = self.fig.add_axes(self.frac(x, y, w, h), zorder=3)
        axis.imshow(
            np.asarray(resized.crop((left, top, left + pw, top + ph))),
            interpolation="lanczos",
        )
        axis.set_axis_off()

    def box(self, x, y, w, h, *, edge=HAIRLINE, face=SURFACE, lw=0.6, radius=0.05, z=1):
        self.fig.add_artist(
            FancyBboxPatch(
                (x / self.width, y / self.height),
                w / self.width,
                h / self.height,
                boxstyle=f"round,pad=0,rounding_size={radius / self.width}",
                transform=self.fig.transFigure,
                facecolor=face,
                edgecolor=edge,
                linewidth=lw,
                zorder=z,
                mutation_aspect=self.width / self.height,
            )
        )

    def text(self, x, y, s, *, size, weight="normal", color=INK, ha="left", va="center", z=5, **kw):
        return self.fig.text(
            x / self.width,
            y / self.height,
            s,
            fontsize=size,
            weight=weight,
            color=color,
            ha=ha,
            va=va,
            zorder=z,
            **kw,
        )

    def arrow(self, x0, y0, x1, y1, *, color, lw=1.1):
        self.fig.add_artist(
            FancyArrowPatch(
                (x0 / self.width, y0 / self.height),
                (x1 / self.width, y1 / self.height),
                transform=self.fig.transFigure,
                arrowstyle="-|>",
                mutation_scale=7,
                linewidth=lw,
                color=color,
                zorder=6,
                shrinkA=0,
                shrinkB=0,
            )
        )

    def hline(self, x0, x1, y, *, color=HAIRLINE, lw=0.6):
        self.fig.add_artist(
            plt.Line2D(
                [x0 / self.width, x1 / self.width],
                [y / self.height, y / self.height],
                transform=self.fig.transFigure,
                color=color,
                linewidth=lw,
                zorder=2,
            )
        )

    def export(self, output_dir: Path, stem: str) -> dict[str, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        outputs = {suffix: output_dir / f"{stem}.{suffix}" for suffix in ("svg", "pdf", "png")}
        self.fig.savefig(outputs["svg"], facecolor=SURFACE)
        self.fig.savefig(outputs["pdf"], facecolor=SURFACE)
        self.fig.savefig(outputs["png"], dpi=PNG_DPI, facecolor=SURFACE)
        plt.close(self.fig)
        return outputs


# --------------------------------------------------------------------------- figure 2


def render_fig2(source_dir: Path = SRC, output_dir: Path = OUT) -> dict[str, Path]:
    margin = 0.05
    gap = 0.04
    cell_w = (TEXT_WIDTH_IN - 2 * margin - gap) / 2
    pad = 0.045
    station_h = 0.87
    station_w = station_h * 16 / 9
    inner_gap = 0.05
    detail_w = cell_w - 2 * pad - station_w - inner_gap
    detail_h = detail_w * 3 / 4
    title_h = 0.21
    cell_h = pad + station_h + title_h + pad
    height = 2 * cell_h + 3 * margin
    canvas = Canvas(TEXT_WIDTH_IN, height)

    for index, case in enumerate(fig2_cases()):
        row, column = divmod(index, 2)
        x = margin + column * (cell_w + gap)
        y = margin + (1 - row) * (cell_h + margin)
        canvas.box(x, y, cell_w, cell_h, radius=0.06)
        title_y = y + cell_h - title_h / 2 - 0.01
        canvas.text(
            x + pad,
            title_y,
            f"{chr(97 + index)}",
            size=FONT_PT["title"],
            weight="bold",
        )
        canvas.text(
            x + pad + 0.13,
            title_y,
            case.title,
            size=FONT_PT["title"],
            weight="bold",
        )
        canvas.text(
            x + cell_w - pad,
            title_y,
            f"Isaac scene · {case.revision}",
            size=FONT_PT["label"],
            color=MUTED,
            ha="right",
        )
        image_y = y + pad
        canvas.image(x + pad, image_y, station_w, station_h, source_dir / case.station)
        detail_x = x + pad + station_w + inner_gap
        detail_y = image_y + station_h - detail_h
        canvas.image(detail_x, detail_y, detail_w, detail_h, source_dir / case.detail)
        canvas.text(
            detail_x + detail_w / 2,
            image_y + (station_h - detail_h) / 2 - 0.005,
            case.action,
            size=FONT_PT["label"],
            weight="bold",
            color=TEAL,
            ha="center",
            wrap=True,
        )

    return canvas.export(output_dir, "fig2-gallery")


# --------------------------------------------------------------------------- figure 3


def render_fig3(source_dir: Path = SRC, output_dir: Path = OUT) -> dict[str, Path]:
    margin = 0.05
    image_w = 1.40
    card_w = 1.90
    panel_h = image_w / 1.15
    arrow_gap = (TEXT_WIDTH_IN - 2 * margin - 2 * image_w - card_w) / 2
    header_h = 0.24
    row_label_h = 0.19
    row_h = row_label_h + panel_h + 0.06
    height = margin + header_h + 2 * row_h + margin
    canvas = Canvas(TEXT_WIDTH_IN, height)

    column_x = (
        margin,
        margin + image_w + arrow_gap,
        margin + image_w + arrow_gap + card_w + arrow_gap,
    )
    column_w = (image_w, card_w, image_w)
    headers = ("Manufacturer evidence", "Agent-written contract", "Admitted USD")
    header_y = height - margin - header_h / 2
    for x, w, header, ha in zip(column_x, column_w, headers, ("left", "center", "right")):
        anchor = {"left": x, "center": x + w / 2, "right": x + w}[ha]
        canvas.text(anchor, header_y, header, size=FONT_PT["header"], weight="bold", ha=ha)
    canvas.hline(margin, TEXT_WIDTH_IN - margin, height - margin - header_h + 0.02)

    for index, case in enumerate(fig3_cases()):
        row_top = height - margin - header_h - index * row_h
        panel_y = row_top - row_label_h - panel_h
        label_y = row_top - row_label_h / 2
        canvas.text(
            column_x[0],
            label_y,
            f"{chr(97 + index)}  {case.title}",
            size=FONT_PT["title"],
            weight="bold",
            color=case.accent,
        )
        canvas.text(
            column_x[2] + image_w,
            label_y,
            case.admission,
            size=FONT_PT["meta"],
            color=MUTED,
            ha="right",
        )
        # evidence and USD panels share one aspect ratio
        canvas.image(column_x[0], panel_y, image_w, panel_h, source_dir / case.evidence)
        canvas.image(column_x[2], panel_y, image_w, panel_h, source_dir / case.usd)
        # contract card: spec identity plus four verifiable fields
        canvas.box(
            column_x[1],
            panel_y,
            card_w,
            panel_h,
            edge=case.accent,
            face="#FFF8EE" if index == 0 else "#EEF4FA",
            lw=0.8,
            radius=0.05,
        )
        canvas.text(
            column_x[1] + 0.09,
            panel_y + panel_h - 0.13,
            f"spec · {case.spec}",
            size=FONT_PT["meta"],
            color=MUTED,
        )
        body_top = panel_y + panel_h - 0.24
        line_gap = (body_top - panel_y - 0.06) / len(case.contract)
        for line_index, line in enumerate(case.contract):
            canvas.text(
                column_x[1] + 0.09,
                body_top - line_gap * (line_index + 0.5),
                line,
                size=FONT_PT["body"],
                weight="bold" if line_index == 1 else "normal",
            )
        # arrows: evidence → contract → USD
        mid = panel_y + panel_h / 2
        for start in (column_x[0] + image_w, column_x[1] + card_w):
            canvas.arrow(start + 0.04, mid, start + arrow_gap - 0.04, mid, color=case.accent)

    return canvas.export(output_dir, "fig3-real-spec-usd")


def main() -> int:
    render_fig2()
    render_fig3()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
