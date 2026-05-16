#!/usr/bin/env python3
"""
Printed mirror cell generator for 8" Newtonian build.

Replaces the plywood Stellafane-style cell with two printable parts:

  Mirror_cell_front.stl   Ø215mm round plate (mirror rests on this)
  Mirror_cell_back.stl    Y-shaped Ø250mm plate with 3 integrated wall tabs
                          (the tabs replace the metal angle brackets — they
                           clip the inside of the tube wall, M5 bolts pass
                           radially from outside through tube into tab)

All holes are CLEARANCE for M5 (Ø6mm), no printed threads — assembly uses
bolts + nuts, exactly like the plywood version.

Built via boolean CSG (trimesh + manifold3d) for guaranteed manifold mesh.

Print orientation: both parts flat on bed.
  Front: any side up.
  Back: tabs face up. No supports needed (tabs are vertical walls sitting
        directly above plate edge — no overhang).

Stiffness: plate is intentionally thin (8mm). Add ribs in slicer via
  walls 8+ and infill 30-40% gyroid. PETG-HF or ASA recommended,
  NOT PLA (creeps under load, softens in summer sun).
"""
import math
from pathlib import Path

import trimesh

# --- Common parameters ---
TUBE_ID = 250.0          # mm — sonotube inner diameter
TUBE_R = TUBE_ID / 2     # 125mm
PLATE_T = 8.0            # plate thickness

# Bolt circles — classic Stellafane "hexagonal" layout:
# 3 push bolts at the EAR centers (0°/120°/240°), outer radius r=95.
# 3 pull bolts BETWEEN ears (60°/180°/300°), inner radius r=80.
# Push and pull are angularly offset by 60° and live on different radii.
# (See images/stellafane_cell_plan1.jpg, plan2.jpg — labels show 30°/60°.)
PUSH_R = 95.0
PULL_R = 80.0
PUSH_ANGLES = [0, 120, 240]
PULL_ANGLES = [60, 180, 300]

BOLT_HOLE_R = 3.0        # Ø6mm clearance for M5 (loose for tilt freedom)
VENT_R = 15.0            # Ø30mm central vent

# Front plate
FRONT_R = 215.0 / 2

# Back plate Y-shape — scallops carved between ears.
# Scallop inner reach = D - R = 90mm, so material survives between ears
# from r=0 to r=90. This keeps ~10mm of meat around each pull hole
# (which sits at r=80 right inside the scallop zone).
SCALLOP_D = 195.0
SCALLOP_R = 105.0
SCALLOP_ANGLES = [60, 180, 300]

# Integrated tube-wall tabs (replace metal angle brackets)
TAB_W = 35.0             # tangential width
TAB_H = 25.0             # height above plate top
TAB_T = 5.0              # radial thickness
TAB_HOLE_R = 2.75        # M5 clearance
TAB_HOLE_Z = 12.0        # bolt hole, mm above plate top (≈ middle of tab)

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


def make_front():
    body = disk(FRONT_R, PLATE_T)
    body = punch(body, VENT_R, 0, 0)
    for ang in PUSH_ANGLES:
        x, y = xy(ang, PUSH_R)
        body = punch(body, BOLT_HOLE_R, x, y)
    for ang in PULL_ANGLES:
        x, y = xy(ang, PULL_R)
        body = punch(body, BOLT_HOLE_R, x, y)
    return body


def make_tab(angle_deg):
    """Vertical flat tab at the ear tip. Outer face flush with tube ID.
    One radial bolt hole through tab."""
    a = math.radians(angle_deg)

    tab = trimesh.creation.box(extents=(TAB_T, TAB_W, TAB_H))
    r_center = TUBE_R - TAB_T / 2
    tab.apply_translation([r_center, 0, PLATE_T / 2 + TAB_H / 2])

    # Bolt hole: axis along X (radial outward at angle 0).
    bolt = trimesh.creation.cylinder(radius=TAB_HOLE_R, height=TAB_T + 20, sections=64)
    rot_y = trimesh.transformations.rotation_matrix(math.radians(90), [0, 1, 0])
    bolt.apply_transform(rot_y)
    bolt.apply_translation([r_center, 0, PLATE_T / 2 + TAB_HOLE_Z])
    tab = tab.difference(bolt)

    # Rotate complete tab+hole assembly to its ear angle.
    rot_z = trimesh.transformations.rotation_matrix(a, [0, 0, 1])
    tab.apply_transform(rot_z)
    return tab


def make_back():
    body = disk(TUBE_R, PLATE_T)

    # Carve scallops between ears → Y-shape.
    for ang in SCALLOP_ANGLES:
        x, y = xy(ang, SCALLOP_D)
        scallop = trimesh.creation.cylinder(
            radius=SCALLOP_R, height=PLATE_T * 4, sections=SEG
        )
        scallop.apply_translation([x, y, 0])
        body = body.difference(scallop)

    body = punch(body, VENT_R, 0, 0)
    for ang in PUSH_ANGLES:
        x, y = xy(ang, PUSH_R)
        body = punch(body, BOLT_HOLE_R, x, y)
    for ang in PULL_ANGLES:
        x, y = xy(ang, PULL_R)
        body = punch(body, BOLT_HOLE_R, x, y)

    # Integrated wall tabs at each ear tip.
    for ang in PUSH_ANGLES:
        body = body.union(make_tab(ang))

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

    print("\nPrint hints:")
    print("  Material : PETG-HF or ASA (NOT PLA)")
    print("  Layer    : 0.2mm")
    print("  Walls    : 8+")
    print("  Infill   : 30-40% gyroid")
    print("  Supports : none (tabs sit above plate edge - no overhang)")
    print("  Bolts    : M5x50 push, M5x20 pull, M5x12 to tube wall — clearance holes,")
    print("             use M5 nuts on the far side. NO threads in plastic.")


if __name__ == "__main__":
    main()
