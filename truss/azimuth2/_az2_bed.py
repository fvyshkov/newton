#!/usr/bin/env python3
"""Раскладка деталей азимута v2 по столам Bambu H2D (350×320), PETG.
Реальные 2D-контуры из STL; сегменты кольца нестятся «валетом» (дуга в дугу).
Проверяет отсутствие пересечений и выход за печатную зону. → az2_bed_layout.png"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon as MPoly
from pathlib import Path
import trimesh
from shapely.affinity import rotate, translate
from shapely.geometry import box as sbox

BED_X, BED_Y = 350, 320
MARGIN = 4
GAP = 4.0                      # минимальный зазор между деталями, мм

VOL = {"az2_ring_fixed_seg": 116, "az2_ring_rot_seg": 106, "az2_magnet_spider": 24,
       "az2_encoder_column": 29, "az2_motor_pedestal": 56, "az2_pinion_16T_bore5": 8}
COL = {"az2_ring_fixed_seg": "#d98a3d", "az2_ring_rot_seg": "#e0a94a",
       "az2_magnet_spider": "#7fb3d5", "az2_encoder_column": "#82c99a",
       "az2_motor_pedestal": "#c8a2c8", "az2_pinion_16T_bore5": "#f0c040"}

FOOT = {}
for f in sorted(Path("stl").glob("*.stl")):
    m = trimesh.load(f, process=False)
    poly = max(m.projected(normal=[0, 0, 1]).polygons_full, key=lambda g: g.area)
    minx, miny, maxx, maxy = poly.bounds
    FOOT[f.stem] = translate(poly, -(minx + maxx) / 2, -(miny + maxy) / 2)


def place(name, x, y, rot=0.0):
    return translate(rotate(FOOT[name], rot, origin=(0, 0)), x, y)


def nest_stack(name, n=4, base_rot=90.0):
    """n дуг в ОДНОЙ ориентации, каждая со сдвигом по Y до зазора GAP: концав
    верхней сидит на конвексе нижней (найдено брутфорсом, шаг ~61 мм).
    base_rot=90 → хорда дуги (длинная, 317) вдоль X (стол 350)."""
    A = place(name, 0, 0, base_rot)
    pitch = 120.0
    while pitch > 0:                     # свести соседей до касания GAP
        if A.distance(place(name, 0, pitch, base_rot)) < GAP:
            pitch += 1.0
            break
        pitch -= 1.0
    return [(name, 0, i * pitch, base_rot) for i in range(n)]


def bbox_of(placed):
    xs = [place(n, x, y, r).bounds for (n, x, y, r) in placed]
    return (min(b[0] for b in xs), min(b[1] for b in xs),
            max(b[2] for b in xs), max(b[3] for b in xs))


def center_on_bed(placed):
    """Сдвинуть всю раскладку в центр стола."""
    x0, y0, x1, y1 = bbox_of(placed)
    dx = (BED_X - (x1 - x0)) / 2 - x0
    dy = (BED_Y - (y1 - y0)) / 2 - y0
    return [(n, x + dx, y + dy, r) for (n, x, y, r) in placed]


def check(placed):
    zone = sbox(MARGIN, MARGIN, BED_X - MARGIN, BED_Y - MARGIN)
    bad = []
    polys = [(n, place(n, x, y, r)) for (n, x, y, r) in placed]
    for i, (n, p) in enumerate(polys):
        if not zone.contains(p):
            bad.append(f"{n} за зоной")
        for j in range(i + 1, len(polys)):
            if p.intersection(polys[j][1]).area > 1.0:
                bad.append(f"{n}∩{polys[j][0]}")
    return bad


# ================= РАСКЛАДКА =================
def plate_rings(name):
    # 4 дуги стопкой-нестингом, хорда вдоль X
    return center_on_bed(nest_stack(name, 4))


def plate_small():
    # спайдер (лучи по диагоналям) по центру; мелочь — в промежутках по осям ±X/±Y
    return [
        ("az2_magnet_spider", 175, 160, 0.0),
        ("az2_encoder_column", 272, 160, 0.0),       # +X промежуток
        ("az2_motor_pedestal", 80, 160, 0.0),        # −X промежуток
        ("az2_pinion_16T_bore5", 175, 266, 0.0),     # +Y промежуток
    ]


PLATES = [
    ("Стол 1 — неподвижное кольцо ×4", plate_rings("az2_ring_fixed_seg")),
    ("Стол 2 — вращающееся кольцо ×4", plate_rings("az2_ring_rot_seg")),
    ("Стол 3 — центр/привод", plate_small()),
]

fig, axes = plt.subplots(1, 3, figsize=(21, 8), dpi=110)
total_g = 0
for ax, (title, placed) in zip(axes, PLATES):
    bad = check(placed)
    ax.add_patch(Rectangle((0, 0), BED_X, BED_Y, fc="#f4f4f4", ec="k", lw=2))
    ax.add_patch(Rectangle((MARGIN, MARGIN), BED_X - 2*MARGIN, BED_Y - 2*MARGIN,
                           fc="none", ec="0.6", ls="--", lw=1))
    pg = 0
    for (n, x, y, r) in placed:
        poly = place(n, x, y, r)
        xs, ys = poly.exterior.xy
        ax.add_patch(MPoly(list(zip(xs, ys)), closed=True, fc=COL[n], ec="k",
                           lw=1.2, alpha=0.9))
        for interior in poly.interiors:
            ix, iy = interior.xy
            ax.add_patch(MPoly(list(zip(ix, iy)), closed=True, fc="#f4f4f4",
                               ec="0.5", lw=0.6))
        ax.text(x, y, n.replace("az2_", "").replace("_seg", "").replace("_16T_bore5", ""),
                ha="center", va="center", fontsize=7.5, weight="bold")
        pg += VOL[n] * 1.27 * 0.5
    total_g += pg
    status = "✓ ок" if not bad else "⚠ " + "; ".join(bad)
    ax.set_title(f"{title}\n≈{pg:.0f} г PETG   {status}", fontsize=11, weight="bold")
    ax.set_xlim(-12, BED_X + 12); ax.set_ylim(-12, BED_Y + 12)
    ax.set_aspect("equal"); ax.set_xlabel("350 мм"); ax.set_ylabel("320 мм")
    ax.grid(alpha=0.15)
    print(f"{title}: {'OK' if not bad else bad}")

fig.suptitle(f"Азимут v2 — раскладка на Bambu H2D (350×320), PETG · {len(PLATES)} стола · "
             f"всего ≈{total_g:.0f} г", fontsize=13, weight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.93])
out = Path("az2_bed_layout.png")
fig.savefig(out, dpi=110, bbox_inches="tight"); plt.close(fig)
print("→", out.resolve())
