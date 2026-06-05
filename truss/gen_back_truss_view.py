#!/usr/bin/env python3
"""Вид новой совмещённой детали: задняя плита + ножки."""
from pathlib import Path

import numpy as np
import trimesh
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection

OUT = Path(__file__).parent / "images" / "back_truss_view.png"
OUT.parent.mkdir(exist_ok=True)

m = trimesh.load(Path(__file__).parent / "stl" / "Mirror_cell_back_truss.stl")
tris = m.triangles
light = np.array([0.5, -0.5, 0.75]); light /= np.linalg.norm(light)
shade = 0.45 + 0.55 * np.clip(m.face_normals @ light, 0, 1)
base = np.array([0.85, 0.55, 0.25])
colors = np.clip(base[None] * shade[:, None], 0, 1)
ang = m.face_adjacency_angles
edges = m.vertices[m.face_adjacency_edges[ang > np.radians(35)]]
b0, b1 = m.bounds


def setup(ax, elev, azim, title):
    ax.add_collection3d(Poly3DCollection(tris, facecolors=colors, edgecolors="none"))
    ax.add_collection3d(Line3DCollection(edges, colors="#333", linewidths=0.4))
    ax.set_xlim(b0[0], b1[0]); ax.set_ylim(b0[1], b1[1]); ax.set_zlim(b0[2]-2, b1[2]+2)
    ax.set_box_aspect((b1[0]-b0[0], b1[1]-b0[1], (b1[2]-b0[2])*2.2))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off(); ax.set_title(title, fontsize=12)


fig = plt.figure(figsize=(15, 7.5))
ax1 = fig.add_subplot(1, 2, 1, projection="3d")
setup(ax1, 22, -60, "Сверху-сбоку: плита + 3 ножки\n(6 отв. коллимации, вент, фестоны)")
ax2 = fig.add_subplot(1, 2, 2, projection="3d")
setup(ax2, -32, -60, "Снизу: углубления ножек под бобышки дна\n+ верт. отв. M5 + пазы гаек")

fig.suptitle("Mirror_cell_back_truss.stl — задняя плита оправы заодно с ножками "
             "(1 деталь, винтится в коробку 3 болтами M5 снизу)", fontsize=13)
fig.tight_layout()
fig.savefig(OUT, dpi=115, bbox_inches="tight")
print(f"saved -> {OUT}")
