#!/usr/bin/env python3
"""Вид сверху: куда встают 3 скобы-ножки на оправе/коробке."""
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Polygon, FancyArrowPatch

OUT = Path(__file__).parent / "images" / "bracket_placement.png"
OUT.parent.mkdir(exist_ok=True)

PLASTIC = "#d98a3d"
PLASTIC_E = "#9c5e22"
METAL = "#7f8896"
CELL = "#cfd6dd"

EAR_R = 125.0
STUD_R = 132.0
BOX_HALF = 151.0
ANGLES = [30.0, 150.0, 270.0]

fig, ax = plt.subplots(figsize=(9, 9))

# Коробка (вид сверху, квадрат)
ax.add_patch(Rectangle((-BOX_HALF, -BOX_HALF), 2 * BOX_HALF, 2 * BOX_HALF,
                       fill=False, edgecolor="#555", linewidth=1.8,
                       linestyle="--"))
ax.text(0, -BOX_HALF - 12, "mirror box 302×302 (вид сверху)", ha="center",
        fontsize=11, color="#555")

# Оправа зеркала (круг Ø250)
ax.add_patch(Circle((0, 0), EAR_R, facecolor=CELL, edgecolor="#8a929b",
                    linewidth=1.5, zorder=2))
ax.add_patch(Circle((0, 0), 101.5, facecolor="#3a3f45", edgecolor="none",
                    zorder=3))  # зеркало Ø203
ax.text(0, 0, "ГЗ Ø203\nв оправе", ha="center", va="center",
        fontsize=10, color="white", zorder=4)

for ang in ANGLES:
    a = math.radians(ang)
    ex, ey = EAR_R * math.cos(a), EAR_R * math.sin(a)
    sx, sy = STUD_R * math.cos(a), STUD_R * math.sin(a)

    # ухо оправы (выступ)
    ax.add_patch(Circle((ex, ey), 13, facecolor=CELL, edgecolor="#8a929b",
                        linewidth=1.3, zorder=4))

    # скоба-ножка (прямоугольник 14×26, длинной стороной по касательной)
    bx = (EAR_R + 7) * math.cos(a)
    by = (EAR_R + 7) * math.sin(a)
    br = Rectangle((-7, -13), 14, 26, facecolor=PLASTIC, edgecolor=PLASTIC_E,
                   linewidth=1.6, zorder=5)
    t = (matplotlib.transforms.Affine2D()
         .rotate_deg(ang)
         .translate(bx, by) + ax.transData)
    br.set_transform(t)
    ax.add_patch(br)

    # шпилька M8 (точка) в скобе
    ax.add_patch(Circle((sx, sy), 4.5, facecolor=METAL, edgecolor="#333",
                        linewidth=1.2, zorder=6))

    # подпись угла
    lx, ly = (EAR_R + 48) * math.cos(a), (EAR_R + 48) * math.sin(a)
    ax.annotate(f"скоба-ножка\n+ шпилька M8\n({ang:.0f}°)", xy=(sx, sy),
                xytext=(lx, ly), ha="center", va="center", fontsize=10.5,
                color=PLASTIC_E,
                arrowprops=dict(arrowstyle="->", color=PLASTIC_E, lw=1.3))

# легенда
ax.add_patch(Rectangle((-145, 150), 16, 10, facecolor=PLASTIC,
                       edgecolor=PLASTIC_E))
ax.text(-124, 155, "скоба-ножка (печать ×3)", fontsize=10.5, va="center")
ax.add_patch(Circle((-137, 135), 5, facecolor=METAL, edgecolor="#333"))
ax.text(-124, 135, "шпилька M8 (×3, металл)", fontsize=10.5, va="center")

ax.set_title("Куда встают 3 скобы-ножки (вид сверху на оправу в коробке)",
             fontsize=13, pad=12)
ax.set_xlim(-175, 175)
ax.set_ylim(-185, 185)
ax.set_aspect("equal")
ax.axis("off")
fig.tight_layout()
fig.savefig(OUT, dpi=120, bbox_inches="tight")
print(f"saved -> {OUT}")
