#!/usr/bin/env python3
"""
Wordless assembly comic for the TrussRocker — the azimuth/altitude rocker
mount for the truss-Dobson.

Generates rocker_assembly_comic.pdf — a step-by-step visual guide that shows
how the printed parts, tubes and drives come together. No descriptions — just
numbered panels, exploded views, and arrows.

Same approach as gen_truss_comic.py: matplotlib Agg + Poly3DCollection shaded
meshes, page_step builders, big step numbers, orange arrows, PdfPages output.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from matplotlib.backends.backend_pdf import PdfPages
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

DECIMATE_TARGET = 4000

ROOT = Path(__file__).parent
STL = ROOT / "stl"
ENC_STL = ROOT.parent / "stl" / "encoder"
PNG_DIR = Path(
    "/private/tmp/claude-501/-Users-mac-newton/"
    "d9ecf066-2821-4ed2-b191-d8536c2acbd4/scratchpad/rocker_comic"
)

CLR_BODY = (0.78, 0.78, 0.80)
CLR_NEW = (0.95, 0.55, 0.25)
CLR_HARDWARE = (0.45, 0.45, 0.48)
CLR_TUBE = (0.72, 0.74, 0.78)
CLR_SCOPE = (0.15, 0.15, 0.16)
CLR_WHEEL = (0.30, 0.30, 0.32)
CLR_MOTOR = (0.24, 0.24, 0.26)
CLR_STEEL = (0.62, 0.64, 0.68)
CLR_BELT = (0.10, 0.10, 0.10)
CLR_POLE = (0.93, 0.93, 0.95)
CLR_SPRING = (0.75, 0.75, 0.78)
CLR_E4 = (0.12, 0.12, 0.13)

TOTAL = 13

_cache = {}


def load_stl(path):
    key = str(path)
    if key not in _cache:
        m = trimesh.load(path)
        if len(m.faces) > DECIMATE_TARGET:
            try:
                m = m.simplify_quadric_decimation(face_count=DECIMATE_TARGET)
            except Exception:
                pass
        _cache[key] = m
    return _cache[key].copy()


def mesh_to_polycoll(mesh, base_color):
    tri = mesh.vertices[mesh.faces]
    n = mesh.face_normals
    light = np.array([0.4, 0.3, 1.0])
    light /= np.linalg.norm(light)
    intens = np.clip(0.40 + 0.60 * (n @ light), 0.25, 1.0)
    base = np.array(base_color)
    facecolors = (base[None, :] * intens[:, None]).clip(0, 1)
    return tri, facecolors, mesh.bounds


def translate(x, y, z):
    M = np.eye(4)
    M[:3, 3] = (x, y, z)
    return M


def rotate_x(deg):
    return trimesh.transformations.rotation_matrix(np.radians(deg), [1, 0, 0])


def rotate_y(deg):
    return trimesh.transformations.rotation_matrix(np.radians(deg), [0, 1, 0])


def rotate_z(deg):
    return trimesh.transformations.rotation_matrix(np.radians(deg), [0, 0, 1])


def compose(*mats):
    out = np.eye(4)
    for M in mats:
        out = out @ M
    return out


def load_part(name, base_color=CLR_BODY, transform=None, encoder=False):
    folder = ENC_STL if encoder else STL
    m = load_stl(folder / f"{name}.stl")
    if transform is not None:
        m.apply_transform(transform)
    return mesh_to_polycoll(m, base_color)


def make_cyl(radius, height, transform=None, color=CLR_NEW, sections=32):
    m = trimesh.creation.cylinder(radius=radius, height=height, sections=sections)
    if transform is not None:
        m.apply_transform(transform)
    return mesh_to_polycoll(m, color)


def make_box(extents, transform=None, color=CLR_NEW):
    m = trimesh.creation.box(extents=extents)
    if transform is not None:
        m.apply_transform(transform)
    return mesh_to_polycoll(m, color)


def make_tube(p1, p2, radius=11, color=CLR_TUBE, sections=24):
    m = trimesh.creation.cylinder(radius=radius, segment=[p1, p2], sections=sections)
    return mesh_to_polycoll(m, color)


def make_annulus(r_min, r_max, height, transform=None, color=CLR_STEEL):
    m = trimesh.creation.annulus(r_min=r_min, r_max=r_max, height=height, sections=32)
    if transform is not None:
        m.apply_transform(transform)
    return mesh_to_polycoll(m, color)


def make_trunccone(r_bottom, r_top, height, transform=None, color=CLR_NEW):
    """Truncated cone, base at z=0, top at z=height."""
    m = trimesh.creation.cylinder(radius=1.0, height=height, sections=32)
    v = m.vertices.copy()
    top = v[:, 2] > 0
    v[top, :2] *= r_top
    v[~top, :2] *= r_bottom
    v[:, 2] += height / 2
    m = trimesh.Trimesh(vertices=v, faces=m.faces.copy())
    if transform is not None:
        m.apply_transform(transform)
    return mesh_to_polycoll(m, color)


def make_torus(major_r, minor_r, transform=None, color=CLR_BELT):
    m = trimesh.creation.torus(major_radius=major_r, minor_radius=minor_r,
                               major_sections=32, minor_sections=12)
    if transform is not None:
        m.apply_transform(transform)
    return mesh_to_polycoll(m, color)


def add_payload(ax, payload, alpha=1.0):
    tri, fc, _ = payload
    poly = Poly3DCollection(tri, facecolors=fc, edgecolor="none", linewidth=0, alpha=alpha)
    poly.set_rasterized(True)
    ax.add_collection3d(poly)


def add_combined(ax, payloads):
    """One Poly3DCollection for all opaque parts -> correct global z-sorting
    (separate collections are depth-sorted as whole units and small near
    parts vanish behind large far ones)."""
    tri = np.vstack([p[0] for p in payloads])
    fc = np.vstack([p[1] for p in payloads])
    poly = Poly3DCollection(tri, facecolors=fc, edgecolor="none", linewidth=0)
    poly.set_rasterized(True)
    ax.add_collection3d(poly)


def arrow_3d(ax, start, end, color="#d04020", lw=3):
    ax.quiver(
        start[0], start[1], start[2],
        end[0] - start[0], end[1] - start[1], end[2] - start[2],
        color=color, arrow_length_ratio=0.18, lw=lw,
    )


def setup_axes(ax, center=(0, 0, 0), span=200, elev=18, azim=-55):
    cx, cy, cz = center
    ax.set_xlim(cx - span, cx + span)
    ax.set_ylim(cy - span, cy + span)
    ax.set_zlim(cz - span, cz + span)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()


def step_label(fig, number, total):
    fig.text(0.05, 0.99, f"{number}", fontsize=110, fontweight="bold", color="#222",
             va="top")
    fig.text(0.94, 0.94, f"/ {total}", fontsize=20, color="#bbb", ha="right", va="center")


def finish_page(fig, pdf, page_no):
    fig.savefig(PNG_DIR / f"page_{page_no:02d}.png", dpi=110)
    pdf.savefig(fig, dpi=140)
    plt.close(fig)
    print(f"page {page_no:02d} done")


# ---------- Page builders ----------

def page_step(pdf, n, total, payloads, ghost=None, arrows=None,
              center=None, span=300, elev=18, azim=-55):
    fig = plt.figure(figsize=(11, 14), dpi=140)
    ax = fig.add_subplot(111, projection="3d")
    # draw in add-order: meshes, then ghosts, then arrows on top
    ax.computed_zorder = False
    add_combined(ax, payloads)
    if ghost:
        for p in ghost:
            add_payload(ax, p, alpha=0.35)
    if arrows:
        for s, e in arrows:
            arrow_3d(ax, s, e)
    if center is None:
        all_v = np.vstack([p[0].reshape(-1, 3) for p in payloads])
        center = all_v.mean(axis=0)
    setup_axes(ax, center=center, span=span, elev=elev, azim=azim)
    step_label(fig, n, total)
    finish_page(fig, pdf, n)


def page_inventory(pdf, page_no, items, rows, cols):
    """Inventory page: each unique part shown once with its quantity badge."""
    fig = plt.figure(figsize=(11, 14), dpi=140)
    for i, (payloads, qty) in enumerate(items):
        ax = fig.add_subplot(rows, cols, i + 1, projection="3d")
        add_combined(ax, payloads)
        all_v = np.vstack([p[0].reshape(-1, 3) for p in payloads])
        lo, hi = all_v.min(axis=0), all_v.max(axis=0)
        span = (hi - lo).max() * 0.62
        c = (lo + hi) / 2
        setup_axes(ax, center=c, span=span, elev=22, azim=-50)
        ax.text2D(
            0.92, 0.90, f"×{qty}",
            transform=ax.transAxes,
            fontsize=28, fontweight="bold", color="#d04020",
            ha="right", va="top",
        )
        ax.text2D(
            0.06, 0.90, f"{i + 1}",
            transform=ax.transAxes,
            fontsize=18, fontweight="bold", color="#333",
            ha="left", va="top",
        )
    fig.subplots_adjust(top=0.88, bottom=0.02, left=0.02, right=0.98,
                        hspace=0.05, wspace=0.05)
    step_label(fig, page_no, TOTAL)
    finish_page(fig, pdf, page_no)


# ---------- Measured STL fixes (inspected with trimesh) ----------
# Rocker_ring_segment.stl: native gear-arc center at (-181.199, +2.808),
# tooth tips at R226.0, plate inner edge R200, z=0..10 (plate 0..8).
# Segment spans ±47° about that center. Translate center -> origin.
RING_SEG_FIX = translate(181.199, -2.808, 0)

# Ref_leavitt_wheel.stl: rim arc is a 270° sector, rim circle R100 centered
# EXACTLY at native (0,0) (max radius uniformly 100.0 at every angle), missing
# quadrant at native azimuth -90°..0°. z spans -15..0 -> center with +7.5.
# (The +5.47/-5.47 "rim center" figure matches the centroid offset of the
# 270° sector, not the rim circle — only the z recentering is needed.)
WHEEL_Z_FIX = translate(0, 0, 7.5)

# ---------- World geometry (z=0 floor, mm) ----------
CORNER_ANGLES = (30, 150, 270)
R_CORNER = 210
R_ARM_OUT = 285
R_FOOT = 280
RING_Z = 50            # ring segments occupy z=50..60, track top = 60
FRAME_Z = 75           # tube axis height of the rotating frame
WHEEL_X = 170          # wheel mid-planes at x=±170 (outer-outer ≈ 360)
ALT_AXIS = (WHEEL_X, 0.0, 590.0)
# APEX_Z lowered so the cross tube + apex nodes sit BELOW the Ø200 wheel rim bottom
# (rim bottom = ALT_AXIS_z − 100 = 490). At 460 the cross-tube top (471) clears the
# rim by ~19 mm and the apex node top (~476) by ~14 mm; the cradle then lifts the
# rollers UP from the cross tube to the rim (see generate_rocker_towers).
APEX_Z = 460           # tower tubes + cross tube meet here (cradles clamp it, below the rim)
PINION_R = 240         # ring pitch 224 + pinion pitch 16
MOTOR_R = 181.4        # belt center distance 58.6


def polar(r, ang_deg, z=0.0):
    a = np.radians(ang_deg)
    return (r * np.cos(a), r * np.sin(a), z)


# ---------- Real-STL parts ----------

def ring_segment(k, dz=0.0, color=CLR_BODY):
    T = compose(translate(0, 0, RING_Z + dz), rotate_z(90 * k), RING_SEG_FIX)
    return load_part("Rocker_ring_segment", base_color=color, transform=T)


def azimuth_ring(dz=0.0):
    return [ring_segment(k, dz) for k in range(4)]


def pinion(dz=0.0):
    # native: gear OD36 z=0..14, hub Ø20 z=14..20, bore Ø8
    return load_part("Rocker_pinion_16T", base_color=CLR_BODY,
                     transform=translate(0, -PINION_R, 50 + dz))


def wheel_mesh():
    """Synthetic FULL wheel Ø200×15 with 8 windows — the user's printed wheels
    are full circles (the stock Leavitt STL is a 270° sector, reads as a
    broken hoop in renders). Axis Z, centered at origin."""
    if "wheel" not in _cache:
        disc = trimesh.creation.cylinder(radius=100, height=15, sections=64)
        holes = []
        for k in range(8):
            a = np.radians(k * 45 + 22.5)
            h = trimesh.creation.cylinder(radius=19, height=25, sections=24)
            h.apply_translation((55 * np.cos(a), 55 * np.sin(a), 0))
            holes.append(h)
        _cache["wheel"] = disc.difference(holes)
    return _cache["wheel"].copy()


def wheel(x_sign, dz=0.0):
    m = wheel_mesh()
    m.apply_transform(compose(translate(x_sign * WHEEL_X, 0, 590 + dz), rotate_y(90)))
    return mesh_to_polycoll(m, CLR_WHEEL)


def cap_azimuth(dz=0.0):
    # native: Ø18, z=0..19.9, bore side up. Flip -> bore down over the M10
    # bolt (bolt top z=112), magnet face UP at z=130.
    T = compose(translate(0, 0, 130 + dz), rotate_x(180))
    return load_part("magnet_cap_azimuth", base_color=CLR_NEW, transform=T, encoder=True)


def cap_altitude(dx=0.0):
    # native: spigot Ø6 z=-4..0, body Ø18 z=0..6.9. Axis -> X, spigot -X into
    # the wheel center hole (wheel outer face at x=177.5).
    T = compose(translate(177.5 + dx, 0, 590), rotate_y(90))
    return load_part("magnet_cap_altitude", base_color=CLR_NEW, transform=T, encoder=True)


def board_azimuth(dz=0.0):
    # native: 28x31 plate z=0..3, bosses to z=6, chip axis at origin.
    # Flip chip-side down; plate spans z=131..137, 1mm above magnet at 130.
    T = compose(translate(0, 0, 137 + dz), rotate_x(180))
    return load_part("board_holder", base_color=CLR_NEW, transform=T, encoder=True)


def board_altitude():
    # vertical, plate ⊥X at x=186..192, chip side facing the magnet (-X)
    T = compose(translate(192, 0, 590), rotate_y(-90))
    return load_part("board_holder", base_color=CLR_NEW, transform=T, encoder=True)


# ---------- Simplified hardware ----------

def nema17(transform, pulley_z=-20.0):
    """NEMA17: body 42.3^2 x48 at z=0..48, shaft Ø5 z=-22..0 pointing -Z,
    GT2 20T pulley Ø16x16 on the shaft at pulley_z."""
    out = []
    body = trimesh.creation.box(extents=(42.3, 42.3, 48))
    body.apply_translation((0, 0, 24))
    body.apply_transform(transform)
    out.append(mesh_to_polycoll(body, CLR_MOTOR))
    shaft = trimesh.creation.cylinder(radius=2.5, height=22, sections=16)
    shaft.apply_translation((0, 0, -11))
    shaft.apply_transform(transform)
    out.append(mesh_to_polycoll(shaft, CLR_HARDWARE))
    pulley = trimesh.creation.cylinder(radius=8, height=16, sections=24)
    pulley.apply_translation((0, 0, pulley_z))
    pulley.apply_transform(transform)
    out.append(mesh_to_polycoll(pulley, CLR_HARDWARE))
    return out


def pulley60(transform):
    """60T GT2: Ø40x12 disc with flange hints."""
    disc = trimesh.creation.cylinder(radius=20, height=12, sections=32)
    f1 = trimesh.creation.cylinder(radius=22.5, height=1.5, sections=32)
    f1.apply_translation((0, 0, 6.0))
    f2 = f1.copy()
    f2.apply_translation((0, 0, -12.0 - 1.5))
    m = trimesh.util.concatenate([disc, f1, f2])
    m.apply_transform(transform)
    return mesh_to_polycoll(m, CLR_HARDWARE)


def bearing_608(transform):
    return make_annulus(4, 11, 7, transform=transform, color=CLR_STEEL)


def belt_lines(p1a, p1b, p2a, p2b):
    """Belt = two straight Ø5 dark lines connecting pulley edges."""
    return [make_tube(p1a, p1b, radius=2.5, color=CLR_BELT, sections=10),
            make_tube(p2a, p2b, radius=2.5, color=CLR_BELT, sections=10)]


def m10_bolt(dz=0.0):
    return make_cyl(5, 67, transform=translate(0, 0, 78.5 + dz), color=CLR_HARDWARE)


# ---------- Ground station ----------

def ground_hub(dz=0.0):
    return make_cyl(35, 45, transform=translate(0, 0, 22.5 + dz), color=CLR_NEW)


def ground_arms(dz=0.0):
    return [make_tube(polar(35, a, 32 + dz), polar(R_ARM_OUT, a, 32 + dz))
            for a in CORNER_ANGLES]


def ground_feet(dz=0.0):
    return [make_trunccone(27.5, 22.5, 43,
                           transform=translate(*polar(R_FOOT, a, dz)), color=CLR_NEW)
            for a in CORNER_ANGLES]


def ground_saddles(dz=0.0):
    return [make_box((30, 30, 10), transform=translate(*polar(R_CORNER, a, 45 + dz)),
                     color=CLR_NEW)
            for a in CORNER_ANGLES]


def ground_station(with_ring=True, with_bolt=True):
    out = [ground_hub(), *ground_arms(), *ground_feet(), *ground_saddles()]
    if with_ring:
        out += azimuth_ring()
    if with_bolt:
        out.append(m10_bolt())
    return out


# ---------- Rotating frame ----------

def corner_node(ang, dz=0.0):
    x, y, _ = polar(R_CORNER, ang)
    T = compose(translate(x, y, 75 + dz), rotate_z(ang - 90))
    return make_box((65, 50, 28), transform=T, color=CLR_NEW)


def drive_corner_node(dz=0.0):
    # rear corner (270°), enlarged radially to reach the pinion shaft at r=240
    return make_box((65, 70, 28), transform=translate(0, -218, 75 + dz), color=CLR_NEW)


def frame_corners(dz=0.0, with_drive=True):
    out = [corner_node(30, dz), corner_node(150, dz)]
    if with_drive:
        out.append(drive_corner_node(dz))
    return out


def frame_base_tubes(dz=0.0):
    pts = [polar(R_CORNER, a, FRAME_Z + dz) for a in CORNER_ANGLES]
    return [make_tube(pts[i], pts[(i + 1) % 3]) for i in range(3)]


def frame_radial_tubes(dz=0.0):
    return [make_tube(polar(200, a, FRAME_Z + dz), polar(35, a, FRAME_Z + dz))
            for a in CORNER_ANGLES]


def center_pivot(dz=0.0):
    return make_cyl(30, 42, transform=translate(0, 0, 87 + dz), color=CLR_NEW)


def encoder_bridge(dz=0.0):
    """Post + arm on the pivot top carrying the AS5048A board face-down."""
    return [
        make_box((14, 14, 36), transform=translate(0, 28, 126 + dz), color=CLR_NEW),
        make_box((14, 42, 7), transform=translate(0, 14, 140.5 + dz), color=CLR_NEW),
        board_azimuth(dz),
    ]


def rotating_frame(dz=0.0):
    return [*frame_corners(dz), *frame_base_tubes(dz),
            *frame_radial_tubes(dz), center_pivot(dz)]


# ---------- Azimuth drive ----------

def az_drive(dz=0.0, motor_dz=0.0, with_node=False):
    out = []
    if with_node:
        out.append(drive_corner_node(dz))
    # vertical 8mm shaft
    out.append(make_cyl(4, 40, transform=translate(0, -PINION_R, 65 + dz),
                        color=CLR_HARDWARE, sections=16))
    out.append(pinion(dz))
    # two 608ZZ in the node around the shaft
    out.append(bearing_608(translate(0, -PINION_R, 64 + dz)))
    out.append(bearing_608(translate(0, -PINION_R, 81 + dz)))
    out.append(pulley60(translate(0, -PINION_R, 70 + dz)))
    # NEMA17 body above the node, shaft down, 20T at z=70
    out += nema17(translate(0, -MOTOR_R, 90 + dz + motor_dz), pulley_z=-20)
    out += belt_lines((14, -PINION_R, 70 + dz), (14, -MOTOR_R, 70 + dz),
                      (-14, -PINION_R, 70 + dz), (-14, -MOTOR_R, 70 + dz))
    return out


# ---------- Towers, cradles ----------

def tower_tubes(dz=0.0):
    out = []
    for s in (+1, -1):
        apex = (s * WHEEL_X, 0, APEX_Z + dz)
        out.append(make_tube(polar(R_CORNER, 30 if s > 0 else 150, FRAME_Z + dz), apex))
        out.append(make_tube(polar(R_CORNER, 270, FRAME_Z + dz), apex))
    return out


def cross_tube(dz=0.0):
    return make_tube((-WHEEL_X, 0, APEX_Z + dz), (WHEEL_X, 0, APEX_Z + dz))


def cradle(side, dx=0.0):
    """Cradle node: block 60x70x80 (top z=560), two 608 rollers at ±35° /
    r=111 under the wheel axis, ears, anti-lift hook over the rim."""
    xc = side * WHEEL_X + dx
    out = [make_box((60, 70, 80), transform=translate(xc, 0, 520), color=CLR_NEW)]
    for ys in (+1, -1):
        out.append(make_box((44, 30, 22), transform=translate(xc, ys * 48, 499),
                            color=CLR_NEW))
        out.append(bearing_608(compose(translate(xc, ys * 63.7, 499.1), rotate_y(90))))
    # anti-lift finger over the wheel rim top
    out.append(make_box((12, 12, 140), transform=translate(xc, 30, 630), color=CLR_NEW))
    out.append(make_box((12, 48, 12), transform=translate(xc, 12, 698), color=CLR_NEW))
    return out


# ---------- Telescope ----------

def telescope(dz=0.0):
    out = []
    # main ring Ø250 OD, axis Y
    out.append(make_annulus(114, 125, 80,
                            transform=compose(translate(0, 0, 590 + dz), rotate_x(90)),
                            color=CLR_SCOPE))
    out.append(wheel(+1, dz))
    out.append(wheel(-1, dz))
    # 3 white poles Ø22 around the Y axis
    for a in (90, 210, 330):
        px = 112 * np.cos(np.radians(a))
        pz = 590 + 112 * np.sin(np.radians(a)) + dz
        out.append(make_tube((px, -350, pz), (px, 350, pz), color=CLR_POLE))
    # mirror ring Ø260x60 + the mirror itself (light-blue disc in the far face)
    out.append(make_annulus(119, 130, 60,
                            transform=compose(translate(0, -400, 590 + dz), rotate_x(90)),
                            color=CLR_SCOPE))
    out.append(make_cyl(118, 5,
                        transform=compose(translate(0, -422, 590 + dz), rotate_x(90)),
                        color=(0.55, 0.78, 0.85), sections=48))
    return out


# ---------- Altitude drive & encoder ----------

def alt_drive(dz=0.0):
    out = []
    # friction roller Ø35x15 touching wheel rim from below, axis X
    T_roll = compose(translate(WHEEL_X, 0, 472.5 + dz), rotate_y(90))
    out.append(make_cyl(17.5, 15, transform=T_roll, color=CLR_NEW))
    out.append(make_torus(17.5, 2.5, transform=T_roll, color=CLR_BELT))
    # 8mm shaft along X, 60T at x=190
    out.append(make_tube((162.5, 0, 472.5 + dz), (195, 0, 472.5 + dz),
                         radius=4, color=CLR_HARDWARE, sections=16))
    out.append(pulley60(compose(translate(190, 0, 472.5 + dz), rotate_y(90))))
    # NEMA17 axis X, body extending +X, 20T at x=190, belt CD 58.6 vertical
    out += nema17(compose(translate(190, 0, 413.9 + dz), rotate_y(90)), pulley_z=0)
    out += belt_lines((190, 14, 472.5 + dz), (190, 14, 413.9 + dz),
                      (190, -14, 472.5 + dz), (190, -14, 413.9 + dz))
    # bracket to the cradle + spring hint
    out.append(make_box((16, 16, 100), transform=translate(198, 26, 465 + dz),
                        color=CLR_NEW))
    out.append(make_tube((162, -25, 485 + dz), (178, -25, 445 + dz),
                         radius=0.9, color=CLR_SPRING, sections=8))
    return out


def alt_encoder(dx_cap=0.0):
    return [
        cap_altitude(dx_cap),
        board_altitude(),
        make_box((10, 14, 70), transform=translate(196, 0, 577), color=CLR_NEW),
    ]


def e4_box():
    return make_box((110, 75, 25), transform=translate(0, -180, 88), color=CLR_E4)


# ---------- Assembled groups ----------

def full_base():
    """Ground station + ring + rotating frame + encoder + azimuth drive."""
    return [*ground_station(), *rotating_frame(), cap_azimuth(),
            *encoder_bridge(), *az_drive()]


def full_mount():
    return [*full_base(), *tower_tubes(), cross_tube(),
            *cradle(+1), *cradle(-1)]


# ---------- The comic ----------

def build_comic():
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ROOT / "rocker_assembly_comic.pdf"
    with PdfPages(out_path) as pdf:
        # ===== Page 1: inventory — printed parts =====
        items = [
            ([load_part("Rocker_ring_segment")], 4),
            ([load_part("Rocker_pinion_16T")], 1),
            ([make_cyl(35, 45, transform=translate(0, 0, 22.5))], 1),
            ([make_trunccone(27.5, 22.5, 43)], 3),
            ([make_box((65, 50, 28))], 2),
            ([make_box((65, 70, 28))], 1),
            ([make_cyl(30, 42, transform=translate(0, 0, 21)),
              make_box((14, 14, 36), transform=translate(0, 28, 60)),
              make_box((14, 42, 7), transform=translate(0, 14, 74.5))], 1),
            ([make_box((60, 70, 80), transform=translate(0, 0, 40)),
              make_box((44, 30, 22), transform=translate(0, 48, 19)),
              make_box((44, 30, 22), transform=translate(0, -48, 19)),
              make_box((12, 12, 140), transform=translate(0, 30, 150)),
              make_box((12, 48, 12), transform=translate(0, 12, 218))], 2),
            ([make_box((16, 16, 100))], 1),
            ([make_box((30, 30, 10))], 3),
        ]
        page_inventory(pdf, 1, items, rows=4, cols=3)

        # ===== Page 2: inventory — hardware =====
        items = [
            (nema17(np.eye(4), pulley_z=-11), 2),
            ([bearing_608(np.eye(4))], 8),
            ([pulley60(np.eye(4)),
              make_cyl(8, 16, transform=translate(0, 58.6, 0), color=CLR_HARDWARE),
              *belt_lines((14, 0, 0), (8, 58.6, 0), (-14, 0, 0), (-8, 58.6, 0))], 2),
            ([make_cyl(5, 67, transform=translate(0, 0, 33.5), color=CLR_HARDWARE),
              make_box((18, 18, 7), transform=translate(0, 0, 70.5),
                       color=CLR_HARDWARE)], 1),
            ([make_tube((-200, 0, 0), (200, 0, 0))], 11),
            ([mesh_to_polycoll(wheel_mesh(), CLR_WHEEL)], 2),
            ([load_part("magnet_cap_azimuth", base_color=CLR_NEW,
                        transform=translate(-22, 0, 0), encoder=True),
              load_part("magnet_cap_altitude", base_color=CLR_NEW, encoder=True),
              load_part("board_holder", base_color=CLR_NEW,
                        transform=translate(30, 0, 0), encoder=True)], 2),
        ]
        page_inventory(pdf, 2, items, rows=4, cols=2)

        # ===== Page 3: ground star — hub + arms + feet exploded, bolt down =====
        lift = 90
        arrows = [((0, 0, 205), (0, 0, 125))]
        for a in CORNER_ANGLES:
            arrows.append((polar(160, a, 30 + lift - 15), polar(160, a, 55)))
        page_step(
            pdf, 3, TOTAL,
            [ground_hub(), *ground_feet(), *ground_arms(lift),
             m10_bolt(lift + 45)],
            arrows=arrows,
            center=(0, 0, 95), span=270, elev=26, azim=-55,
        )

        # ===== Page 4: ring — 4 segments hover, arrows down onto saddles =====
        seg_lift = 150
        arrows = [(polar(R_CORNER, a, RING_Z + seg_lift - 10), polar(R_CORNER, a, 68))
                  for a in CORNER_ANGLES]
        page_step(
            pdf, 4, TOTAL,
            [*ground_station(with_ring=False), *azimuth_ring(seg_lift)],
            arrows=arrows,
            center=(0, 0, 130), span=330, elev=22, azim=-55,
        )

        # ===== Page 5: rotating frame drops onto the bolt / ring track =====
        f_lift = 250
        page_step(
            pdf, 5, TOTAL,
            [*ground_station(), *rotating_frame(f_lift)],
            arrows=[((0, 0, 66 + f_lift - 15), (0, 0, 125))],
            center=(0, 0, 200), span=330, elev=15, azim=-55,
        )

        # ===== Page 6: CLOSE-UP azimuth encoder — cap on bolt, board lowers =====
        b_lift = 26
        page_step(
            pdf, 6, TOTAL,
            [center_pivot(), m10_bolt(), cap_azimuth(),
             *frame_radial_tubes(), *encoder_bridge(b_lift)],
            arrows=[((0, -14, 156), (0, -14, 134))],
            center=(0, 0, 121), span=60, elev=18, azim=-55,
        )

        # ===== Page 7: CLOSE-UP azimuth drive at the rear corner =====
        page_step(
            pdf, 7, TOTAL,
            [*ground_station(), *frame_base_tubes(), *frame_radial_tubes(),
             corner_node(30), corner_node(150), *az_drive()],
            ghost=[drive_corner_node()],
            arrows=[((0, -MOTOR_R, 185), (0, -MOTOR_R, 142)),
                    ((36, -274, 56), (4, -248, 56))],
            center=(0, -215, 85), span=120, elev=18, azim=-55,
        )

        # ===== Page 8: towers — 4 tubes + cross tube hover, arrows down =====
        t_lift = 200
        arrows = [
            (polar(R_CORNER, 30, FRAME_Z + t_lift - 15), polar(R_CORNER, 30, 100)),
            (polar(R_CORNER, 150, FRAME_Z + t_lift - 15), polar(R_CORNER, 150, 100)),
            (polar(R_CORNER, 270, FRAME_Z + t_lift - 15), polar(R_CORNER, 270, 100)),
            ((WHEEL_X, 0, APEX_Z + t_lift - 15), (WHEEL_X, 0, APEX_Z + 25)),
            ((-WHEEL_X, 0, APEX_Z + t_lift - 15), (-WHEEL_X, 0, APEX_Z + 25)),
        ]
        page_step(
            pdf, 8, TOTAL,
            [*full_base(), *tower_tubes(t_lift), cross_tube(t_lift)],
            arrows=arrows,
            center=(0, 0, 330), span=440, elev=12, azim=-55,
        )

        # ===== Page 9: cradles slide onto the cross tube (along X) =====
        c_dx = 175
        page_step(
            pdf, 9, TOTAL,
            [*full_base(), *tower_tubes(), cross_tube(),
             *cradle(+1, dx=c_dx), *cradle(-1, dx=-c_dx)],
            arrows=[((295, 0, 520), (215, 0, 520)),
                    ((-295, 0, 520), (-215, 0, 520))],
            center=(0, 0, 330), span=450, elev=12, azim=-55,
        )

        # ===== Page 10: telescope drops into the cradles =====
        s_lift = 150
        page_step(
            pdf, 10, TOTAL,
            [*full_mount(), *telescope(s_lift)],
            arrows=[((235, 0, 790), (235, 0, 565)),
                    ((-235, 0, 790), (-235, 0, 565))],
            center=(0, 0, 440), span=510, elev=12, azim=-55,
        )

        # ===== Page 11: CLOSE-UP altitude drive — roller pressed to the rim =====
        page_step(
            pdf, 11, TOTAL,
            [wheel(+1), cross_tube(), *tower_tubes(), *alt_drive()],
            ghost=cradle(+1),
            arrows=[((170, -60, 418), (170, -16, 452))],
            center=(182, 0, 468), span=130, elev=16, azim=-60,
        )

        # ===== Page 12: CLOSE-UP altitude encoder — cap into the wheel hub =====
        page_step(
            pdf, 12, TOTAL,
            [wheel(+1), *alt_encoder(dx_cap=34)],
            arrows=[((224, -12, 599), (196, -2, 591))],
            center=(188, 0, 588), span=62, elev=12, azim=-30,
        )

        # ===== Page 13: FINALE — the whole mount, hero shot =====
        page_step(
            pdf, 13, TOTAL,
            [*full_mount(), *telescope(), *alt_drive(), *alt_encoder(),
             e4_box()],
            arrows=None,
            center=(0, -50, 340), span=420, elev=12, azim=-35,
        )

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    build_comic()
