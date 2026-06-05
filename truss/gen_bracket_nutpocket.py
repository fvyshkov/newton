#!/usr/bin/env python3
"""Крупный план: шестигранный карман под гайку M5 на внешней грани скобы."""
from pathlib import Path

import numpy as np
import trimesh
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection

OUT = Path(__file__).parent / "images" / "bracket_nutpocket.png"
OUT.parent.mkdir(exist_ok=True)

m = trimesh.load(Path(__file__).parent / "stl" / "Cell_leg_bracket.stl")
tris = m.triangles
light = np.array([0.6, -0.5, 0.6]); light /= np.linalg.norm(light)
shade = 0.45 + 0.55 * np.clip(m.face_normals @ light, 0, 1)
base = np.array([0.85, 0.55, 0.25])
colors = np.clip(base[None, :] * shade[:, None], 0, 1)
ang = m.face_adjacency_angles
sharp = m.face_adjacency_edges[ang > np.radians(20)]
edges = m.vertices[sharp]

fig = plt.figure(figsize=(11, 7))

# общий вид с внешней грани
ax = fig.add_subplot(1, 2, 1, projection="3d")
ax.add_collection3d(Poly3DCollection(tris, facecolors=colors, edgecolors="none"))
ax.add_collection3d(Line3DCollection(edges, colors="#222", linewidths=0.6))
b0, b1 = m.bounds
ax.set_xlim(b0[0]-2, b1[0]+2); ax.set_ylim(b0[1]-2, b1[1]+2); ax.set_zlim(b0[2]-2, b1[2]+2)
ax.set_box_aspect(b1-b0); ax.view_init(elev=12, azim=70)
ax.set_xticks([]); ax.set_yticks([]); ax.set_zticks([])
ax.set_title("Внешняя грань целиком", fontsize=11)

# зум на верхнюю часть (карман у z=0)
ax2 = fig.add_subplot(1, 2, 2, projection="3d")
ax2.add_collection3d(Poly3DCollection(tris, facecolors=colors, edgecolors="none"))
ax2.add_collection3d(Line3DCollection(edges, colors="#222", linewidths=0.8))
ax2.set_xlim(0, 16); ax2.set_ylim(-13, 13); ax2.set_zlim(-18, 6)
ax2.set_box_aspect((16, 26, 24)); ax2.view_init(elev=10, azim=72)
ax2.set_xticks([]); ax2.set_yticks([]); ax2.set_zticks([])
ax2.set_title("ЗУМ: шестигранный карман под гайку M5\n(сюда вдавить гайку, болт вкрутить в неё)",
              fontsize=11)

fig.suptitle("Cell_leg_bracket.stl — зацепка через металлическую гайку, не через пластик",
             fontsize=13)
fig.tight_layout()
fig.savefig(OUT, dpi=120, bbox_inches="tight")
print(f"saved -> {OUT}")
