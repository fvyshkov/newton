#!/usr/bin/env python3
"""Аннотированный вид Cell_leg_bracket.stl — что за что отвечает."""
from pathlib import Path

import numpy as np
import trimesh
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

OUT = Path(__file__).parent / "images" / "bracket_annotated.png"
OUT.parent.mkdir(exist_ok=True)

m = trimesh.load(Path(__file__).parent / "stl" / "Cell_leg_bracket.stl")
tris = m.triangles  # (F,3,3)

# простое ламбертово затенение
light = np.array([0.4, -0.7, 0.6])
light = light / np.linalg.norm(light)
n = m.face_normals
shade = np.clip(n @ light, 0.15, 1.0)
base = np.array([0.62, 0.66, 0.71])
colors = np.clip(base[None, :] * shade[:, None], 0, 1)


def make_ax(fig, pos, elev, azim, title):
    ax = fig.add_subplot(pos, projection="3d")
    coll = Poly3DCollection(tris, facecolors=colors, edgecolors="none")
    ax.add_collection3d(coll)
    b0, b1 = m.bounds
    ax.set_xlim(b0[0] - 2, b1[0] + 2)
    ax.set_ylim(b0[1] - 2, b1[1] + 2)
    ax.set_zlim(b0[2] - 2, b1[2] + 2)
    ax.set_box_aspect((b1 - b0))
    ax.view_init(elev=elev, azim=azim)
    ax.set_xlabel("X (радиально)")
    ax.set_ylabel("Y (ширина)")
    ax.set_zlabel("Z (вертикаль)")
    ax.set_title(title, fontsize=12)
    return ax


fig = plt.figure(figsize=(14, 7))

# Вид 1 — со стороны вогнутой грани (внутренняя, к уху оправы)
ax1 = make_ax(fig, 121, elev=18, azim=-60,
              title="Вид со стороны уха оправы (вогнутая грань)")
ax1.text2D(0.02, 0.95,
           "Вогнутая грань (x=0) —\nприжимается к круглому уху оправы",
           transform=ax1.transAxes, fontsize=10, color="#6a3d00")
ax1.text2D(0.02, 0.06,
           "Сквозное Ø9 (вертикаль) —\nнадевается на шпильку M8",
           transform=ax1.transAxes, fontsize=10, color="#003a6a")

# Вид 2 — со стороны внешней грани (карман гайки + торец M5)
ax2 = make_ax(fig, 122, elev=18, azim=120,
              title="Вид с внешней грани (карман гайки M5)")
ax2.text2D(0.02, 0.95,
           "Горизонтальное Ø5.5 (ось X) —\nболт M5 к уху оправы",
           transform=ax2.transAxes, fontsize=10, color="#003a6a")
ax2.text2D(0.02, 0.06,
           "Шестигранный карман —\nгайка M5 (вдавить при сборке)",
           transform=ax2.transAxes, fontsize=10, color="#6a3d00")

fig.suptitle("Cell_leg_bracket.stl  —  14×26×60 мм, печать ×3", fontsize=14)
fig.tight_layout()
fig.savefig(OUT, dpi=120, bbox_inches="tight")
print(f"saved -> {OUT}")
