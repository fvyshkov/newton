#!/usr/bin/env python3
"""Как соединяется скоба-ножка: разнесённая (exploded) + собранная сборка."""
from pathlib import Path

import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

OUT = Path(__file__).parent / "images" / "bracket_exploded.png"
OUT.parent.mkdir(exist_ok=True)

ORANGE = (0.85, 0.54, 0.24)   # скоба (печать)
TAN = (0.79, 0.55, 0.31)      # дно коробки (печать)
CELL = (0.73, 0.77, 0.82)     # оправа/ухо (печать, др. цвет)
METAL = (0.55, 0.59, 0.65)    # металл


def cyl(r, h, axis="z", at=(0, 0, 0), sections=48):
    c = trimesh.creation.cylinder(radius=r, height=h, sections=sections)
    if axis == "x":
        c.apply_transform(rotation_matrix(np.radians(90), [0, 1, 0]))
    c.apply_translation(at)
    return c


def wing_nut(at, r=8.0, h=6.0):
    """Барашек: шестигранник по Z + два крыла."""
    parts = [cyl(r, h, "z", at, sections=6)]
    for s in (-1, 1):
        w = trimesh.creation.box(extents=(3, 14, h * 0.8))
        w.apply_translation([at[0], at[1] + s * (r + 6), at[2]])
        parts.append(w)
    return trimesh.util.concatenate(parts)


def box(ext, at):
    b = trimesh.creation.box(extents=ext)
    b.apply_translation(at)
    return b


# === детали в СОБРАННЫХ позициях (локальная рамка скобы) ===
bracket = trimesh.load(Path(__file__).parent / "stl" / "Cell_leg_bracket.stl")

# ухо оправы — кусок пластины с выступом, прижат к вогнутой грани (x=0)
ear = box((26, 26, 16), at=(-13, 0, 0))
# болт M5 поперёк (ось X) + головка
m5 = cyl(2.5, 40, "x", at=(-5, 0, 0))
m5_head = cyl(4.5, 4, "x", at=(-26, 0, 0))
# шпилька M8 вертикально через канал скобы (x=7,y=0)
stud = cyl(4.0, 95, "z", at=(7, 0, -30))
# барашки
low_nut = wing_nut((7, 0, -60))
up_nut = wing_nut((7, 0, 9))
# дно коробки
floor = box((90, 70, 12), at=(7, 0, -78))
# анкер-гайка под дном
anchor = cyl(7, 8, "z", at=(7, 0, -88), sections=6)

# (mesh, color, explode-offset)
PARTS = [
    ("ухо оправы\n(печать)", ear, CELL, (-42, 0, 0)),
    ("болт M5×20", trimesh.util.concatenate([m5, m5_head]), METAL, (-90, 0, 0)),
    ("СКОБА-НОЖКА\n(печать)", bracket, ORANGE, (0, 0, 0)),
    ("верхний барашек M8", up_nut, METAL, (0, 0, 48)),
    ("шпилька M8\n(металл)", stud, METAL, (0, 0, -60)),
    ("нижний барашек M8\n(высота)", low_nut, METAL, (0, 0, -30)),
    ("дно коробки\n(печать)", floor, TAN, (0, 0, -55)),
    ("гайка+шайба\nснизу", anchor, METAL, (0, 0, -78)),
]

light = np.array([0.5, -0.55, 0.7]); light /= np.linalg.norm(light)


def draw(ax, explode):
    alltris, allcol = [], []
    for name, mesh, col, off in PARTS:
        mm = mesh.copy()
        if explode:
            mm.apply_translation(off)
        shade = 0.5 + 0.5 * np.clip(mm.face_normals @ light, 0, 1)
        c = np.clip(np.array(col)[None, :] * shade[:, None], 0, 1)
        alltris.append(mm.triangles)
        allcol.append(c)
    tris = np.vstack(alltris)
    cols = np.vstack(allcol)
    ax.add_collection3d(Poly3DCollection(tris, facecolors=cols,
                                         edgecolors=(0, 0, 0, 0.15),
                                         linewidths=0.25))
    ax.set_xlim(-110, 40); ax.set_ylim(-60, 60)
    ax.set_zlim(-145, 70)
    ax.set_box_aspect((150, 120, 215))
    ax.view_init(elev=14, azim=-70)
    ax.set_xticks([]); ax.set_yticks([]); ax.set_zticks([])
    ax.set_axis_off()


fig = plt.figure(figsize=(15, 9))

ax1 = fig.add_subplot(1, 2, 1, projection="3d")
draw(ax1, explode=True)
ax1.set_title("РАЗНЕСЁННЫЙ ВИД — что во что вставляется", fontsize=13)
# подписи в разнесённом виде
lbl = {
    "ухо оправы\n(печать)": (-55, 0, 24),
    "болт M5×20": (-95, 0, 24),
    "СКОБА-НОЖКА\n(печать)": (10, 0, 22),
    "верхний барашек M8": (8, 0, 70),
    "шпилька M8\n(металл)": (30, 0, -78),
    "нижний барашек M8\n(высота)": (32, 0, -92),
    "дно коробки\n(печать)": (-60, 0, -128),
    "гайка+шайба\nснизу": (32, 0, -150),
}
for name, mesh, col, off in PARTS:
    if name in lbl:
        x, y, z = lbl[name]
        ax1.text(x, y, z, name, fontsize=9.5, color="#222", ha="center")

ax2 = fig.add_subplot(1, 2, 2, projection="3d")
draw(ax2, explode=False)
ax2.set_title("СОБРАНО", fontsize=13)

fig.suptitle("Как соединяется скоба-ножка (1 из 3 точек крепления оправы)",
             fontsize=14)
fig.tight_layout()
fig.savefig(OUT, dpi=115, bbox_inches="tight")
print(f"saved -> {OUT}")
