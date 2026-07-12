#!/usr/bin/env python3
"""Раскладка деталей ручного высотного узла по столам Bambu H2D (350×320).
Вывод: 2 стола (седло+вышка+2 ролика на каждом). → verkhniy_yarus/_BED_LAYOUT.png"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pathlib import Path

BED_X, BED_Y = 350, 320
MARGIN = 3                      # печатная зона отступ от края

# footprint'ы из STL (поза печати): (dx, dy)
CRADLE = (257.0, 156.8)
APEX = (83.7, 76.9)
ROLLER = (35.0, 35.0)

# раскладка одного стола: (имя, x0, y0, w, h, цвет)
def plate_items(side):
    c = "R" if side == 0 else "L"
    return [
        (f"cradle_{c}\n(седло) 257×157", 6, 6, *CRADLE, "#8fbfe8"),
        (f"apex_{c}\n(вышка) 84×77", 6, 170, *APEX, "#f0a95a"),
        ("roller 35", 105, 170, *ROLLER, "#f0c040"),
        ("roller 35", 148, 170, *ROLLER, "#f0c040"),
    ]

fig, axes = plt.subplots(1, 2, figsize=(15, 8), dpi=115)
for si, ax in enumerate(axes):
    # стол + печатная зона
    ax.add_patch(Rectangle((0, 0), BED_X, BED_Y, fc="#f4f4f4", ec="k", lw=2))
    ax.add_patch(Rectangle((MARGIN, MARGIN), BED_X-2*MARGIN, BED_Y-2*MARGIN,
                           fc="none", ec="0.6", ls="--", lw=1))
    for name, x, y, w, h, col in plate_items(si):
        ax.add_patch(Rectangle((x, y), w, h, fc=col, ec="k", lw=1.4, alpha=0.9))
        ax.text(x + w/2, y + h/2, name, ha="center", va="center", fontsize=9, weight="bold")
    ax.set_xlim(-10, BED_X+10); ax.set_ylim(-10, BED_Y+10); ax.set_aspect("equal")
    ax.set_title(f"СТОЛ {si+1}: седло {'R' if si==0 else 'L'} + вышка + 2 ролика",
                 fontsize=13, weight="bold")
    ax.set_xlabel("350 мм"); ax.set_ylabel("320 мм")
    ax.grid(alpha=0.2)

fig.suptitle("Раскладка на Bambu H2D (350×320) — ручной высотный узел, PETG\n"
             "На ОДИН стол всё НЕ влезает: два седла = 2×157 = 314 мм ≈ вся ширина (без зазора).\n"
             "→ 2 стола, на каждом седло+вышка+2 ролика (≈140 г/стол). Итого 2 печати.",
             fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.90])
out = Path("print_queue/verkhniy_yarus/_BED_LAYOUT.png")
fig.savefig(out, dpi=115, bbox_inches="tight"); plt.close(fig)
print("→", out.resolve())
PY = None
