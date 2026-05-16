#!/usr/bin/env python3
"""
Printed mirror cell generator for 8" Newtonian build.

Two printable parts:

  Mirror_cell_front.stl   Ø215mm round plate (mirror rests on this) with
                          3 small vertical retention уголки on top,
                          positioned just outside the mirror edge to
                          stop it from sliding sideways.

  Mirror_cell_back.stl    Y-shaped Ø250mm plate. Three ears reach the
                          tube ID; each ear has a radial Ø5.5mm hole
                          in its outer edge, so an M5×12 bolt from
                          outside the tube goes through the cardboard
                          wall straight into the ear. No tabs, no
                          metal angle brackets.

All 6 collimation holes are CLEARANCE for M5 (Ø6mm) and match between
the two plates so the bolts pass straight through. No printed threads —
push/pull assembly uses bolts + nuts exactly like the plywood version.

Radii follow the classic Stellafane proportions:
  Pull (OUTER) circle: diameter = mirror_D − 1″ → 8″ mirror → r ≈ 89mm
  Push (INNER) circle: diameter = mirror_D − 2½″ → 8″ mirror → r ≈ 70mm
Push and pull are 30° apart angularly, on different radii.

Built via boolean CSG (trimesh + manifold3d).

Print orientation: both parts flat on bed.
  Front: plate-side down on bed, retainer walls face up (no overhang).
  Back:  flat, either side up.
Stiffness: walls 8+, infill 30-40% gyroid. PETG-HF or ASA, NOT PLA.
"""
import math
from pathlib import Path

import trimesh

# --- Common parameters ---
TUBE_ID = 250.0
TUBE_R = TUBE_ID / 2          # 125mm
MIRROR_D = 203.0
MIRROR_R = MIRROR_D / 2       # 101.5mm
PLATE_T = 8.0                 # plate thickness

# --- Bolt geometry (Stellafane proportions) ---
# Pull bolt circle diameter = mirror_D − 1″  → r = (203 − 25.4)/2 ≈ 88.8mm
# Push bolt circle diameter = mirror_D − 2½″ → r = (203 − 63.5)/2 ≈ 69.75mm
# Push goes through INNER ring, pull through OUTER ring.
PUSH_R = 70.0
PULL_R = 89.0

# Angular layout: 6 bolts evenly spaced every 60° around the plate.
# Push and pull alternate: push at 0°/120°/240°, pull at 60°/180°/300°.
# (Different from Stellafane's 30°/30°/60° pattern — chose uniform 60°
#  spacing for cleaner geometry and a symmetric Y-plate.)
PUSH_ANGLES = [0, 120, 240]
PULL_ANGLES = [60, 180, 300]

BOLT_HOLE_R = 3.0             # Ø6mm clearance for M5
VENT_R = 15.0                 # Ø30 central vent

# --- Front plate ---
FRONT_R = 215.0 / 2

# Mirror retention уголки on front plate.
# Placed midway between adjacent push/pull bolts (30°/150°/270°), where
# they don't clash with any bolt hole.
RETAINER_ANGLES = [30, 150, 270]
RETAINER_INNER_R = MIRROR_R + 3.0 # 3mm radial gap to mirror edge (≈ Stellafane 1/8″)
RETAINER_T = 3.0                  # radial wall thickness
RETAINER_W = 20.0                 # tangential width
RETAINER_H = 8.0                  # height above plate top surface

# --- Back plate Y-shape ---
# Each push+pull pair (e.g. push at 0°, pull at 60°) has its midpoint at 30°.
# Ears centered on these midpoints (30°/150°/270°) — each ear covers one
# bolt pair. Scallops carved in the empty regions between pairs (90°/210°/330°).
EAR_ANGLES = [30, 150, 270]
SCALLOP_ANGLES = [90, 210, 330]
SCALLOP_D = 195.0
SCALLOP_R = 110.0                 # leaves ~11mm clearance around the pull holes

# Radial mounting holes through ear edges (M5×12 from outside the tube wall).
MOUNT_HOLE_R = 2.75               # Ø5.5 clearance for M5 bolt body

SEG = 96
SEG_DISK = 256

OUT_DIR = Path(__file__).parent
OUT_FRONT = OUT_DIR / "Mirror_cell_front.stl"
OUT_BACK = OUT_DIR / "Mirror_cell_back.stl"


def disk(radius, thickness, segments=SEG_DISK):
    return trimesh.creation.cylinder(radius=radius, height=thickness, sections=segments)


def hole_cyl(radius, segments=64):
    return trimesh.creation.cylinder(radius=radius, height=PLATE_T * 4, sections=segments)


def xy(angle_deg, r):
    a = math.radians(angle_deg)
    return r * math.cos(a), r * math.sin(a)


def punch(body, radius, x, y):
    h = hole_cyl(radius)
    h.apply_translation([x, y, 0])
    return body.difference(h)


def make_retainer(angle_deg):
    """Small vertical wall on the front plate to keep the mirror from
    sliding sideways. Outer face clipped to plate edge so it doesn't
    overhang."""
    a = math.radians(angle_deg)
    wall = trimesh.creation.box(extents=(RETAINER_T, RETAINER_W, RETAINER_H))
    r_center = RETAINER_INNER_R + RETAINER_T / 2
    wall.apply_translation([r_center, 0, PLATE_T / 2 + RETAINER_H / 2])
    # Clip outer face / corners to plate edge.
    plate_clip = trimesh.creation.cylinder(
        radius=FRONT_R, height=RETAINER_H + 4, sections=SEG_DISK
    )
    plate_clip.apply_translation([0, 0, PLATE_T / 2 + RETAINER_H / 2])
    wall = wall.intersection(plate_clip)
    # Rotate to ear angle.
    rot_z = trimesh.transformations.rotation_matrix(a, [0, 0, 1])
    wall.apply_transform(rot_z)
    return wall


def make_front():
    body = disk(FRONT_R, PLATE_T)
    body = punch(body, VENT_R, 0, 0)
    for ang in PUSH_ANGLES:
        x, y = xy(ang, PUSH_R)
        body = punch(body, BOLT_HOLE_R, x, y)
    for ang in PULL_ANGLES:
        x, y = xy(ang, PULL_R)
        body = punch(body, BOLT_HOLE_R, x, y)
    for ang in RETAINER_ANGLES:
        body = body.union(make_retainer(ang))
    return body


def make_back():
    body = disk(TUBE_R, PLATE_T)

    # Carve scallops in the empty angular regions between bolt pairs.
    for ang in SCALLOP_ANGLES:
        x, y = xy(ang, SCALLOP_D)
        scallop = trimesh.creation.cylinder(
            radius=SCALLOP_R, height=PLATE_T * 4, sections=SEG
        )
        scallop.apply_translation([x, y, 0])
        body = body.difference(scallop)

    body = punch(body, VENT_R, 0, 0)

    # Same 6 collimation holes as front plate — bolts go through both.
    for ang in PUSH_ANGLES:
        x, y = xy(ang, PUSH_R)
        body = punch(body, BOLT_HOLE_R, x, y)
    for ang in PULL_ANGLES:
        x, y = xy(ang, PULL_R)
        body = punch(body, BOLT_HOLE_R, x, y)

    # Radial Ø5.5 mounting holes through each ear's outer edge,
    # centered on plate mid-thickness (Z=0).
    for ang in EAR_ANGLES:
        a = math.radians(ang)
        bolt = trimesh.creation.cylinder(
            radius=MOUNT_HOLE_R, height=40, sections=64
        )
        # axis Z → axis X (radial outward at angle 0)
        rot_y = trimesh.transformations.rotation_matrix(math.radians(90), [0, 1, 0])
        bolt.apply_transform(rot_y)
        # Center the cylinder so it spans well past the ear edge in both directions.
        bolt.apply_translation([TUBE_R - 10, 0, 0])
        rot_z = trimesh.transformations.rotation_matrix(a, [0, 0, 1])
        bolt.apply_transform(rot_z)
        body = body.difference(bolt)

    return body


def main():
    print("Generating front plate ...")
    front = make_front()
    front.export(OUT_FRONT)
    e = front.extents
    print(f"  -> {OUT_FRONT.name}  {len(front.faces)} faces, "
          f"{e[0]:.1f}x{e[1]:.1f}x{e[2]:.1f}mm")

    print("Generating back plate ...")
    back = make_back()
    back.export(OUT_BACK)
    e = back.extents
    print(f"  -> {OUT_BACK.name}  {len(back.faces)} faces, "
          f"{e[0]:.1f}x{e[1]:.1f}x{e[2]:.1f}mm")

    print()
    print(f"  push circle: r={PUSH_R:.1f}  Ø{2*PUSH_R:.1f}  "
          f"(Stellafane: (mirror_D − 2.5″)/2 = {(MIRROR_D - 63.5)/2:.2f}mm)")
    print(f"  pull circle: r={PULL_R:.1f}  Ø{2*PULL_R:.1f}  "
          f"(Stellafane: (mirror_D − 1″)/2  = {(MIRROR_D - 25.4)/2:.2f}mm)")
    print()
    print("  Material : PETG-HF or ASA (NOT PLA)")
    print("  Layer    : 0.2mm, walls 8+, infill 30-40% gyroid")
    print("  Bolts    : M5x50 push, M5x20 pull, M5x12 mounting — all clearance,")
    print("             use M5 nuts on the far side.")


if __name__ == "__main__":
    main()
