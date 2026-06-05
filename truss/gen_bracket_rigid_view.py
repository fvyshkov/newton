#!/usr/bin/env python3
"""Новый ЖЁСТКИЙ кронштейн: разнесённый + собранный вид."""
from pathlib import Path

import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

OUT = Path(__file__).parent / "images" / "bracket_rigid_view.png"
OUT.parent.mkdir(exist_ok=True)

ORANGE = (0.85, 0.54, 0.24)   # кронштейн
TAN = (0.79, 0.55, 0.31)      # дно коробки
CELL = (0.73, 0.77, 0.82)     # ухо оправы
METAL = (0.55, 0.59, 0.65)


def cyl(r, h, axis="z", at=(0, 0, 0), sections=40):
    c = trimesh.creation.cylinder(radius=r, height=h, sections=sections)
    if axis == "x":
        c.apply_transform(rotation_matrix(np.radians(90), [0, 1, 0]))
    c.apply_translation(at)
    return c


def box(ext, at):
    b = trimesh.creation.box(extents=ext)
    b.apply_translation(at)
    return b


bracket = trimesh.load(Path(__file__).parent / "stl" / "Cell_leg_bracket.stl")

ear = box((26, 26, 8), at=(-13, 0, 30))
m5h = trimesh.util.concatenate([cyl(2.5, 42, "x", (-5, 0, 30)),
                                cyl(4.5, 4, "x", (-26, 0, 30))])
floor = box((90, 70, 12), at=(7, 0, -6))
m5v = trimesh.util.concatenate([cyl(2.5, 34, "z", (7, 0, -5)),
                                cyl(4.5, 4, "z", (7, 0, -20)),
                                cyl(6.5, 1.5, "z", (7, 0, -13))])  # болт+головка+шайба

PARTS = [
    ("ухо задней плиты\n(оправа)", ear, CELL, (-44, 0, 0)),
    ("болт M5 (к уху)", m5h, METAL, (-92, 0, 0)),
    ("КРОНШТЕЙН\n(печать ×3)", bracket, ORANGE, (0, 0, 0)),
    ("дно коробки", floor, TAN, (0, 0, -38)),
    ("болт M5 снизу\n+ шайба", m5v, METAL, (0, 0, -70)),
]

light = np.array([0.5, -0.55, 0.7]); light /= np.linalg.norm(light)


def draw(ax, explode):
    ta, ca = [], []
    for _, mesh, col, off in PARTS:
        mm = mesh.copy()
        if explode:
            mm.apply_translation(off)
        shade = 0.5 + 0.5 * np.clip(mm.face_normals @ light, 0, 1)
        ca.append(np.clip(np.array(col)[None] * shade[:, None], 0, 1))
        ta.append(mm.triangles)
    ax.add_collection3d(Poly3DCollection(np.vstack(ta), facecolors=np.vstack(ca),
                                         edgecolors=(0, 0, 0, 0.18), linewidths=0.25))
    ax.set_xlim(-110, 35); ax.set_ylim(-55, 55); ax.set_zlim(-130, 55)
    ax.set_box_aspect((145, 110, 185))
    ax.view_init(elev=15, azim=-72)
    ax.set_axis_off()


fig = plt.figure(figsize=(15, 9))
ax1 = fig.add_subplot(1, 2, 1, projection="3d")
draw(ax1, True)
ax1.set_title("РАЗНЕСЁННЫЙ — что во что", fontsize=13)
lbl = {
    "ухо задней плиты\n(оправа)": (-58, 0, 40),
    "болт M5 (к уху)": (-95, 0, 42),
    "КРОНШТЕЙН\n(печать ×3)": (12, 0, 30),
    "дно коробки": (-55, 0, -52),
    "болт M5 снизу\n+ шайба": (32, 0, -105),
}
for name, *_ in PARTS:
    if name in lbl:
        x, y, z = lbl[name]
        ax1.text(x, y, z, name, fontsize=10, ha="center", color="#222")

ax2 = fig.add_subplot(1, 2, 2, projection="3d")
draw(ax2, False)
ax2.set_title("СОБРАНО", fontsize=13)

fig.suptitle("Жёсткий кронштейн оправы — без шпильки/барашков. "
             "Регулировка = штатный push-pull оправы", fontsize=13)
fig.tight_layout()
fig.savefig(OUT, dpi=115, bbox_inches="tight")
print(f"saved -> {OUT}")
