#!/usr/bin/env python3
"""
Focuser saddle generator for 8" Newtonian build.

Sits between flat Focuser outer bottom plate (101×90mm) and curved
sonotube outer surface (OD 258mm). Cylindrical concave bottom, flat top.

Outputs binary STL: stl/Focuser saddle.stl
"""
import struct
import math
from pathlib import Path

# --- Parameters ---
L = 101.0           # X span (along tube axis) — matches focuser base
W = 90.0            # Y span (wraps around tube) — matches focuser base
R_TUBE = 129.0      # sonotube OD radius (258mm / 2)
T_MIN = 2.5         # minimum saddle thickness at Y=0 (centerline)
HOLE_LIGHT_R = 25.0 # central light path hole radius (50mm Ø)
HOLE_BOLT_R = 3.5   # M5 clearance hole radius (Ø7) — 1mm slop per side
BOLT_X = 43.0       # bolt hole positions (matches focuser ear corners)
BOLT_Y = 40.0
SEG_Y = 80          # tessellation along curved Y direction
SEG_HOLE = 32       # tessellation of holes

OUT = Path(__file__).parent / "stl" / "Focuser saddle.stl"


def bottom_z(y):
    """Z of curved bottom surface at given Y. Top is at Z=0."""
    return -T_MIN - (R_TUBE - math.sqrt(R_TUBE * R_TUBE - y * y))


def write_stl(triangles, path):
    """Write list of triangles (each = 3 (x,y,z) tuples) as binary STL."""
    with open(path, "wb") as fp:
        fp.write(b"saddle".ljust(80, b"\0"))
        fp.write(struct.pack("<I", len(triangles)))
        for tri in triangles:
            # compute normal
            (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = tri
            ux, uy, uz = x2 - x1, y2 - y1, z2 - z1
            vx, vy, vz = x3 - x1, y3 - y1, z3 - z1
            nx = uy * vz - uz * vy
            ny = uz * vx - ux * vz
            nz = ux * vy - uy * vx
            n = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            fp.write(struct.pack("<fff", nx / n, ny / n, nz / n))
            for v in tri:
                fp.write(struct.pack("<fff", *v))
            fp.write(b"\0\0")


def in_circle(x, y, cx, cy, r):
    return (x - cx) ** 2 + (y - cy) ** 2 < r * r


def is_hole(x, y):
    """True if (x,y) is inside any drilled hole (skip area)."""
    if in_circle(x, y, 0, 0, HOLE_LIGHT_R):
        return True
    for sx in (-1, 1):
        for sy in (-1, 1):
            if in_circle(x, y, sx * BOLT_X, sy * BOLT_Y, HOLE_BOLT_R):
                return True
    return False


def generate():
    tris = []

    # Build a grid in (x, y), generate top and bottom surfaces with holes carved out.
    # Strategy: rectangular grid with high resolution; punch holes by checking each quad.
    # For each grid cell, if all 4 corners are outside holes → add top + bottom + outer wall.

    NX = 80
    NY = SEG_Y
    xs = [-L / 2 + L * i / NX for i in range(NX + 1)]
    ys = [-W / 2 + W * j / NY for j in range(NY + 1)]

    # Top + bottom faces (rectangle minus holes via "hole" check at quad center)
    for i in range(NX):
        for j in range(NY):
            x0, x1 = xs[i], xs[i + 1]
            y0, y1 = ys[j], ys[j + 1]
            xc, yc = (x0 + x1) / 2, (y0 + y1) / 2
            if is_hole(xc, yc):
                continue
            # Skip if any corner deep inside hole (avoids overlapping mesh near hole edge)
            if any(is_hole(x, y) for x in (x0, x1) for y in (y0, y1)):
                continue
            # Top (Z=0), normal up
            tris.append([(x0, y0, 0), (x1, y0, 0), (x1, y1, 0)])
            tris.append([(x0, y0, 0), (x1, y1, 0), (x0, y1, 0)])
            # Bottom (curved), normal down — wind reverse
            z00, z01 = bottom_z(y0), bottom_z(y1)
            z10, z11 = bottom_z(y0), bottom_z(y1)
            tris.append([(x0, y0, z00), (x1, y1, z11), (x1, y0, z10)])
            tris.append([(x0, y0, z00), (x0, y1, z01), (x1, y1, z11)])

    # Hole walls — cylindrical for each hole
    def add_hole_walls(cx, cy, r, ztop=0.0, zbot_fn=lambda x, y: bottom_z(y)):
        for k in range(SEG_HOLE):
            a0 = 2 * math.pi * k / SEG_HOLE
            a1 = 2 * math.pi * (k + 1) / SEG_HOLE
            x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
            x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
            zb0 = zbot_fn(x0, y0)
            zb1 = zbot_fn(x1, y1)
            # inward-facing wall (normal points toward hole center)
            tris.append([(x0, y0, ztop), (x1, y1, ztop), (x1, y1, zb1)])
            tris.append([(x0, y0, ztop), (x1, y1, zb1), (x0, y0, zb0)])

    add_hole_walls(0, 0, HOLE_LIGHT_R)
    for sx in (-1, 1):
        for sy in (-1, 1):
            add_hole_walls(sx * BOLT_X, sy * BOLT_Y, HOLE_BOLT_R)

    # Outer walls (4 sides)
    # +X side (vertical, x = L/2)
    for j in range(NY):
        y0, y1 = ys[j], ys[j + 1]
        z0 = bottom_z(y0)
        z1 = bottom_z(y1)
        x = L / 2
        tris.append([(x, y0, 0), (x, y0, z0), (x, y1, z1)])
        tris.append([(x, y0, 0), (x, y1, z1), (x, y1, 0)])
    # -X side
    for j in range(NY):
        y0, y1 = ys[j], ys[j + 1]
        z0 = bottom_z(y0)
        z1 = bottom_z(y1)
        x = -L / 2
        tris.append([(x, y0, 0), (x, y1, z1), (x, y0, z0)])
        tris.append([(x, y0, 0), (x, y1, 0), (x, y1, z1)])
    # +Y side (curved bottom but flat in X)
    for i in range(NX):
        x0, x1 = xs[i], xs[i + 1]
        y = W / 2
        z = bottom_z(y)
        tris.append([(x0, y, 0), (x1, y, 0), (x1, y, z)])
        tris.append([(x0, y, 0), (x1, y, z), (x0, y, z)])
    # -Y side
    for i in range(NX):
        x0, x1 = xs[i], xs[i + 1]
        y = -W / 2
        z = bottom_z(y)
        tris.append([(x0, y, 0), (x1, y, z), (x1, y, 0)])
        tris.append([(x0, y, 0), (x0, y, z), (x1, y, z)])

    write_stl(tris, OUT)

    # Print summary
    z_edge = bottom_z(W / 2)
    z_bolt = bottom_z(BOLT_Y)
    print(f"Wrote {OUT}")
    print(f"Triangles: {len(tris)}")
    print(f"Footprint: {L}×{W}mm")
    print(f"Thickness at Y=0 (center): {T_MIN}mm")
    print(f"Thickness at Y=±{BOLT_Y} (bolt holes): {T_MIN + (R_TUBE - math.sqrt(R_TUBE**2 - BOLT_Y**2)):.2f}mm")
    print(f"Thickness at Y=±{W/2} (edge): {T_MIN + (R_TUBE - math.sqrt(R_TUBE**2 - (W/2)**2)):.2f}mm")
    print(f"Required bolt length (ear 5 + tube 4 + saddle_at_bolt + nut 4 + ~3mm engagement):")
    bolt_min = 5 + 4 + (T_MIN + (R_TUBE - math.sqrt(R_TUBE**2 - BOLT_Y**2))) + 4 + 3
    print(f"  ≥ {bolt_min:.1f}mm — recommend M5×25")


if __name__ == "__main__":
    generate()
