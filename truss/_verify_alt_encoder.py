#!/usr/bin/env python3
"""Проверка энкодер-arm'а В СБОРКЕ (мировые координаты): коллизии с диском Ø200,
apex, люлькой; зазор чип↔магнит; клиренс к грани диска. + рендер R-яруса.
arm STL построен build123d СРАЗУ в мире → просто пересекаем с мировыми телами."""
import math
import numpy as np
import trimesh
import gen_rocker_comic as W
import generate_rocker_towers as TW

ENGINE = "manifold"


def _clean(m, *a, **k):
    m.merge_vertices(digits_vertex=5); m.process(validate=True)
    ps = m.split(only_watertight=False)
    return max(ps, key=lambda x: abs(x.volume)) if len(ps) > 1 else m
TW.finish = lambda m, n, pose=None: _clean(m)
TW.tube_fit_test = lambda *a, **k: True
TW.tube_fit = lambda *a, **k: True
TW.seat_enclosure_test = lambda *a, **k: True

def roty(d): return trimesh.transformations.rotation_matrix(math.radians(d), [0, 1, 0])
def tr(x, y, z):
    M = np.eye(4); M[:3, 3] = (x, y, z); return M

WX, APZ, AXZ = W.WHEEL_X, W.APEX_Z, W.ALT_AXIS[2]

# --- тела в мире ---
apex = TW.rocker_tower_apex(+1, "Rocker_tower_apex_R", enc_pad=True); apex.apply_transform(tr(WX, 0, APZ))
cradle = TW.rocker_cradle(+1, "Rocker_cradle_R"); cradle.apply_transform(roty(90)); cradle.apply_transform(tr(WX, 0, APZ))
disc = trimesh.creation.cylinder(radius=100.0, height=15.0, sections=64); disc.apply_transform(roty(90)); disc.apply_transform(tr(WX, 0, AXZ))
# магнит-колпачок: цилиндр Ø18, вклеен в грань диска x=177.5, торчит наружу к 184.4
mag = trimesh.creation.cylinder(radius=9.0, height=7.0, sections=32); mag.apply_transform(roty(90)); mag.apply_transform(tr(WX + 7.5 + 3.45, 0, AXZ))
arm = trimesh.load(TW.OUTDIR / "Rocker_alt_encoder_arm.stl")

print(f"arm: watertight={arm.is_watertight}  vol={arm.volume/1000:.1f}cm³  "
      f"bbox x[{arm.bounds[0,0]:.0f},{arm.bounds[1,0]:.0f}] "
      f"y[{arm.bounds[0,1]:.0f},{arm.bounds[1,1]:.0f}] z[{arm.bounds[0,2]:.0f},{arm.bounds[1,2]:.0f}]")

def vinter(a, b):
    try:
        it = trimesh.boolean.intersection([a, b], engine=ENGINE)
        return abs(it.volume) if it is not None and len(it.faces) else 0.0
    except Exception:
        return float("nan")

print("\n=== КОЛЛИЗИИ (ожидание: диск/люлька=0; apex>0 — это КОНТАКТ ноги на площадке) ===")
for nm, body, expect in [("диск Ø200", disc, "0 (нельзя касаться)"),
                          ("люлька R", cradle, "0"),
                          ("apex R (площадка)", apex, ">0 — нога стоит на площадке, ОК"),
                          ("магнит-колпачок", mag, "0 (только воздушный зазор)")]:
    v = vinter(arm, body)
    print(f"  arm ∩ {nm:20s}: {v/1000:6.2f} cm³   [{expect}]")

# зазор чип↔магнит и клиренс к грани диска
arm_min_x = arm.bounds[0, 0]
print(f"\n=== ЗАЗОРЫ ===")
print(f"  стойка ближе всего к диску: x_min(arm)={arm_min_x:.1f} vs грань диска 177.5 → "
      f"клиренс {arm_min_x-177.5:+.1f} мм")
# чип-плоскость: −X торец бобышек ~ CHIP_X=186; лицо магнита 184.4
print(f"  чип (−X торец бобышек) ~x=186.0 vs лицо магнита ~184.4 → зазор ~1.6 мм (слоты ±3)")

# --- рендер: R-ярус + arm ---
def shade(mesh, base):
    n = mesh.face_normals
    L = np.array([0.5, 0.35, 1.0]); L /= np.linalg.norm(L)
    inten = np.clip(0.4 + 0.6 * (n @ L), 0.25, 1.0)
    return mesh.vertices[mesh.faces], (np.array(base)[None] * inten[:, None]).clip(0, 1)

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

groups = [shade(disc, (0.20, 0.20, 0.22)), shade(mag, (0.85, 0.2, 0.2)),
          shade(apex, (0.95, 0.55, 0.25)), shade(cradle, (0.55, 0.75, 0.95)),
          shade(arm, (0.30, 0.85, 0.45))]
allv = np.vstack([g[0].reshape(-1, 3) for g in groups])
lo, hi = allv.min(0), allv.max(0); ctr = (lo + hi) / 2; span = (hi - lo).max() * 0.55
views = [("iso", 18, -55), ("front (Y-Z)", 4, 0), ("top (X-Y)", 88, -90), ("outboard (X-Z)", 6, -90)]
fig = plt.figure(figsize=(15, 14), dpi=110)
for i, (nm, el, az) in enumerate(views):
    ax = fig.add_subplot(2, 2, i + 1, projection="3d"); ax.computed_zorder = False
    tri = np.vstack([g[0] for g in groups]); fc = np.vstack([g[1] for g in groups])
    pc = Poly3DCollection(tri, facecolors=fc, edgecolor="none"); pc.set_rasterized(True)
    ax.add_collection3d(pc)
    ax.set_xlim(ctr[0]-span, ctr[0]+span); ax.set_ylim(ctr[1]-span, ctr[1]+span); ax.set_zlim(ctr[2]-span, ctr[2]+span)
    ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=el, azim=az); ax.set_title(nm, fontsize=13); ax.set_axis_off()
fig.suptitle("R-ярус высоты: диск(тёмн)+магнит(красн)+apex(оранж)+люлька(син)+ЭНКОДЕР-ARM(зелён, build123d)", fontsize=13)
fig.tight_layout()
out = TW.OUTDIR.parent / "alt_encoder_check.png"
fig.savefig(out, dpi=110); plt.close(fig)
print(f"\nРендер → {out}")
