#!/usr/bin/env python3
"""Схемы двух узлов GoTo-привода для Добсона (OnStep).

Рисует два узла:
  1. Азимутальный привод (вид сверху) — печатная зубчатая корона вокруг
     оси M10, мотор NEMA17 с пиньоном, кронштейн на рокер-боксе.
  2. Высотный привод (вид сбоку) — печатный зубчатый сектор на высотном
     подшипнике R100, мотор NEMA17 с пиньоном на боковине рокера.

Цветовой код как в остальном проекте:
  оранжевый = печатная деталь (PETG), серый = металл/покупное.
"""
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, Rectangle, Wedge, FancyArrowPatch

PLASTIC = "#d98a3d"   # печать PETG
PLASTIC_E = "#9c5e22"
METAL = "#9aa3ad"     # сталь / алюминий
METAL_E = "#4a4f55"
WOOD = "#cdaa6d"      # фанера / деревянный подшипник
WOOD_E = "#8a6d3b"
MOTOR = "#3f4756"     # корпус мотора
MOTOR_E = "#20242c"

OUT = Path(__file__).parent / "images"
OUT.mkdir(exist_ok=True)


def gear_ring(ax, cx, cy, r, n_teeth, tooth_h, fc, ec, z=3, lw=1.4,
              a0=0.0, a1=360.0):
    """Зубчатое колесо/сектор: тело + прямоугольные зубья по дуге [a0,a1]."""
    # тело
    if a0 == 0.0 and a1 == 360.0:
        ax.add_patch(Circle((cx, cy), r, facecolor=fc, edgecolor=ec,
                            linewidth=lw, zorder=z))
    else:
        ax.add_patch(Wedge((cx, cy), r, a0, a1, facecolor=fc, edgecolor=ec,
                           linewidth=lw, zorder=z))
    # зубья
    span = a1 - a0
    for i in range(n_teeth):
        ang = math.radians(a0 + span * (i + 0.5) / n_teeth)
        tw = 2.0 * math.pi * r / n_teeth * 0.45   # ширина зуба
        # прямоугольный зуб, ориентированный радиально
        bx, by = cx + r * math.cos(ang), cy + r * math.sin(ang)
        tx, ty = math.cos(ang), math.sin(ang)        # радиальное направление
        px, py = -ty, tx                              # тангенциальное
        pts = [
            (bx + px * tw / 2, by + py * tw / 2),
            (bx + px * tw / 2 + tx * tooth_h, by + py * tw / 2 + ty * tooth_h),
            (bx - px * tw / 2 + tx * tooth_h, by - py * tw / 2 + ty * tooth_h),
            (bx - px * tw / 2, by - py * tw / 2),
        ]
        ax.add_patch(Polygon(pts, closed=True, facecolor=fc, edgecolor=ec,
                            linewidth=lw, zorder=z))


def nema17(ax, cx, cy, size, label_xy=None):
    """Корпус мотора NEMA17 (квадрат со срезанными углами) + вал."""
    s = size / 2
    chamf = size * 0.18
    pts = [
        (cx - s + chamf, cy - s), (cx + s - chamf, cy - s),
        (cx + s, cy - s + chamf), (cx + s, cy + s - chamf),
        (cx + s - chamf, cy + s), (cx - s + chamf, cy + s),
        (cx - s, cy + s - chamf), (cx - s, cy - s + chamf),
    ]
    ax.add_patch(Polygon(pts, closed=True, facecolor=MOTOR, edgecolor=MOTOR_E,
                        linewidth=1.6, zorder=6))
    ax.text(cx, cy, "NEMA 17", color="white", ha="center", va="center",
            fontsize=8, fontweight="bold", zorder=7)


def arrow(ax, xy0, xy1, color="#c0392b", lw=2.0):
    ax.add_patch(FancyArrowPatch(xy0, xy1, arrowstyle="-|>", mutation_scale=18,
                                 color=color, linewidth=lw, zorder=20))


def label(ax, x, y, text, xytext, color="black", fs=10, bold=False):
    ax.annotate(text, xy=(x, y), xytext=xytext, fontsize=fs,
                color=color, fontweight="bold" if bold else "normal",
                ha="left", va="center", zorder=21,
                arrowprops=dict(arrowstyle="-", color="#333", lw=1.0),
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#999",
                          alpha=0.95))


def legend(ax, x, y):
    items = [("печать PETG", PLASTIC, PLASTIC_E),
             ("металл / покупное", METAL, METAL_E),
             ("корпус мотора", MOTOR, MOTOR_E),
             ("дерево/фанера", WOOD, WOOD_E)]
    for i, (txt, fc, ec) in enumerate(items):
        yy = y - i * 16
        ax.add_patch(Rectangle((x, yy), 12, 10, facecolor=fc, edgecolor=ec,
                              linewidth=1.2, zorder=21))
        ax.text(x + 18, yy + 5, txt, fontsize=9, va="center", zorder=21)


# ---------------------------------------------------------------------------
# УЗЕЛ 1 — АЗИМУТАЛЬНЫЙ ПРИВОД (вид сверху)
# ---------------------------------------------------------------------------
def draw_azimuth():
    fig, ax = plt.subplots(figsize=(9, 9))
    ax.set_aspect("equal")
    ax.axis("off")

    R_BOARD = 170      # азимутальный круг (дно рокера), мм
    R_RING = 130       # печатная зубчатая корона, мм
    R_PTFE = 150       # радиус PTFE-пятаков

    # азимутальный круг (низ рокер-бокса) — дерево
    ax.add_patch(Circle((0, 0), R_BOARD, facecolor=WOOD, edgecolor=WOOD_E,
                        linewidth=1.6, zorder=1))

    # печатная зубчатая корона вокруг центра
    gear_ring(ax, 0, 0, R_RING, 96, 7, PLASTIC, PLASTIC_E, z=3)
    ax.add_patch(Circle((0, 0), R_RING - 22, facecolor=WOOD, edgecolor=PLASTIC_E,
                        linewidth=1.2, zorder=4))   # внутр. вырез короны

    # центральная ось M10
    ax.add_patch(Circle((0, 0), 9, facecolor=METAL, edgecolor=METAL_E,
                        linewidth=1.4, zorder=8))

    # 3 PTFE-пятака на 120°
    for a in (90, 210, 330):
        x = R_PTFE * math.cos(math.radians(a))
        y = R_PTFE * math.sin(math.radians(a))
        ax.add_patch(Circle((x, y), 9, facecolor=METAL, edgecolor=METAL_E,
                            linewidth=1.2, zorder=5))

    # мотор + пиньон у края короны (справа)
    pin_r = 16
    pin_x = R_RING + 7 + pin_r       # пиньон касается зубьев короны
    gear_ring(ax, pin_x, 0, pin_r, 14, 7, PLASTIC, PLASTIC_E, z=6)
    nema17(ax, pin_x + pin_r + 28, 0, 46)

    # кронштейн мотора (печать) — от края круга к мотору
    ax.add_patch(Rectangle((R_BOARD - 6, -28), pin_x + pin_r + 28 - (R_BOARD - 6),
                          56, facecolor=PLASTIC, edgecolor=PLASTIC_E,
                          linewidth=1.4, alpha=0.55, zorder=2))

    # стрелка вращения
    th = [math.radians(a) for a in range(120, 60, -3)]
    ax.plot([(R_RING + 22) * math.cos(t) for t in th],
            [(R_RING + 22) * math.sin(t) for t in th],
            color="#c0392b", lw=2.2, zorder=20)
    arrow(ax, ((R_RING + 22) * math.cos(th[-2]), (R_RING + 22) * math.sin(th[-2])),
          ((R_RING + 22) * math.cos(th[-1]), (R_RING + 22) * math.sin(th[-1])))

    # подписи
    label(ax, 0, 9, "Ось азимута M10\n(уже есть в проекте)", (-260, 150), bold=True)
    label(ax, R_RING * math.cos(math.radians(200)),
          R_RING * math.sin(math.radians(200)),
          "Печатная зубчатая корона\nØ~260 мм, ~96 зубьев", (-330, -120),
          color=PLASTIC_E, bold=True)
    label(ax, pin_x, pin_r, "Пиньон (печать)\n~14 зубьев", (120, 130),
          color=PLASTIC_E)
    label(ax, pin_x + pin_r + 28, 24, "Шаговый мотор\nNEMA 17", (120, 80), bold=True)
    label(ax, R_BOARD - 6, -28, "Кронштейн мотора (печать)\nна дно рокер-бокса",
          (60, -150), color=PLASTIC_E)
    label(ax, R_PTFE * math.cos(math.radians(330)),
          R_PTFE * math.sin(math.radians(330)),
          "PTFE-пятак (1 из 3)", (90, -210))

    ax.text(0, R_BOARD + 38, "УЗЕЛ 1 — АЗИМУТАЛЬНЫЙ ПРИВОД (вид сверху)",
            ha="center", fontsize=14, fontweight="bold")
    ax.text(0, -R_BOARD - 40,
            "Передаточное ~96:14 ≈ 6.9.  Мотор крутит корону → весь рокер "
            "поворачивается по азимуту.",
            ha="center", fontsize=9.5, color="#444")
    legend(ax, -R_BOARD - 95, 70)

    ax.set_xlim(-R_BOARD - 110, R_BOARD + 130)
    ax.set_ylim(-R_BOARD - 60, R_BOARD + 60)
    fig.tight_layout()
    p = OUT / "motor_azimuth_drive.png"
    fig.savefig(p, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print("written", p)


# ---------------------------------------------------------------------------
# УЗЕЛ 2 — ВЫСОТНЫЙ ПРИВОД (вид сбоку)
# ---------------------------------------------------------------------------
def draw_altitude():
    fig, ax = plt.subplots(figsize=(9, 9))
    ax.set_aspect("equal")
    ax.axis("off")

    R_BRG = 100        # высотный подшипник (деревянный круг), мм
    R_SEG = 100        # радиус зубчатого сектора (по краю подшипника)

    # боковина рокер-бокса с полукруглым вырезом (фон)
    ax.add_patch(Rectangle((-150, -150), 300, 150, facecolor="#efe7d6",
                          edgecolor=WOOD_E, linewidth=1.4, zorder=0))
    ax.add_patch(Wedge((0, 0), R_BRG + 6, 200, 340, facecolor="white",
                       edgecolor=WOOD_E, linewidth=1.2, zorder=1))  # вырез

    # высотный подшипник (деревянный круг)
    ax.add_patch(Circle((0, 0), R_BRG, facecolor=WOOD, edgecolor=WOOD_E,
                        linewidth=1.8, zorder=2))
    ax.add_patch(Circle((0, 0), 7, facecolor=METAL, edgecolor=METAL_E,
                        linewidth=1.2, zorder=4))   # центр оси высоты

    # PTFE-пятаки в вырезе (точки опоры)
    for a in (215, 325):
        x = (R_BRG + 1) * math.cos(math.radians(a))
        y = (R_BRG + 1) * math.sin(math.radians(a))
        ax.add_patch(Circle((x, y), 6, facecolor=METAL, edgecolor=METAL_E,
                            linewidth=1.0, zorder=5))

    # печатный зубчатый сектор на лицевой стороне подшипника (верхняя дуга)
    gear_ring(ax, 0, 0, R_SEG, 60, 7, PLASTIC, PLASTIC_E, z=3, a0=20, a1=160)
    ax.add_patch(Wedge((0, 0), R_SEG - 20, 20, 160, facecolor=WOOD,
                       edgecolor=PLASTIC_E, linewidth=1.0, zorder=3))

    # труба-люлька сверху (схематично)
    ax.add_patch(Rectangle((-34, R_BRG - 4), 68, 70, facecolor="#d7d2c4",
                          edgecolor=WOOD_E, linewidth=1.4, zorder=2))
    ax.text(0, R_BRG + 30, "люлька / труба", ha="center", fontsize=8,
            color="#555", zorder=6)

    # мотор с пиньоном, цепляется за зубья сектора сверху-слева
    seg_ang = math.radians(120)
    px = (R_SEG + 7 + 15) * math.cos(seg_ang)
    py = (R_SEG + 7 + 15) * math.sin(seg_ang)
    gear_ring(ax, px, py, 15, 13, 7, PLASTIC, PLASTIC_E, z=6)
    mdx, mdy = math.cos(seg_ang), math.sin(seg_ang)
    nema17(ax, px + mdx * 40, py + mdy * 40, 44)

    # кронштейн мотора (печать) на боковину
    ax.add_patch(Polygon([(px + mdx * 65, py + mdy * 65),
                          (px + mdx * 12, py + mdy * 12),
                          (px + mdx * 12 - 20, py + mdy * 12 + 20),
                          (px + mdx * 65 - 20, py + mdy * 65 + 20)],
                         closed=True, facecolor=PLASTIC, edgecolor=PLASTIC_E,
                         linewidth=1.4, alpha=0.55, zorder=2))

    # стрелка вращения (по высоте)
    th = [math.radians(a) for a in range(40, 90, 3)]
    ax.plot([(R_SEG + 24) * math.cos(t) for t in th],
            [(R_SEG + 24) * math.sin(t) for t in th],
            color="#c0392b", lw=2.2, zorder=20)
    arrow(ax, ((R_SEG + 24) * math.cos(th[-2]), (R_SEG + 24) * math.sin(th[-2])),
          ((R_SEG + 24) * math.cos(th[-1]), (R_SEG + 24) * math.sin(th[-1])))

    # подписи
    label(ax, 0, 0, "Ось высоты\n(центр подшипника)", (110, -40), bold=True)
    label(ax, R_BRG * math.cos(math.radians(250)),
          R_BRG * math.sin(math.radians(250)),
          "Высотный подшипник R100\n(дерево, уже есть)", (-150, -120),
          color=WOOD_E, bold=True)
    label(ax, R_SEG * math.cos(math.radians(60)),
          R_SEG * math.sin(math.radians(60)),
          "Печатный зубчатый сектор\nна лицо подшипника", (95, 95),
          color=PLASTIC_E, bold=True)
    label(ax, px, py, "Пиньон (печать)\n~13 зубьев", (-220, 70), color=PLASTIC_E)
    label(ax, px + mdx * 40, py + mdy * 40 + 22, "Шаговый мотор\nNEMA 17",
          (-260, 130), bold=True)
    label(ax, px + mdx * 45 - 18, py + mdy * 45 + 10,
          "Кронштейн мотора (печать)\nна боковину рокера", (-300, -10),
          color=PLASTIC_E)
    label(ax, (R_BRG) * math.cos(math.radians(325)),
          (R_BRG) * math.sin(math.radians(325)),
          "PTFE в вырезе\n(опора)", (110, -110))

    ax.text(0, R_BRG + 78, "УЗЕЛ 2 — ВЫСОТНЫЙ ПРИВОД (вид сбоку)",
            ha="center", fontsize=14, fontweight="bold")
    ax.text(0, -148,
            "Сектор зубьев нужен только на рабочий диапазон высоты (~0–90°). "
            "Мотор качает трубу вверх/вниз.",
            ha="center", fontsize=9.5, color="#444")
    legend(ax, 150, 55)

    ax.set_xlim(-160, 270)
    ax.set_ylim(-160, R_BRG + 100)
    fig.tight_layout()
    p = OUT / "motor_altitude_drive.png"
    fig.savefig(p, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print("written", p)


if __name__ == "__main__":
    draw_azimuth()
    draw_altitude()
