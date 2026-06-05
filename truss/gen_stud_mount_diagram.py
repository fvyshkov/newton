#!/usr/bin/env python3
"""Разрез узла крепления оправы на шпильке M8 (вариант "две гайки").

Показывает что металл (покупное), а что пластик (печать).
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle, FancyArrowPatch

PLASTIC = "#d98a3d"   # печатный PETG (оранжевый)
PLASTIC_E = "#9c5e22"
METAL = "#9aa3ad"     # сталь
METAL_E = "#4a4f55"

OUT = Path(__file__).parent / "images" / "stud_mount_diagram.png"
OUT.parent.mkdir(exist_ok=True)


def hatched_rect(ax, x, y, w, h, fc, ec, hatch=None, z=2):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec,
                           linewidth=1.6, hatch=hatch, zorder=z))


def threaded_rod(ax, cx, y0, y1, w):
    """Вертикальный резьбовой стержень с насечкой резьбы."""
    ax.add_patch(Rectangle((cx - w / 2, y0), w, y1 - y0, facecolor=METAL,
                           edgecolor=METAL_E, linewidth=1.4, zorder=5))
    yy = y0
    step = 3.0
    while yy < y1:
        ax.plot([cx - w / 2, cx + w / 2], [yy, yy + step * 0.6],
                color=METAL_E, linewidth=0.5, zorder=6)
        yy += step


def hex_nut(ax, cx, cy, w, h, label=None):
    """Гайка сбоку — шестигранник в профиль (прямоугольник со срезами)."""
    pts = [(cx - w / 2, cy - h / 2 + h * 0.18),
           (cx - w / 2, cy + h / 2 - h * 0.18),
           (cx - w / 2 + w * 0.15, cy + h / 2),
           (cx + w / 2 - w * 0.15, cy + h / 2),
           (cx + w / 2, cy + h / 2 - h * 0.18),
           (cx + w / 2, cy - h / 2 + h * 0.18),
           (cx + w / 2 - w * 0.15, cy - h / 2),
           (cx - w / 2 + w * 0.15, cy - h / 2)]
    ax.add_patch(Polygon(pts, closed=True, facecolor=METAL, edgecolor=METAL_E,
                         linewidth=1.4, zorder=7))


def wing_nut(ax, cx, cy, w, h):
    """Барашковая гайка — гайка с двумя 'крыльями'."""
    hex_nut(ax, cx, cy, w, h)
    for s in (-1, 1):
        wing = [(cx + s * w / 2, cy - h * 0.18),
                (cx + s * w / 2, cy + h * 0.18),
                (cx + s * (w / 2 + w * 0.7), cy + h * 0.9),
                (cx + s * (w / 2 + w * 0.85), cy + h * 0.55),
                (cx + s * (w / 2 + w * 0.5), cy)]
        ax.add_patch(Polygon(wing, closed=True, facecolor=METAL,
                             edgecolor=METAL_E, linewidth=1.3, zorder=7))


def washer(ax, cx, cy, w, h):
    ax.add_patch(Rectangle((cx - w / 2, cy - h / 2), w, h, facecolor=METAL,
                           edgecolor=METAL_E, linewidth=1.2, zorder=7))


def label(ax, x, y, text, tx, ty, color="#222", ha="left"):
    ax.annotate(text, xy=(x, y), xytext=(tx, ty), fontsize=10.5, ha=ha,
                va="center", color=color,
                arrowprops=dict(arrowstyle="->", color=color, lw=1.3))


fig, ax = plt.subplots(figsize=(9.5, 9.0))
cx = 0.0
RW = 8.0  # ширина шпильки

# --- ШПИЛЬКА (металл) ---
threaded_rod(ax, cx, 6, 150, RW)

# --- ДНО КОРОБКИ (пластик, печать) ---
floor_y, floor_h = 40, 14
hatched_rect(ax, -75, floor_y, 150, floor_h, PLASTIC, PLASTIC_E, hatch="////", z=3)
# отверстие Ø9 в дне (зазор под шпильку — БЕЗ резьбы)
ax.add_patch(Rectangle((cx - RW / 2 - 1.2, floor_y - 0.5), RW + 2.4, floor_h + 1,
                       facecolor="white", edgecolor="none", zorder=4))
threaded_rod(ax, cx, 6, 150, RW)  # перерисовать стержень поверх дыры

# --- НИЖНИЙ АНКЕР: шайба + гайка под дном (металл) ---
washer(ax, cx, floor_y - 3.0, 30, 4)
hex_nut(ax, cx, floor_y - 12, 26, 12)

# --- НИЖНИЙ БАРАШЕК (регулировочный, металл) ---
low_wn_y = 70
wing_nut(ax, cx, low_wn_y, 24, 13)

# --- СКОБА-НОЖКА (пластик, печать) ---
# горизонтальный фланец с отверстием под шпильку, лежит на нижнем барашке
flange_y = low_wn_y + 6.5 + 2
hatched_rect(ax, -34, flange_y, 68, 13, PLASTIC, PLASTIC_E, hatch="\\\\", z=8)
ax.add_patch(Rectangle((cx - RW / 2 - 1.2, flange_y - 0.5), RW + 2.4, 14,
                       facecolor="white", edgecolor="none", zorder=9))
threaded_rod(ax, cx, 6, 150, RW)
# стойка скобы поднимается вверх-влево к уху оправы
hatched_rect(ax, -34, flange_y, 16, 46, PLASTIC, PLASTIC_E, hatch="\\\\", z=8)

# --- ВЕРХНИЙ БАРАШЕК (контрит скобу, металл) ---
up_wn_y = flange_y + 13 + 6.5
wing_nut(ax, cx, up_wn_y, 24, 13)

# --- УХО ОПРАВЫ + горизонтальный болт M5 (металл болт) ---
ear_y = flange_y + 40
hatched_rect(ax, -70, ear_y - 8, 36, 18, PLASTIC, PLASTIC_E, hatch="xx", z=6)
# болт M5 горизонтально сквозь ухо в скобу
ax.add_patch(Rectangle((-66, ear_y - 2.2), 50, 4.4, facecolor=METAL,
                       edgecolor=METAL_E, linewidth=1.2, zorder=10))
ax.add_patch(Rectangle((-70, ear_y - 4), 5, 8, facecolor=METAL,
                       edgecolor=METAL_E, linewidth=1.2, zorder=10))  # головка

# === ПОДПИСИ ===
# правая колонка
RX = 86
label(ax, cx + RW / 2, 142, "ШПИЛЬКА M8×80 (металл,\nпокупное — стальная резьба)",
      RX, 144, color=METAL_E)
label(ax, cx + 13, up_wn_y, "верхний барашек M8 —\nКОНТРИТ скобу сверху",
      RX, 113, color="#b00", ha="left")
label(ax, cx + 13, low_wn_y, "нижний барашек M8 —\nРЕГУЛИРОВОЧНЫЙ (высота)",
      RX, 70, color="#b00", ha="left")
label(ax, 62, floor_y + floor_h / 2, "ДНО КОРОБКИ (печать).\nОтверстие Ø9 гладкое,\nбез резьбы",
      RX, 33, color=PLASTIC_E, ha="left")
label(ax, cx, floor_y - 12, "гайка + шайба M8 снизу —\nфиксируют шпильку в дне",
      RX, -2, color=METAL_E)

# левая колонка
LX = -132
label(ax, -52, ear_y - 6, "оправа зеркала (печать)",
      LX, ear_y + 20, color=PLASTIC_E, ha="left")
label(ax, -68, ear_y, "болт M5×20\n(сквозь ухо в скобу)",
      LX, ear_y - 6, color=METAL_E, ha="left")
label(ax, -30, flange_y + 28, "СКОБА-НОЖКА (печать)",
      LX, flange_y + 4, color=PLASTIC_E, ha="left")

# стрелка хода регулировки
ax.add_patch(FancyArrowPatch((40, low_wn_y - 4), (40, up_wn_y + 4),
             arrowstyle="<->", mutation_scale=18, color="#b00", lw=2, zorder=12))
ax.text(43, (low_wn_y + up_wn_y) / 2, "ход\nрегул.", fontsize=10.5,
        color="#b00", va="center")

# легенда
ax.add_patch(Rectangle((LX, -16), 12, 7, facecolor=METAL, edgecolor=METAL_E))
ax.text(LX + 16, -12.5, "металл (покупное)", fontsize=11, va="center")
ax.add_patch(Rectangle((LX, -28), 12, 7, facecolor=PLASTIC,
                       edgecolor=PLASTIC_E, hatch="//"))
ax.text(LX + 16, -24.5, "пластик (3D-печать)", fontsize=11, va="center")

ax.set_title("Узел крепления оправы на шпильке M8 (разрез, вариант «две гайки»)",
             fontsize=13, pad=14)
ax.set_xlim(-145, 162)
ax.set_ylim(-34, 156)
ax.set_aspect("equal")
ax.axis("off")
fig.tight_layout()
fig.savefig(OUT, dpi=130, bbox_inches="tight")
print(f"saved -> {OUT}")
