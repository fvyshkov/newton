#!/usr/bin/env python3
"""Собрать файлы для печати на Bambu H2D: по одному файлу на стол с УЖЕ
разложенными (вложенными) деталями. → truss/print_queue/azimuth2/
Экспорт 3mf (объекты сохраняют взаимные позиции) + позиционный STL (бэкап)."""
import numpy as np, shutil
from pathlib import Path
import trimesh
from shapely.affinity import rotate as srot, translate as strans

GAP = 4.0
SRC = Path("stl")
OUT = Path("../print_queue/azimuth2")
OUT.mkdir(parents=True, exist_ok=True)


def load_centered(name):
    m = trimesh.load(SRC / f"{name}.stl", process=False)
    # STL = «суп треугольников» (вершины продублированы на каждый треугольник).
    # Без слияния 3mf наследует дубли → Bambu считает меш дырявым, чинит сам и
    # может выкинуть слои («empty layer», «faulty mesh»). Сливаем до экспорта.
    m.merge_vertices()
    b = m.bounds
    m.apply_translation([-(b[0][0] + b[1][0]) / 2, -(b[0][1] + b[1][1]) / 2, 0])
    return m


def foot(name):
    m = trimesh.load(SRC / f"{name}.stl", process=False)
    p = max(m.projected(normal=[0, 0, 1]).polygons_full, key=lambda g: g.area)
    b = p.bounds
    return strans(p, -(b[0] + b[2]) / 2, -(b[1] + b[3]) / 2)


def pitch_of(name, base_rot=90.0):
    A = srot(foot(name), base_rot, origin=(0, 0))
    pt = 120.0
    while pt > 0:
        if A.distance(strans(srot(foot(name), base_rot, origin=(0, 0)), 0, pt)) < GAP:
            pt += 1.0
            break
        pt -= 1.0
    return pt


def rotZ(deg):
    return trimesh.transformations.rotation_matrix(np.radians(deg), [0, 0, 1])


def build_plate(items):
    """items: [(name, x, y, rotdeg)]. Вернёт (Scene, [meshes]) с центром в (0,0)."""
    meshes = []
    for (name, x, y, rd) in items:
        m = load_centered(name).copy()
        m.apply_transform(rotZ(rd))
        m.apply_translation([x, y, 0])
        meshes.append(m)
    b = trimesh.Scene(meshes).bounds
    cx, cy = (b[0][0] + b[1][0]) / 2, (b[0][1] + b[1][1]) / 2
    for m in meshes:
        m.apply_translation([-cx, -cy, 0])
    return trimesh.Scene(meshes), meshes


def ring_items(name, n=4):
    pt = pitch_of(name)
    return [(name, 0, i * pt, 90.0) for i in range(n)]


def ring_items_list(names):
    pt = max(pitch_of(nm) for nm in names)
    return [(names[i], 0, i * pt, 90.0) for i in range(len(names))]


SMALL = [("az2_magnet_spider", 175, 160, 0.0),
         ("az2_encoder_column", 272, 160, 0.0),
         ("az2_motor_pedestal", 80, 160, 0.0),
         ("az2_pinion_16T_bore5", 175, 266, 0.0)]

SHOES = [("az2_magnet_spider3", 165.7, 194.6, -75.0),  # хаб → (175,160), лучи 45/135/225
         ("az2_motor_pedestal", 80, 160, 0.0),
         ("az2_encoder_column", 272, 160, 0.0),
         ("az2_pinion_16T_bore5", 175, 266, 0.0),
         ("az2_shoe_C150", 145, 48, 0.0),
         ("az2_shoe_A30", 215, 48, 0.0),
         ("az2_shoe_D270", 295, 70, 0.0)]

PLATES = {
    "plate1_ring_fixed_x4": ring_items("az2_ring_fixed_seg"),
    "plate2_venec_rot_x4": ring_items_list(
        ["az2_ring_rot_A_leg30", "az2_ring_rot_B_plain",
         "az2_ring_rot_C_leg150", "az2_ring_rot_D_leg270"]),
    "plate3_center_4parts": SMALL,
    "plate4_bashmaki_center": SHOES,
}

print("Сборка файлов для Bambu H2D →", OUT.resolve())
for pname, items in PLATES.items():
    scene, meshes = build_plate(items)
    scene.export(OUT / f"{pname}.3mf")
    trimesh.util.concatenate(meshes).export(OUT / f"{pname}.stl")
    e = scene.extents
    print(f"  {pname}: {len(meshes)} дет., габарит {e[0]:.0f}×{e[1]:.0f}×{e[2]:.0f} мм "
          f"→ .3mf + .stl")

# отдельные STL и картинка раскладки — в подпапку
(OUT / "stl_отдельно").mkdir(exist_ok=True)
for f in SRC.glob("*.stl"):
    shutil.copy(f, OUT / "stl_отдельно" / f.name)
for img in ("az2_bed_layout.png", "az2_scheme.png"):
    if Path(img).exists():
        shutil.copy(img, OUT / img)
print("  + отдельные STL, az2_bed_layout.png, az2_scheme.png")
