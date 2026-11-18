#!/usr/bin/env python3
"""Схема прижима венца (az2_hold_clamp): радиальный разрез у скобы."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

import generate_az2 as G
import generate_az2_clamps as C

WOOD = "#caa472"; FIX = "#d98a3d"; ROT = "#e0a94a"; CLAMP = "#5b8dbf"
TEFLON = "#e8f0f5"; SHOE = "#b8b8b8"; E = "#6b4a1d"

fig, ax = plt.subplots(figsize=(11, 5))


def rect(x, y, w, h, fc, ec=E, z=3, alpha=1.0, hatch=None):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec,
                           linewidth=1.2, zorder=z, alpha=alpha, hatch=hatch))


# фанера
rect(170, -6, 100, 6, WOOD)
ax.text(175, -3, "фанера", va="center", fontsize=9)

# неподвижное кольцо: тело z0..8 + буртик R180..185 z8..17
rect(G.FIX_R_IN, 0, G.FIX_R_OUT - G.FIX_R_IN, G.BODY_T, FIX)
rect(G.LIP_R_IN, G.FIX_Z1, G.LIP_R_OUT - G.LIP_R_IN, G.LIP_Z1 - G.FIX_Z1, FIX)
ax.text(196, 4, "неподвижное кольцо", fontsize=9, va="center")

# тефлон
rect(G.PAD_R - G.PAD_D / 2, G.FIX_Z1, G.PAD_D, 1.0, TEFLON, z=4)

# вращающееся: тело z9..17, обод+зубья z9..19
rect(G.ROT_R_IN, G.ROT_Z0, G.BODY_R_OUT - G.ROT_R_IN, G.BODY_T, ROT)
rect(G.RIM_R_IN, G.ROT_Z0, G.RING_ROOT_R - G.RIM_R_IN, G.RIM_H, ROT)
rect(G.RING_ROOT_R, G.ROT_Z0, G.RING_TIP_R - G.RING_ROOT_R, G.RIM_H, ROT,
     hatch="///", alpha=0.85)
ax.text(200, 13, "венец (вращается)", fontsize=9, va="center")
ax.annotate("зубья (верш. R226)", xy=(G.RING_TIP_R, 14), xytext=(238, 12),
            fontsize=8.5, arrowprops=dict(arrowstyle="->", lw=1))
ax.annotate("верх обода z=19", xy=(219.5, G.ROT_RIM_Z1), xytext=(180, 22.5),
            fontsize=8.5, arrowprops=dict(arrowstyle="->", lw=1))

# башмак ноги (метёт по кругу) — пунктиром
rect(188.0, G.ROT_Z1, 217.1 - 188.0, 8, SHOE, alpha=0.45)
ax.text(202, 21, "башмак ноги (метёт, R<218)", fontsize=8.5, va="center", style="italic")

# скоба: подошва / стенка / язык
rect(C.WALL_R_IN, 0, C.FOOT_R_OUT - C.WALL_R_IN, C.FOOT_T, CLAMP, z=5)
rect(C.WALL_R_IN, 0, C.WALL_T, C.FINGER_Z1, CLAMP, z=5)
rect(C.FINGER_R_IN, C.FINGER_Z0, C.WALL_R_OUT - C.FINGER_R_IN, C.FINGER_T, CLAMP, z=5)
ax.text(247, 8.5, "az2_hold_clamp\n(3 шт, шурупы 3.5–4×25)", fontsize=9,
        ha="center", color="#1f4e79")
for r in C.SCREW_R:
    ax.plot([r, r], [-5, C.FOOT_T], color="#333", lw=1.6, zorder=6)

# зазор
ax.annotate("", xy=(224, G.ROT_RIM_Z1), xytext=(224, C.FINGER_Z0),
            arrowprops=dict(arrowstyle="<->", lw=1.2, color="#c0392b"), zorder=20)
ax.annotate(f"зазор {C.GAP} мм", xy=(224, 19.2), xytext=(224, 27),
            fontsize=9.5, color="#c0392b", ha="center", zorder=20,
            bbox=dict(fc="white", ec="#c0392b", lw=0.8),
            arrowprops=dict(arrowstyle="->", lw=1.1, color="#c0392b"))
ax.annotate(f"R{C.FINGER_R_IN:.0f}", xy=(C.FINGER_R_IN, C.FINGER_Z0 + 2.5),
            xytext=(207, 27), fontsize=8.5,
            arrowprops=dict(arrowstyle="->", lw=1))
ax.annotate(f"R{C.WALL_R_IN:.0f}", xy=(C.WALL_R_IN, 10), xytext=(236, 16),
            fontsize=8.5, arrowprops=dict(arrowstyle="->", lw=1))

ax.set_xlim(170, 268); ax.set_ylim(-7, 30)
ax.set_aspect("equal"); ax.grid(alpha=0.25)
ax.set_xlabel("R, мм (от оси азимута)"); ax.set_ylabel("z, мм (0 = верх фанеры)")
ax.set_title("Прижим венца az2: язык над ободом зубьев, стенка снаружи зубьев")
out = Path(__file__).parent / "az2_clamp_scheme.png"
fig.tight_layout(); fig.savefig(out, dpi=150)
print(out)
