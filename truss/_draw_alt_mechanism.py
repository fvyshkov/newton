#!/usr/bin/env python3
"""Пояснительная схема высотного узла: колесо Ø200 в люльке, V-опора на 2 ролика,
−Y ролик = ведущий (NEMA17→ремень GT2 3:1), энкодер на оси (магнит центра колеса).
Слева — 3D iso (реальные меши в мире), справа — схема-разрез (вид спереди Y-Z)
с подписями кинематики. → print_queue/verkhniy_yarus/_MECHANISM.png"""
import math
import numpy as np
import trimesh
import gen_rocker_comic as W
import generate_rocker_towers as TW

def _clean(m, *a, **k):
    m.merge_vertices(digits_vertex=5); m.process(validate=True)
    ps = m.split(only_watertight=False)
    return max(ps, key=lambda x: abs(x.volume)) if len(ps) > 1 else m
TW.finish = lambda m, n, pose=None: _clean(m)
TW.tube_fit_test = TW.tube_fit = TW.seat_enclosure_test = lambda *a, **k: True

def roty(d): return trimesh.transformations.rotation_matrix(math.radians(d), [0, 1, 0])
def tr(x, y, z):
    M = np.eye(4); M[:3, 3] = (x, y, z); return M

WX, APZ, AXZ = W.WHEEL_X, W.APEX_Z, W.ALT_AXIS[2]     # 170, 460, 590
ROLL_Y, ROLL_DZ = TW.ROLL_Y, TW.ROLL_DZ               # 67.4, 96.25
ROLL_Z = AXZ - ROLL_DZ                                # 493.75  z центров роликов
ROLL_XW = WX + (TW.ROLL_DZ - (AXZ - APZ)) + 5         # мир x ролика ≈175 (=170+z_l=5)
MOT_Z = ROLL_Z - TW.BELT_CD                           # 435.15  z оси мотора (CD 58.6 «вниз»)

# ---------- 3D меши в мире ----------
apex = TW.rocker_tower_apex(+1, "R", enc_pad=True); apex.apply_transform(tr(WX, 0, APZ))
cradle = TW.rocker_cradle(+1, "R"); cradle.apply_transform(roty(90)); cradle.apply_transform(tr(WX, 0, APZ))
drive = TW.rocker_alt_drive("d"); drive.apply_transform(roty(90)); drive.apply_transform(tr(WX, 0, APZ))
disc = trimesh.creation.cylinder(radius=100, height=15, sections=64); disc.apply_transform(roty(90)); disc.apply_transform(tr(WX, 0, AXZ))
mag = trimesh.creation.cylinder(radius=9, height=7, sections=24); mag.apply_transform(roty(90)); mag.apply_transform(tr(WX + 11, 0, AXZ))
arm = trimesh.load(TW.OUTDIR / "Rocker_alt_encoder_arm.stl")

def roller(y):
    m = trimesh.creation.cylinder(radius=17.5, height=16, sections=32); m.apply_transform(roty(90)); m.apply_transform(tr(ROLL_XW, y, ROLL_Z)); return m
rollA, rollB = roller(-ROLL_Y), roller(+ROLL_Y)       # −Y ведущий, +Y свободный
# NEMA17 корпус (ось X), шкивы, ремень — у −Y
nema = trimesh.creation.box(extents=(48, 42, 42)); nema.apply_transform(tr(ROLL_XW + 40, -ROLL_Y, MOT_Z))
pul_mot = trimesh.creation.cylinder(radius=8, height=6, sections=24); pul_mot.apply_transform(roty(90)); pul_mot.apply_transform(tr(ROLL_XW + 13, -ROLL_Y, MOT_Z))
pul_rol = trimesh.creation.cylinder(radius=20, height=6, sections=24); pul_rol.apply_transform(roty(90)); pul_rol.apply_transform(tr(ROLL_XW + 13, -ROLL_Y, ROLL_Z))

def shade(mesh, base):
    n = mesh.face_normals; L = np.array([0.5, 0.35, 1.0]); L /= np.linalg.norm(L)
    it = np.clip(0.4 + 0.6 * (n @ L), 0.25, 1.0)
    return mesh.vertices[mesh.faces], (np.array(base)[None] * it[:, None]).clip(0, 1)

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, FancyArrowPatch, Wedge
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

CLR = {"колесо Ø200 (крутится с трубой = ВЫСОТА)": (disc, (0.2, 0.2, 0.22)),
       "магнит в центре колеса": (mag, (0.85, 0.2, 0.2)),
       "вышка apex (НЕПОДВИЖНА)": (apex, (0.95, 0.55, 0.25)),
       "люлька-седло (НЕПОДВИЖНА)": (cradle, (0.55, 0.75, 0.95)),
       "кронштейн мотора alt_drive": (drive, (0.75, 0.6, 0.9)),
       "энкодер-arm + плата AS5048A": (arm, (0.3, 0.85, 0.45)),
       "ролик −Y = ВЕДУЩИЙ (фрикцион)": (rollA, (0.95, 0.75, 0.1)),
       "ролик +Y = опорный": (rollB, (0.6, 0.6, 0.62)),
       "NEMA17 + шкивы GT2 + ремень": (nema, (0.15, 0.15, 0.15))}

fig = plt.figure(figsize=(19, 10), dpi=115)

# ============ ЛЕВО: 3D iso ============
ax = fig.add_subplot(1, 2, 1, projection="3d"); ax.computed_zorder = False
groups = [shade(m, c) for (m, c) in CLR.values()]
for extra, c in [(pul_mot, (0.1, 0.1, 0.1)), (pul_rol, (0.1, 0.1, 0.1))]:
    groups.append(shade(extra, c))
tri = np.vstack([g[0] for g in groups]); fc = np.vstack([g[1] for g in groups])
pc = Poly3DCollection(tri, facecolors=fc, edgecolor="none"); pc.set_rasterized(True); ax.add_collection3d(pc)
allv = np.vstack([g[0].reshape(-1, 3) for g in groups]); lo, hi = allv.min(0), allv.max(0)
ctr = (lo + hi) / 2; span = (hi - lo).max() * 0.55
ax.set_xlim(ctr[0]-span, ctr[0]+span); ax.set_ylim(ctr[1]-span, ctr[1]+span); ax.set_zlim(ctr[2]-span, ctr[2]+span)
ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=16, azim=-58); ax.set_axis_off()
ax.set_title("3D: как всё стоит вместе (R-сторона)", fontsize=14)
handles = [plt.Line2D([0], [0], marker='s', ls='', ms=11, mfc=c, mec='k',
           label=name) for name, (m, c) in CLR.items()]
ax.legend(handles=handles, loc='upper left', bbox_to_anchor=(-0.05, 0.98), fontsize=9.5, framealpha=0.9)

# ============ ПРАВО: схема-разрез (вид спереди Y-Z) ============
ax2 = fig.add_subplot(1, 2, 2); ax2.set_aspect("equal"); ax2.axis("off")
ax2.set_title("Схема-разрез (вид спереди, вдоль оси высоты)", fontsize=14)
# колесо
ax2.add_patch(Circle((0, AXZ), 100, fc=(0.2, 0.2, 0.22), ec="k", lw=1.5, zorder=1))
ax2.add_patch(Wedge((0, AXZ), 100, 60, 120, width=3, fc=(0.4, 0.4, 0.42), zorder=2))
# ролики
for y, col, lab in [(-ROLL_Y, (0.95, 0.75, 0.1), "ВЕДУЩИЙ"), (ROLL_Y, (0.6, 0.6, 0.62), "опорный")]:
    ax2.add_patch(Circle((y, ROLL_Z), 17.5, fc=col, ec="k", lw=1.5, zorder=3))
    ax2.text(y, ROLL_Z, lab, ha="center", va="center", fontsize=7, weight="bold")
# точки контакта
for y in (-ROLL_Y, ROLL_Y):
    cx = y * (100 / 117.5); cz = AXZ - (AXZ - ROLL_Z) * (100 / 117.5)
    ax2.plot([cx], [cz], "r^", ms=8, zorder=5)
# мотор + шкивы + ремень (у −Y)
ax2.add_patch(Rectangle((-ROLL_Y - 21, MOT_Z - 21), 42, 42, fc=(0.15, 0.15, 0.15), ec="k", zorder=3))
ax2.add_patch(Circle((-ROLL_Y, MOT_Z), 8, fc="0.3", ec="k", zorder=4))     # шкив 20T
ax2.add_patch(Circle((-ROLL_Y, ROLL_Z), 20, fc="none", ec="0.3", lw=6, zorder=2))  # шкив 60T
ax2.plot([-ROLL_Y - 8, -ROLL_Y - 20], [MOT_Z, ROLL_Z], "-", color="0.3", lw=2, zorder=2)
ax2.plot([-ROLL_Y + 8, -ROLL_Y + 20], [MOT_Z, ROLL_Z], "-", color="0.3", lw=2, zorder=2)
ax2.text(-ROLL_Y, MOT_Z - 30, "NEMA17", ha="center", fontsize=9, weight="bold")
ax2.text(-ROLL_Y - 33, (MOT_Z + ROLL_Z) / 2, "ремень\nGT2 3:1", ha="center", fontsize=8)
# магнит + чип (на оси, вынесены по X — показать пометкой)
ax2.add_patch(Circle((0, AXZ), 5, fc=(0.85, 0.2, 0.2), ec="k", zorder=6))
ax2.plot([0], [AXZ], "g+", ms=16, mew=3, zorder=7)

# подписи-выноски
def note(x, y, tx, ty, txt, **kw):
    ax2.annotate(txt, xy=(x, y), xytext=(tx, ty), fontsize=9.5,
                 arrowprops=dict(arrowstyle="->", lw=1.3), ha=kw.get("ha", "left"),
                 va="center", bbox=dict(boxstyle="round", fc="#fffbe6", ec="0.6"))
note(0, AXZ + 100, -180, AXZ + 120, "КОЛЕСО Ø200 прикручено к трубе.\nКрутится ВМЕСТЕ с трубой = ось ВЫСОТЫ")
note(0, AXZ, 120, AXZ + 95, "МАГНИТ в центре колеса (красн.)\n+ ЧИП AS5048A (зелён.) на арме:\nчип неподвижен, читает угол магнита")
note(-ROLL_Y, ROLL_Z, -230, ROLL_Z + 20, "−Y ролик — ВЕДУЩИЙ:\nмотор через ремень крутит его,\nтрение по ободу катит колесо")
note(ROLL_Y, ROLL_Z, 150, ROLL_Z - 30, "2 ролика = V-опора:\nколесо просто ЛЕЖИТ на них\n(люлька их держит, не даёт съехать)")
note(-ROLL_Y, MOT_Z, 60, MOT_Z - 20, "МОТОР NEMA17 на кронштейне\nalt_drive (лапится на люльку)")
ax2.text(0, 330, "Неподвижно (на раме): люлька + вышка + мотор + энкодер.\n"
                 "Крутится: только колесо (с трубой). Мотор ↔ энкодер замыкают петлю (OnStepX).",
         ha="center", fontsize=10, bbox=dict(boxstyle="round", fc="#e8f4ff", ec="0.5"))
ax2.set_xlim(-260, 210); ax2.set_ylim(310, 720)

fig.tight_layout()
out = TW.OUTDIR / "../print_queue/verkhniy_yarus/_MECHANISM.png"
fig.savefig(out, dpi=115, bbox_inches="tight"); plt.close(fig)
print("→", out.resolve())
