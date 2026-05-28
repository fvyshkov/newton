#!/usr/bin/env python3
"""
Wordless assembly comic for the truss-Dobson.

Generates truss_assembly_comic.pdf — a step-by-step visual guide that shows
how the printed parts come together. No descriptions — just numbered panels,
exploded views, and arrows.
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
LEGACY_STL = ROOT.parent / "stl" / "mirror_cell"

CLR_BODY = (0.78, 0.78, 0.80)
CLR_NEW = (0.95, 0.55, 0.25)
CLR_HARDWARE = (0.45, 0.45, 0.48)
CLR_TUBE = (0.72, 0.74, 0.78)
CLR_MIRROR = (0.55, 0.78, 0.85)

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


def load_part(name, base_color=CLR_BODY, transform=None, legacy=False):
    folder = LEGACY_STL if legacy else STL
    m = load_stl(folder / f"{name}.stl")
    if transform is not None:
        m.apply_transform(transform)
    return mesh_to_polycoll(m, base_color)


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


def rotate_z(deg):
    return trimesh.transformations.rotation_matrix(np.radians(deg), [0, 0, 1])


def compose(*mats):
    out = np.eye(4)
    for M in mats:
        out = out @ M
    return out


def make_tube(radius, length, transform=None, color=CLR_TUBE):
    m = trimesh.creation.cylinder(radius=radius, height=length, sections=24)
    if transform is not None:
        m.apply_transform(transform)
    return mesh_to_polycoll(m, color)


def make_bolt(length=12, radius=2.5, transform=None):
    shaft = trimesh.creation.cylinder(radius=radius, height=length, sections=20)
    head = trimesh.creation.box(extents=(radius * 2.4, radius * 2.4, 3))
    head.apply_translation((0, 0, length / 2 + 1.5))
    bolt = trimesh.util.concatenate([shaft, head])
    if transform is not None:
        bolt.apply_transform(transform)
    return mesh_to_polycoll(bolt, CLR_HARDWARE)


def make_disc(radius, thickness, transform=None, color=CLR_MIRROR):
    m = trimesh.creation.cylinder(radius=radius, height=thickness, sections=64)
    if transform is not None:
        m.apply_transform(transform)
    return mesh_to_polycoll(m, color)


def add_payload(ax, payload, alpha=1.0):
    tri, fc, _ = payload
    poly = Poly3DCollection(tri, facecolors=fc, edgecolor="none", linewidth=0, alpha=alpha)
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
    fig.text(0.05, 0.94, f"{number}", fontsize=110, fontweight="bold", color="#222")
    fig.text(0.94, 0.94, f"/ {total}", fontsize=20, color="#bbb", ha="right", va="center")


# ---------- Truss socket placement helpers ----------
# Native Truss_socket.stl sits at +X,+Y corner of mirror box.
# Native bounds: x,y = 106..195, z = 80..200. Anchor: clamp center at (167,167).

def socket_on_box_corner(corner, z_offset=0):
    """Place a socket on the mirror box. corner=0..3 for +X+Y, -X+Y, -X-Y, +X-Y."""
    angle = corner * 90
    return compose(translate(0, 0, z_offset), rotate_z(angle))


def socket_on_uta(corner, z_offset):
    """Same socket but flipped 180° around X to grip from above on UTA frame."""
    # Flip around X axis at z=140 (mid of clamp), then place at corner
    flip = trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0])
    # The flip mirrors Z about z=0, so socket that was z=80..200 becomes z=-200..-80
    # Then shift up by uta_top + some offset
    angle = corner * 90
    return compose(translate(0, 0, z_offset), rotate_z(angle), flip)


# ---------- Page builders ----------

def page_step(pdf, n, total, payloads, arrows=None, center=None, span=300, elev=18, azim=-55):
    fig = plt.figure(figsize=(11, 14), dpi=140)
    ax = fig.add_subplot(111, projection="3d")
    for p in payloads:
        add_payload(ax, p)
    if arrows:
        for s, e in arrows:
            arrow_3d(ax, s, e)
    if center is None:
        all_v = np.vstack([p[0].reshape(-1, 3) for p in payloads])
        center = all_v.mean(axis=0)
    setup_axes(ax, center=center, span=span, elev=elev, azim=azim)
    step_label(fig, n, total)
    pdf.savefig(fig, dpi=140)
    plt.close()


def page_inventory(pdf):
    """Page 1: each unique printed part shown once with its quantity badge."""
    items = [
        ("Mirror_box", 1, False),
        ("UTA_ring", 1, False),
        ("Truss_socket", 8, False),
        ("Spider_4vane", 1, False),
        ("Secondary_holder", 1, False),
        ("Cell_leg_bracket", 3, False),
    ]
    fig = plt.figure(figsize=(11, 14), dpi=140)
    for i, (name, qty, legacy) in enumerate(items):
        ax = fig.add_subplot(3, 2, i + 1, projection="3d")
        tri, fc, bb = load_part(name, legacy=legacy)
        poly = Poly3DCollection(tri, facecolors=fc, edgecolor="none", linewidth=0)
        poly.set_rasterized(True)
        ax.add_collection3d(poly)
        size = bb[1] - bb[0]
        span = size.max() * 0.62
        c = (bb[0] + bb[1]) / 2
        setup_axes(ax, center=c, span=span, elev=22, azim=-50)
        # Quantity badge: big × N in orange, top-right of the panel
        ax.text2D(
            0.92, 0.90, f"×{qty}",
            transform=ax.transAxes,
            fontsize=36, fontweight="bold", color="#d04020",
            ha="right", va="top",
        )
        # Part index in dark grey, top-left
        ax.text2D(
            0.06, 0.90, f"{i + 1}",
            transform=ax.transAxes,
            fontsize=24, fontweight="bold", color="#333",
            ha="left", va="top",
        )
    plt.tight_layout()
    pdf.savefig(fig, dpi=140)
    plt.close()


# ---------- Assembly world geometry ----------
BOX_TOP = 130             # mirror box top edge
UTA_FRAME_BOTTOM = 1000   # where UTA frame sits in the assembled world
UTA_FRAME_TOP = UTA_FRAME_BOTTOM + 120


def box_payload(color=CLR_BODY):
    return load_part("Mirror_box", base_color=color)


def uta_payload(z, color=CLR_BODY):
    return load_part("UTA_ring", base_color=color, transform=translate(0, 0, z))


def four_box_sockets(highlight_one=None, color=CLR_BODY, new_color=CLR_NEW):
    """4 sockets on the mirror box corners. highlight_one=index colors one orange."""
    out = []
    for i in range(4):
        c = new_color if i == highlight_one else color
        out.append(load_part("Truss_socket", base_color=c, transform=socket_on_box_corner(i)))
    return out


def four_uta_sockets(z, color=CLR_BODY):
    """4 sockets on UTA frame, flipped to grip from above."""
    # Socket native z=80..200, after X-flip becomes -200..-80.
    # We want sockets clamps to sit on UTA frame z=0..120 (UTA frame height 120).
    # Place such that the clamp cylinder portion (originally z=130..200) lies just above frame.
    # After X-flip, original z=130..200 → z=-200..-130.
    # We want that range to be at z_world = UTA_FRAME_BOTTOM-70..UTA_FRAME_BOTTOM (clamp hanging below UTA frame), so offset = UTA_FRAME_BOTTOM + 200-130 - wait simpler:
    # We want flipped socket bottom (was z=80) → flipped to z=-80, ends up at world z_off-80.
    # UTA frame sits at UTA_FRAME_BOTTOM..UTA_FRAME_BOTTOM+120.
    # Put the socket's clamp portion overlapping z = UTA_FRAME_BOTTOM..UTA_FRAME_BOTTOM+120.
    # After flip: original socket extends z=80..200, flipped → z=-200..-80.
    # We want this to land at z = UTA_FRAME_BOTTOM..UTA_FRAME_BOTTOM+120 (i.e. socket clamp spans frame).
    # So offset = UTA_FRAME_BOTTOM + 200 = z. We translate by z so flipped z=-200 becomes z, and z=-80 becomes z+120.
    out = []
    for i in range(4):
        out.append(load_part("Truss_socket", base_color=color, transform=socket_on_uta(i, z + 200)))
    return out


def four_tubes(z_bottom, z_top, color=CLR_TUBE):
    """4 truss tubes between mirror box and UTA. Tubes go at the four corners."""
    out = []
    length = z_top - z_bottom
    radius = 11  # ~22mm tube
    for cx, cy in [(167, 167), (-167, 167), (-167, -167), (167, -167)]:
        m = trimesh.creation.cylinder(radius=radius, height=length, sections=20)
        m.apply_translation((cx, cy, z_bottom + length / 2))
        out.append(mesh_to_polycoll(m, color))
    return out


def spider_in_uta(z_center_uta, base_color=CLR_BODY):
    # Spider native: flat, z=0..16. Center of spider should be at UTA cylinder mid-height.
    # In UTA local: secondary center at z=222. World: UTA_FRAME_BOTTOM + 222.
    return load_part("Spider_4vane", base_color=base_color,
                     transform=translate(0, 0, z_center_uta - 8))


def secondary_holder_at(z_center, base_color=CLR_BODY):
    # Secondary_holder native: 58×58×70, base at z=0. Place center at z_center.
    return load_part("Secondary_holder", base_color=base_color,
                     transform=translate(0, 0, z_center - 35))


def mirror_disc(z):
    return make_disc(radius=101.5, thickness=20,
                     transform=translate(0, 0, z), color=CLR_MIRROR)


def mirror_cell_back(z, color=CLR_BODY):
    return load_part("Mirror_cell_back", base_color=color,
                     transform=translate(0, 0, z), legacy=True)


def mirror_cell_front(z, color=CLR_BODY):
    return load_part("Mirror_cell_front", base_color=color,
                     transform=translate(0, 0, z), legacy=True)


def three_leg_brackets(z_base, color=CLR_BODY):
    """3 leg brackets at 120° around old mirror cell. Native at (0..14, -13..13, -56..4).

    Bracket-local +x = radial outward; concave inner face at x=0 wraps the ear
    cylinder of radius EAR_R=125. Push 3mm into the ear so the parts read as
    bolted/joined instead of just touching at a thin curve.
    """
    out = []
    radius = 122  # 3mm overlap with ear cylinder (r=125) — visibly joined
    for k in range(3):
        ang = 30 + k * 120
        rad = np.radians(ang)
        cx, cy = radius * np.cos(rad), radius * np.sin(rad)
        T = compose(translate(cx, cy, z_base), rotate_z(ang))
        out.append(load_part("Cell_leg_bracket", base_color=color, transform=T))
    return out


# ---------- The comic ----------

def build_comic():
    out_path = ROOT / "truss_assembly_comic.pdf"
    total = 8
    with PdfPages(out_path) as pdf:
        # ===== Page 1: inventory =====
        page_inventory(pdf)

        # ===== Step 1: Mirror box alone, then 4 sockets descending from above =====
        # Show the box at Z=0..130 and 4 sockets exploded up by +120
        box = box_payload()
        socket_offset = 220
        sockets_up = []
        for i in range(4):
            sockets_up.append(
                load_part(
                    "Truss_socket",
                    base_color=CLR_NEW,
                    transform=compose(translate(0, 0, socket_offset), rotate_z(i * 90)),
                )
            )
        # arrows from raised sockets down to their corners on box
        arrows = []
        for i in range(4):
            ang = np.radians(i * 90)
            # native socket center at (167,167); after rotation:
            cx = 167 * np.cos(ang) - 167 * np.sin(ang)
            cy = 167 * np.sin(ang) + 167 * np.cos(ang)
            arrows.append(((cx, cy, 80 + socket_offset + 60),
                           (cx, cy, 150)))
        page_step(
            pdf, 1, total,
            [box, *sockets_up],
            arrows=arrows,
            center=(0, 0, 150), span=260, elev=22, azim=-55,
        )

        # ===== Step 2: Same view but sockets seated; 4 tubes raised above =====
        box = box_payload()
        sockets_seated = four_box_sockets(color=CLR_BODY)
        tube_lift = 380
        tubes_up = []
        for cx, cy in [(167, 167), (-167, 167), (-167, -167), (167, -167)]:
            m = trimesh.creation.cylinder(radius=11, height=900, sections=20)
            m.apply_translation((cx, cy, tube_lift + 450))
            tubes_up.append(mesh_to_polycoll(m, CLR_NEW))
        arrows = []
        for cx, cy in [(167, 167), (-167, 167), (-167, -167), (167, -167)]:
            arrows.append(((cx, cy, tube_lift + 30), (cx, cy, 210)))
        page_step(
            pdf, 2, total,
            [box, *sockets_seated, *tubes_up],
            arrows=arrows,
            center=(0, 0, 500), span=620, elev=8, azim=-55,
        )

        # ===== Step 3: Tubes seated. Now show UTA assembly being formed separately:
        # UTA ring with 4 sockets exploded above it =====
        # We'll show ONLY the UTA part being assembled (not the whole telescope).
        uta_z = 0
        uta = load_part("UTA_ring", base_color=CLR_BODY,
                        transform=translate(0, 0, uta_z))
        # UTA sockets in their seated position (gripping frame from above)
        uta_socket_seated = []
        # ===== Step 3: UTA + 4 sockets coming down onto UTA frame =====
        sockets_above = []
        for i in range(4):
            T = compose(
                translate(0, 0, 380),
                rotate_z(i * 90),
                trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]),
            )
            sockets_above.append(load_part("Truss_socket", base_color=CLR_NEW, transform=T))
        # Arrows down onto UTA frame corners
        arrows = []
        for i in range(4):
            ang = np.radians(i * 90)
            cx = 167 * np.cos(ang) - 167 * np.sin(ang)
            cy = 167 * np.sin(ang) + 167 * np.cos(ang)
            arrows.append(((cx, cy, 320), (cx, cy, 130)))
        page_step(
            pdf, 3, total,
            [uta, *sockets_above],
            arrows=arrows,
            center=(0, 0, 200), span=300, elev=20, azim=-55,
        )

        # ===== Step 4: UTA + sockets seated, spider drops in from above =====
        uta = load_part("UTA_ring", base_color=CLR_BODY)
        # 4 seated UTA sockets (flipped)
        uta_sockets = []
        for i in range(4):
            T = compose(
                rotate_z(i * 90),
                trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]),
                translate(0, 0, -200),  # bring flipped socket into UTA frame
            )
            # Simpler: use socket_on_uta-like placement; bypass for clarity:
            # native socket flipped → z=-200..-80. Then translate +120 so it lands at z=-80..40.
            # That doesn't match UTA frame z=0..120. Re-derive:
            # We want clamp portion (orig z=130..200, flipped → z=-200..-130) at z=0..70 of UTA frame.
            # So shift = +200. Then z=-200..-130 → z=0..70.  z=-80..-200 → z=120..0 (overlapping frame).
            T = compose(
                translate(0, 0, 200),
                rotate_z(i * 90),
                trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]),
            )
            uta_sockets.append(load_part("Truss_socket", base_color=CLR_BODY, transform=T))
        # Spider above UTA cylinder
        spider_z_target = 222  # UTA local: secondary center
        spider = load_part("Spider_4vane", base_color=CLR_NEW,
                           transform=translate(0, 0, 380))
        page_step(
            pdf, 4, total,
            [uta, *uta_sockets, spider],
            arrows=[((0, 0, 370), (0, 0, spider_z_target + 10))],
            center=(0, 0, 200), span=280, elev=18, azim=-55,
        )

        # ===== Step 5: Spider seated, secondary holder drops onto spider hub =====
        uta = load_part("UTA_ring", base_color=CLR_BODY)
        uta_sockets = []
        for i in range(4):
            T = compose(
                translate(0, 0, 200),
                rotate_z(i * 90),
                trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]),
            )
            uta_sockets.append(load_part("Truss_socket", base_color=CLR_BODY, transform=T))
        spider = load_part("Spider_4vane", base_color=CLR_BODY,
                           transform=translate(0, 0, spider_z_target - 8))
        sec_holder = load_part("Secondary_holder", base_color=CLR_NEW,
                               transform=translate(0, 0, 350))
        page_step(
            pdf, 5, total,
            [uta, *uta_sockets, spider, sec_holder],
            # Arrow points to where the holder slab will land: on top of spider hub.
            arrows=[((0, 0, 345), (0, 0, spider_z_target - 2))],
            center=(0, 0, 200), span=280, elev=18, azim=-55,
        )

        # ===== Step 6: Mirror cell sub-assembly — show old back plate + 3 leg brackets =====
        back = load_part("Mirror_cell_back", base_color=CLR_BODY, legacy=True,
                         transform=translate(0, 0, 0))
        # 3 brackets exploded above the back plate, with arrows down to its ears
        brackets = []
        bracket_lift = 120
        for k in range(3):
            ang = 30 + k * 120
            rad = np.radians(ang)
            cx, cy = 122 * np.cos(rad), 122 * np.sin(rad)
            T = compose(translate(cx, cy, bracket_lift), rotate_z(ang))
            brackets.append(load_part("Cell_leg_bracket", base_color=CLR_NEW, transform=T))
        arrows = []
        for k in range(3):
            ang = np.radians(30 + k * 120)
            cx, cy = 122 * np.cos(ang), 122 * np.sin(ang)
            arrows.append(((cx, cy, bracket_lift - 20), (cx, cy, 0)))
        page_step(
            pdf, 6, total,
            [back, *brackets],
            arrows=arrows,
            center=(0, 0, 30), span=180, elev=22, azim=-55,
        )

        # ===== Step 7: Lower the UTA assembly down onto the four tubes =====
        # Compose full bottom assembly: box + sockets + tubes
        box = box_payload()
        sockets_seated = four_box_sockets(color=CLR_BODY)
        tubes_in_place = []
        for cx, cy in [(167, 167), (-167, 167), (-167, -167), (167, -167)]:
            # Tubes go from box socket bore bottom (z=80) to UTA frame top (z=1100)
            # so they fully fill both clamp bores — joined, not just touching.
            m = trimesh.creation.cylinder(radius=11, height=1020, sections=20)
            m.apply_translation((cx, cy, 80 + 510))  # tube from z=80 to z=1100
            tubes_in_place.append(mesh_to_polycoll(m, CLR_TUBE))

        # UTA assembly lifted above
        uta_lift = 1200
        uta_top = load_part("UTA_ring", base_color=CLR_NEW,
                            transform=translate(0, 0, uta_lift))
        uta_sockets_top = []
        for i in range(4):
            T = compose(
                translate(0, 0, uta_lift + 200),
                rotate_z(i * 90),
                trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]),
            )
            uta_sockets_top.append(load_part("Truss_socket", base_color=CLR_NEW, transform=T))
        spider_top = load_part("Spider_4vane", base_color=CLR_NEW,
                               transform=translate(0, 0, uta_lift + spider_z_target - 8))
        # Holder slab sinks 2mm into spider hub top (visibly joined, not just
        # touching at one Z value). Hub top = sz-2, push slab down 2mm to sz-4.
        sec_top = load_part("Secondary_holder", base_color=CLR_NEW,
                            transform=translate(0, 0, uta_lift + spider_z_target - 4))

        # Arrow: big down arrow from UTA assembly to tubes
        arrows = [((0, 0, uta_lift - 50), (0, 0, 1050))]
        page_step(
            pdf, 7, total,
            [box, *sockets_seated, *tubes_in_place, uta_top,
             *uta_sockets_top, spider_top, sec_top],
            arrows=arrows,
            center=(0, 0, 800), span=900, elev=8, azim=-55,
        )

        # ===== Step 8: Hero shot — everything assembled =====
        # UTA placed so its sockets hug the tube tops.
        UTA_AT = 980
        box = box_payload()
        sockets_seated = four_box_sockets(color=CLR_BODY)
        tubes_full = []
        for cx, cy in [(167, 167), (-167, 167), (-167, -167), (167, -167)]:
            # Tubes fully fill both clamp bores (box: z=80..200, UTA: z=980..1100).
            m = trimesh.creation.cylinder(radius=11, height=1020, sections=20)
            m.apply_translation((cx, cy, 80 + 510))  # z=80 to z=1100
            tubes_full.append(mesh_to_polycoll(m, CLR_TUBE))
        uta_final = load_part("UTA_ring", base_color=CLR_BODY,
                              transform=translate(0, 0, UTA_AT))
        uta_sockets_final = []
        for i in range(4):
            T = compose(
                translate(0, 0, UTA_AT + 200),
                rotate_z(i * 90),
                trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]),
            )
            uta_sockets_final.append(load_part("Truss_socket", base_color=CLR_BODY, transform=T))
        spider_final = load_part("Spider_4vane", base_color=CLR_BODY,
                                 transform=translate(0, 0, UTA_AT + spider_z_target - 8))
        # Holder slab sinks 2mm into spider hub for visible joining.
        sec_final = load_part("Secondary_holder", base_color=CLR_BODY,
                              transform=translate(0, 0, UTA_AT + spider_z_target - 4))
        # Mirror cell at bottom, inside the box. cell_z=66 chosen so the leg
        # brackets (which extend 56mm below the cell ear) sit 2mm above the
        # box floor (z=8), while the cell-front retainers (62mm above the ear)
        # have 2mm clearance under the box top (z=130).
        cell_z = 66
        back_final = load_part("Mirror_cell_back", base_color=CLR_BODY, legacy=True,
                               transform=translate(0, 0, cell_z))
        front_final = load_part("Mirror_cell_front", base_color=CLR_BODY, legacy=True,
                                transform=translate(0, 0, cell_z))
        bracket_final = []
        for k in range(3):
            ang = 30 + k * 120
            rad = np.radians(ang)
            # 3mm radial overlap with ear (r=125) so bracket visibly hugs/joins.
            cx, cy = 122 * np.cos(rad), 122 * np.sin(rad)
            T = compose(translate(cx, cy, cell_z), rotate_z(ang))
            bracket_final.append(load_part("Cell_leg_bracket", base_color=CLR_BODY, transform=T))
        # Mirror disc (20mm thick) sinks 2mm into cell back top so it reads
        # as resting in/joined to the cell rather than floating above it.
        mirror_z = cell_z + 4 + 10 - 2
        mirror = make_disc(101.5, 20, transform=translate(0, 0, mirror_z), color=CLR_MIRROR)
        # 3 M8 collimation shafts from box floor (z=8) up through the bracket
        # M8 holes (z=cell_z-44=22). Without these the cell would look like
        # it's floating inside the box.
        m8_shafts = []
        for k in range(3):
            ang = 30 + k * 120
            rad = np.radians(ang)
            sx, sy = 132 * np.cos(rad), 132 * np.sin(rad)
            shaft = trimesh.creation.cylinder(radius=4, height=60, sections=16)
            shaft.apply_translation((sx, sy, 8 + 30))  # z=8..68 (through bracket M8 at z=22)
            m8_shafts.append(mesh_to_polycoll(shaft, CLR_HARDWARE))

        page_step(
            pdf, 8, total,
            [box, *sockets_seated, *tubes_full, uta_final,
             *uta_sockets_final, spider_final, sec_final,
             back_final, front_final, *bracket_final, *m8_shafts, mirror],
            arrows=None,
            center=(0, 0, 600), span=750, elev=5, azim=-60,
        )

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    build_comic()
