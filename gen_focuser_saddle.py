#!/usr/bin/env python3
"""
Focuser saddle generator for 8" Newtonian build.

Sits between flat Focuser outer bottom plate (101×90mm) and curved
sonotube outer surface (OD 258mm).

Built via boolean CSG (trimesh + manifold3d) for guaranteed manifold mesh:
   block  −  carve_cylinder  −  light_hole  −  4 × bolt_holes

Outputs binary STL: stl/Focuser saddle.stl
"""
import math
from pathlib import Path

import numpy as np
import trimesh

# --- Parameters ---
L = 101.0           # X span (along tube axis) — matches focuser base
W = 90.0            # Y span (wraps around tube) — matches focuser base
H_MAX = 11.0        # max saddle thickness (block height before carving curve)
R_TUBE = 129.0      # sonotube OD radius (258mm / 2)
T_MIN = 2.5         # minimum saddle thickness at Y=0 (centerline)
HOLE_LIGHT_R = 25.0 # central light path hole radius (Ø50)
HOLE_BOLT_R = 3.5   # M5 clearance hole radius (Ø7)
BOLT_X = 43.0
BOLT_Y = 40.0
SEG = 128           # tessellation for the small (hole) cylinders (Ø50 and Ø7)
SEG_TUBE = 1024     # tessellation for the large tube cylinder (R=129).
                    # Hole edges on the curved bottom inherit these facets,
                    # so we go aggressive: 1024 segments → 0.8mm chord step,
                    # invisible at 0.2mm print resolution.

OUT = Path(__file__).parent / "stl" / "Focuser saddle.stl"


def cylinder(radius, height, segments, transform=None):
    """Wrapper around trimesh.creation.cylinder."""
    cyl = trimesh.creation.cylinder(radius=radius, height=height, sections=segments)
    if transform is not None:
        cyl.apply_transform(transform)
    return cyl


def translation(x, y, z):
    M = np.eye(4)
    M[:3, 3] = (x, y, z)
    return M


def rotation_x_90():
    """Rotate so cylinder axis lies along X instead of default Z."""
    c, s = 0.0, 1.0  # cos 90, sin 90
    return np.array([
        [1, 0,  0, 0],
        [0, c, -s, 0],
        [0, s,  c, 0],
        [0, 0,  0, 1],
    ])


def generate():
    # Block: 101 × 90 × H_MAX. Top at Z=0, bottom at Z=-H_MAX.
    block = trimesh.creation.box(extents=(L, W, H_MAX))
    block.apply_translation((0, 0, -H_MAX / 2))

    # Carve the tube curve out of the bottom.
    # Cylinder axis along X (tube axis), radius = R_TUBE.
    # Cylinder center placed so its surface touches Z = -T_MIN at Y=0:
    #   cylinder center Z = -T_MIN - R_TUBE
    carve_len = L + 20  # extend past block so boolean is clean
    transform = rotation_x_90() @ translation(0, 0, 0)  # rotate cyl axis to X
    # After rotation, cylinder height (originally along Z) is now along Y due to rotation_x_90 acting from left.
    # We want axis along X. Use trimesh's cylinder oriented via custom transform.
    carve = trimesh.creation.cylinder(radius=R_TUBE, height=carve_len, sections=SEG_TUBE)
    # default cylinder axis is Z. Rotate so axis is X: rotate -90 around Y.
    rot = trimesh.transformations.rotation_matrix(np.radians(90), [0, 1, 0])
    carve.apply_transform(rot)
    # Now place center: X=0, Y=0, Z = -T_MIN - R_TUBE
    carve.apply_translation((0, 0, -T_MIN - R_TUBE))

    # Light hole: cylinder along Z, radius=25, tall enough to pass through block
    light = trimesh.creation.cylinder(radius=HOLE_LIGHT_R, height=H_MAX * 4, sections=SEG)
    light.apply_translation((0, 0, 0))

    # 4 bolt holes
    bolts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            b = trimesh.creation.cylinder(radius=HOLE_BOLT_R, height=H_MAX * 4, sections=SEG // 2)
            b.apply_translation((sx * BOLT_X, sy * BOLT_Y, 0))
            bolts.append(b)

    # Boolean: block − carve − light − bolts
    print("Computing boolean difference (CSG)...")
    result = block.difference(carve)
    result = result.difference(light)
    for b in bolts:
        result = result.difference(b)

    # Verify manifold
    print(f"Watertight: {result.is_watertight}")
    print(f"Volume: {result.volume:.1f} mm³")
    print(f"Triangles: {len(result.faces)}")
    bb = result.bounds
    print(f"Bounds: X {bb[0,0]:.1f}..{bb[1,0]:.1f}  Y {bb[0,1]:.1f}..{bb[1,1]:.1f}  Z {bb[0,2]:.1f}..{bb[1,2]:.1f}")

    OUT.parent.mkdir(exist_ok=True)
    result.export(OUT)
    print(f"\nWrote {OUT}")

    # Stack summary
    t_at_bolt = T_MIN + (R_TUBE - math.sqrt(R_TUBE**2 - BOLT_Y**2))
    t_at_edge = T_MIN + (R_TUBE - math.sqrt(R_TUBE**2 - (W/2)**2))
    print(f"\nThickness profile:")
    print(f"  Y=0 (center): {T_MIN}mm")
    print(f"  Y=±{BOLT_Y} (bolts): {t_at_bolt:.2f}mm")
    print(f"  Y=±{W/2} (edge):  {t_at_edge:.2f}mm")
    print(f"\nMin bolt length: {5 + 4 + t_at_bolt + 4 + 3:.1f}mm → M5×25")


if __name__ == "__main__":
    generate()
