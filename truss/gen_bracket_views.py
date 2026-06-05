#!/usr/bin/env python3
"""Cell_leg_bracket.stl с 4 ракурсов — затенение + контурные рёбра."""
from pathlib import Path

import numpy as np
import trimesh
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection

OUT = Path(__file__).parent / "images" / "bracket_views.png"
OUT.parent.mkdir(exist_ok=True)

m = trimesh.load(Path(__file__).parent / "stl" / "Cell_leg_bracket.stl")
tris = m.triangles

# затенение: ambient + diffuse
light = np.array([0.5, -0.6, 0.7])
light /= np.linalg.norm(light)
diff = np.clip(m.face_normals @ light, 0, 1)
shade = 0.45 + 0.55 * diff
base = np.array([0.80, 0.83, 0.87])
colors = np.clip(base[None, :] * shade[:, None], 0, 1)

# контурные рёбра (где излом > 25°)
ang = m.face_adjacency_angles
sharp = m.face_adjacency_edges[ang > np.radians(25)]
edge_segs = m.vertices[sharp]  # (E,2,3)

b0, b1 = m.bounds
ctr = (b0 + b1) / 2

VIEWS = [
    (20, -55, "1) 3/4 со стороны уха (вогнутая грань x=0)"),
    (20, 125, "2) 3/4 с внешней грани (карман гайки M5)"),
    (78, -90, "3) сверху (вход M8 + проточка под шайбу)"),
    (4, -90, "4) сбоку (видно сквозное M8 по всей высоте)"),
]

fig = plt.figure(figsize=(13, 12))
for i, (elev, azim, title) in enumerate(VIEWS, 1):
    ax = fig.add_subplot(2, 2, i, projection="3d")
    ax.add_collection3d(Poly3DCollection(tris, facecolors=colors,
                                         edgecolors="none"))
    ax.add_collection3d(Line3DCollection(edge_segs, colors="#222",
                                         linewidths=0.7))
    ax.set_xlim(b0[0] - 2, b1[0] + 2)
    ax.set_ylim(b0[1] - 2, b1[1] + 2)
    ax.set_zlim(b0[2] - 2, b1[2] + 2)
    ax.set_box_aspect(b1 - b0)
    ax.view_init(elev=elev, azim=azim)
    ax.set_title(title, fontsize=11.5)
    ax.set_xticks([]); ax.set_yticks([]); ax.set_zticks([])
    ax.set_xlabel("X радиал"); ax.set_zlabel("Z верт")

fig.suptitle("Cell_leg_bracket.stl — 14×26×60 мм (печать ×3). "
             "Вогнутая грань → к уху; гориз. Ø5.5 → болт M5; верт. Ø9 → шпилька M8",
             fontsize=12)
fig.tight_layout()
fig.savefig(OUT, dpi=115, bbox_inches="tight")
print(f"saved -> {OUT}")
