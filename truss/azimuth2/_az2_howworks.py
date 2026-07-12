#!/usr/bin/env python3
"""Как работает узел: кольца НЕ зацепляются зубьями — скользят по тефлону,
зубья верхнего кольца крутит ШЕСТЕРНЯ мотора сбоку. → az2_howworks.png"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, Polygon as MPoly

FIX = "#d98a3d"; ROT = "#e8b25a"; METAL = "#9aa3ad"; METAL_E="#4a4f55"
TEFLON = "#dfeef7"; TEFLON_E = "#6fa8c8"; WOOD = "#caa472"; RED="#c0392b"; GREEN="#0a7d3a"

fig, ax = plt.subplots(figsize=(15, 8.5))

def r(x, y, w, h, fc, ec="#7a4a1a", z=3, hatch=None, lw=1.5):
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec=ec, lw=lw, zorder=z, hatch=hatch))

# фанера
r(150, -16, 160, 16, WOOD, "#8a6d3b", hatch="////", z=1)
ax.text(160, -8, "ФАНЕРА (неподвижна)", fontsize=10, va="center", color="#5c4523", zorder=5)

# НИЖНЕЕ (неподвижное) кольцо — БЕЗ зубьев + буртик
r(176, 0, 42, 8, FIX, z=3)
r(180, 8, 5, 9, FIX, z=4)                       # буртик
ax.text(197, 4, "НИЖНЕЕ кольцо\nБЕЗ зубьев", ha="center", va="center", fontsize=9,
        weight="bold", color="#6b3d12", zorder=6)

# тефлон (скользкая прослойка)
r(189, 8, 24, 1.4, TEFLON, TEFLON_E, z=6)

# ВЕРХНЕЕ (вращающееся) кольцо — тело + зубья наружу
r(185.5, 9.4, 32, 7.6, ROT, z=5)                # тело
r(217.5, 9.4, 8.5, 10, ROT, z=5)                # обод зубьев
for k in range(4):                              # зубцы наружу (вправо)
    zc = 10 + k*2.4
    ax.add_patch(MPoly([(226, zc), (231, zc+1.1), (226, zc+2.2)], closed=True,
                       fc=ROT, ec="#7a4a1a", lw=0.8, zorder=5))

# гнездо стойки (торчит ВВЕРХ) + короткая труба
r(182, 9.4, 30, 30, ROT, z=7)                   # бобышка Ø30 z9..39
ax.add_patch(Rectangle((185.7, 12), 22.6, 28, fc="white", ec="#7a4a1a", lw=1, zorder=8))  # бор
r(186.7, 39, 20.6, 10, METAL, METAL_E, z=6)     # труба-стойка (обрезана)
ax.annotate("гнездо стойки Ø22 ↑ к седлу\n(торчит ВВЕРХ, внутри R197 —\nдорожке и шестерне НЕ мешает)",
            xy=(200, 44), xytext=(120, 40), fontsize=9, color="#6b3d12", ha="left",
            arrowprops=dict(arrowstyle="->", color="#6b3d12", lw=1.2), zorder=20)

# ШЕСТЕРНЯ мотора — сбоку, крутит зубья
r(233, 8, 30, 12, "#b5762e", "#7a4a1a", z=7)
for k in range(5):
    zc=9+k*2
    ax.add_patch(MPoly([(233, zc),(229,zc+1),(233,zc+2)], closed=True, fc="#b5762e",
                       ec="#7a4a1a", lw=0.7, zorder=8))
ax.text(248, 14, "ШЕСТЕРНЯ\nмотора 16T", ha="center", va="center", fontsize=8.5,
        weight="bold", color="w", zorder=9)
r(238, 20, 22, 24, METAL, METAL_E, z=6)
ax.text(249, 32, "NEMA17\nосью вниз", ha="center", va="center",
        fontsize=8, color="w", weight="bold", zorder=7)
ax.annotate("тут ЗАЦЕПЛЕНИЕ:\nзубья ↔ шестерня", xy=(230, 14), xytext=(250, 50),
            fontsize=9, color=RED, ha="center",
            arrowprops=dict(arrowstyle="->", color=RED, lw=1.4), zorder=20)

# левые выноски
ax.annotate("тефлон: верхнее\nскользит по нижнему", xy=(200, 8.7),
            xytext=(112, 24), fontsize=9, color=TEFLON_E, ha="left",
            arrowprops=dict(arrowstyle="->", color=TEFLON_E, lw=1.3), zorder=20)
ax.annotate("буртик центрирует\n(по внутр. окружности)", xy=(182.5, 13),
            xytext=(112, 40), fontsize=9, color="#6b3d12", ha="left",
            arrowprops=dict(arrowstyle="->", color="#6b3d12", lw=1.2), zorder=20)

# ==== ГЛАВНЫЕ ПОДПИСИ (чистая полоса сверху) ====
ax.text(112, 74, "1.  Кольца НЕ зацепляются зубьями друг с другом — скользят по тефлону (поворотный стол).",
        fontsize=12.5, weight="bold", color=RED)
ax.text(112, 67, "2.  Зубья — только на ВЕРХНЕМ кольце, смотрят НАРУЖУ; их крутит ШЕСТЕРНЯ мотора СБОКУ.",
        fontsize=12.5, weight="bold", color=GREEN)
ax.text(112, 60, "3.  Нижнее кольцо — БЕЗ зубьев, просто дорожка + буртик, прикручено к фанере.",
        fontsize=12.5, weight="bold", color="#5c4523")

ax.set_xlim(108, 300); ax.set_ylim(-22, 80)
ax.set_aspect("equal"); ax.axis("off")
ax.set_title("Азимут v2 — как это работает (разрез сбоку). z=0 — верх фанеры",
             fontsize=14, weight="bold", pad=12)
fig.tight_layout()
fig.savefig("az2_howworks.png", dpi=120, bbox_inches="tight")
print("saved -> az2_howworks.png")
