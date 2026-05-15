#!/usr/bin/env python3
"""
Comic-style assembly guide for the Leavitt focuser.

Produces focuser_assembly_comic.pdf — a sequence of 3D renders that
shows assembly steps visually, IKEA-style, with minimal text.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from matplotlib.backends.backend_pdf import PdfPages
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

# Decimate heavy meshes — we don't need 100k triangles for a visual guide
DECIMATE_TARGET = 4000  # triangles per part max

ROOT = Path(__file__).parent
STL = ROOT / "stl"

# Color palette: muted neutral + one accent for the "active" part being added
CLR_BODY = (0.78, 0.78, 0.80)   # assembled parts
CLR_NEW = (0.95, 0.55, 0.25)    # part being added in this step (orange)
CLR_HARDWARE = (0.45, 0.45, 0.48)  # bolts


_cache = {}


def load_part(name, base_color=CLR_BODY, transform=None):
    """Load STL (decimated), optionally transform, return (verts, faces, facecolors)."""
    if name not in _cache:
        m = trimesh.load(STL / f"{name}.stl")
        if len(m.faces) > DECIMATE_TARGET:
            try:
                m = m.simplify_quadric_decimation(face_count=DECIMATE_TARGET)
            except Exception:
                pass
        _cache[name] = m
    m = _cache[name].copy()
    if transform is not None:
        m.apply_transform(transform)
    return mesh_to_polycoll_data(m, base_color)


def mesh_to_polycoll_data(mesh, base_color):
    tri = mesh.vertices[mesh.faces]
    n = mesh.face_normals
    light = np.array([0.4, 0.3, 1.0])
    light /= np.linalg.norm(light)
    intens = np.clip(0.40 + 0.60 * (n @ light), 0.25, 1.0)
    base = np.array(base_color)
    facecolors = (base[None, :] * intens[:, None]).clip(0, 1)
    return tri, facecolors, mesh.bounds


def make_bolt(length=12, radius=2.5, transform=None):
    """Simple bolt: cylinder + box head."""
    shaft = trimesh.creation.cylinder(radius=radius, height=length, sections=24)
    head = trimesh.creation.box(extents=(radius * 2.2, radius * 2.2, 3))
    head.apply_translation((0, 0, length / 2 + 1.5))
    bolt = trimesh.util.concatenate([shaft, head])
    if transform is not None:
        bolt.apply_transform(transform)
    return mesh_to_polycoll_data(bolt, CLR_HARDWARE)


def translate(x, y, z):
    M = np.eye(4)
    M[:3, 3] = (x, y, z)
    return M


def add_to_axes(ax, payload, alpha=1.0):
    tri, fc, _ = payload
    poly = Poly3DCollection(tri, facecolors=fc, edgecolor="none", linewidth=0, alpha=alpha)
    poly.set_rasterized(True)  # critical: keeps PDF size small
    ax.add_collection3d(poly)


def arrow_3d(ax, start, end, color="#d04020", lw=3, headsize=0.05):
    """Draw a 3D arrow from start to end."""
    ax.quiver(
        start[0], start[1], start[2],
        end[0] - start[0], end[1] - start[1], end[2] - start[2],
        color=color, arrow_length_ratio=0.18, lw=lw,
    )


def setup_axes(ax, center=(0, 0, 0), span=120, elev=22, azim=-55):
    cx, cy, cz = center
    ax.set_xlim(cx - span, cx + span)
    ax.set_ylim(cy - span, cy + span)
    ax.set_zlim(cz - span, cz + span)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()


def panel_label(fig, number, total, subtitle=""):
    """Big step number top-left, total in top-right. Subtitle ignored for text-free comic."""
    fig.text(0.05, 0.92, f"{number}", fontsize=96, fontweight="bold", color="#222")
    fig.text(0.93, 0.92, f"/ {total}", fontsize=18, color="#bbb", ha="right", va="center")


def page_inventory(pdf):
    """Page 1: all 10 parts in a grid with numbers."""
    parts = [
        "Focuser outer bottom", "Focuser outer top", "Focuser inner",
        "Focuser ring", "Collet", "Collet nut",
        "Focuser grub", "Focuser grub screw panel", "1.25 eyepiece adapter",
        "Focuser saddle",
    ]
    fig = plt.figure(figsize=(11, 14), dpi=150)
    # No header text — let the images speak. Just the part numbers.
    for i, name in enumerate(parts):
        ax = fig.add_subplot(4, 3, i + 1, projection="3d")
        tri, fc, bb = load_part(name)
        poly = Poly3DCollection(tri, facecolors=fc, edgecolor="none", linewidth=0)
        poly.set_rasterized(True)
        ax.add_collection3d(poly)
        span = (bb[1] - bb[0]).max() * 0.58
        c = (bb[0] + bb[1]) / 2
        setup_axes(ax, center=c, span=span)
        ax.text2D(
            0.04, 0.90, f"{i + 1}", transform=ax.transAxes,
            fontsize=22, fontweight="bold", color="#d04020"
        )
    plt.tight_layout(rect=[0, 0, 1, 0.92])
    pdf.savefig(fig, dpi=150)
    plt.close()


def page_step(pdf, n, total, payloads, arrows=None, subtitle="", center=None, span=120, elev=22, azim=-55):
    """One assembly step. payloads = list of (verts, facecolors, bounds). arrows = [(start, end), ...]"""
    fig = plt.figure(figsize=(11, 14), dpi=150)
    ax = fig.add_subplot(111, projection="3d")
    for p in payloads:
        add_to_axes(ax, p)
    if arrows:
        for start, end in arrows:
            arrow_3d(ax, start, end)
    if center is None:
        all_verts = np.vstack([p[0].reshape(-1, 3) for p in payloads])
        center = all_verts.mean(axis=0)
    setup_axes(ax, center=center, span=span, elev=elev, azim=azim)
    panel_label(fig, n, total, subtitle=subtitle)
    pdf.savefig(fig, dpi=150)
    plt.close()


def build_comic():
    """Render pages as PNGs first, then concatenate into a small PDF."""
    out = ROOT / "focuser_assembly_comic.pdf"
    total = 8
    pages = []  # list of PNG paths
    with PdfPages(out) as pdf:
        # ---- Page 1: inventory ----
        page_inventory(pdf)

        # ---- Step 1: outer bottom + outer top + 4 bolts ----
        # outer bottom in place; outer top offset upward; 4 bolts above each corner with arrows down
        bottom = load_part("Focuser outer bottom")
        top = load_part("Focuser outer top", transform=translate(0, 0, 40))
        bolts = []
        arrows = []
        for sx, sy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
            x, y = sx * 45, sy * 42
            bolts.append(make_bolt(length=14, radius=2.5, transform=translate(x, y, 80)))
            arrows.append(((x, y, 70), (x, y, 30)))
        # main arrow: top → bottom
        arrows.append(((0, 0, 75), (0, 0, 45)))
        page_step(
            pdf, 1, total,
            [bottom, top, *bolts],
            arrows=arrows,
            subtitle="outer top + outer bottom  +  4× M5×12",
            center=(0, 0, 0), span=90,
        )

        # ---- Step 2: ring on inner ----
        inner = load_part("Focuser inner")
        ring = load_part("Focuser ring", transform=translate(0, 0, 80))
        arrows = [((0, 0, 75), (0, 0, 40))]
        page_step(
            pdf, 2, total,
            [inner, ring],
            arrows=arrows,
            subtitle="ring screwed onto inner",
            center=(0, 0, 30), span=80,
        )

        # ---- Step 3: inner+ring assembly → into outer body ----
        # The full outer body assembled (bottom + top stacked)
        bottom = load_part("Focuser outer bottom")
        top = load_part("Focuser outer top")
        # inner+ring lifted high above
        inner_z = 100
        inner_t = load_part("Focuser inner", transform=translate(0, 0, inner_z))
        ring_t = load_part("Focuser ring", transform=translate(0, 0, inner_z + 30))
        arrows = [((0, 0, inner_z + 60), (0, 0, 20))]
        page_step(
            pdf, 3, total,
            [bottom, top, inner_t, ring_t],
            arrows=arrows,
            subtitle="inner + ring → into outer body",
            center=(0, 0, 30), span=110,
        )

        # ---- Step 4: collet into top of inner ----
        # Simplification: just show "assembled outer body + inner (already in)" + collet coming down
        bottom = load_part("Focuser outer bottom")
        top = load_part("Focuser outer top")
        inner_p = load_part("Focuser inner", transform=translate(0, 0, 10))
        ring_p = load_part("Focuser ring", transform=translate(0, 0, 35))
        collet = load_part("Collet", transform=translate(0, 0, 110))
        arrows = [((0, 0, 105), (0, 0, 50))]
        page_step(
            pdf, 4, total,
            [bottom, top, inner_p, ring_p, collet],
            arrows=arrows,
            subtitle="collet into inner (петалами вверх)",
            center=(0, 0, 30), span=110,
        )

        # ---- Step 5: collet nut on top ----
        bottom = load_part("Focuser outer bottom")
        top = load_part("Focuser outer top")
        inner_p = load_part("Focuser inner", transform=translate(0, 0, 10))
        ring_p = load_part("Focuser ring", transform=translate(0, 0, 35))
        collet_p = load_part("Collet", transform=translate(0, 0, 45))
        nut = load_part("Collet nut", transform=translate(0, 0, 130))
        arrows = [((0, 0, 125), (0, 0, 65))]
        page_step(
            pdf, 5, total,
            [bottom, top, inner_p, ring_p, collet_p, nut],
            arrows=arrows,
            subtitle="collet nut screws on top",
            center=(0, 0, 35), span=110,
        )

        # ---- Step 6: grub panel + grub on the side ----
        bottom = load_part("Focuser outer bottom")
        top = load_part("Focuser outer top")
        inner_p = load_part("Focuser inner", transform=translate(0, 0, 10))
        ring_p = load_part("Focuser ring", transform=translate(0, 0, 35))
        collet_p = load_part("Collet", transform=translate(0, 0, 45))
        nut_p = load_part("Collet nut", transform=translate(0, 0, 55))
        # grub panel offset to +Y direction
        panel = load_part("Focuser grub screw panel", transform=translate(0, 80, 0))
        grub = load_part("Focuser grub", transform=translate(0, 110, 0))
        arrows = [
            ((0, 75, 0), (0, 40, 0)),     # panel → onto side
            ((0, 105, 0), (0, 80, 0)),    # grub → into panel
        ]
        page_step(
            pdf, 6, total,
            [bottom, top, inner_p, ring_p, collet_p, nut_p, panel, grub],
            arrows=arrows,
            subtitle="grub panel + grub → side of body",
            center=(0, 30, 20), span=110,
        )

        # ---- Step 7: 1.25 adapter into top ----
        bottom = load_part("Focuser outer bottom")
        top = load_part("Focuser outer top")
        inner_p = load_part("Focuser inner", transform=translate(0, 0, 10))
        ring_p = load_part("Focuser ring", transform=translate(0, 0, 35))
        collet_p = load_part("Collet", transform=translate(0, 0, 45))
        nut_p = load_part("Collet nut", transform=translate(0, 0, 55))
        panel_p = load_part("Focuser grub screw panel", transform=translate(0, 38, 0))
        grub_p = load_part("Focuser grub", transform=translate(0, 65, 0))
        adapter = load_part("1.25 eyepiece adapter", transform=translate(0, 0, 130))
        arrows = [((0, 0, 125), (0, 0, 75))]
        page_step(
            pdf, 7, total,
            [bottom, top, inner_p, ring_p, collet_p, nut_p, panel_p, grub_p, adapter],
            arrows=arrows,
            subtitle="1.25\" adapter → top of collet",
            center=(0, 15, 35), span=110,
        )

        # ---- Step 8: final assembly + tube + saddle (saddle highlighted) ----
        # Each STL is mostly in its "assembled" native Z position. We only
        # translate the two parts that were stored in print-flat orientation:
        #   collet nut (native Z=-42..-29, needs +92 → +50..+63 on top of inner)
        #   1.25 adapter (native Z=0..47, needs +63 → +63..+110 above collet)
        bottom = load_part("Focuser outer bottom")                            # -42..-5
        top = load_part("Focuser outer top")                                  # -5..+18.4
        inner = load_part("Focuser inner")                                    # -12..+59
        ring = load_part("Focuser ring")                                      # 0..15
        collet = load_part("Collet")                                          # 31..59
        nut = load_part("Collet nut", transform=translate(0, 0, 92))          # → 50..63
        panel = load_part("Focuser grub screw panel")                         # Y=45..54
        grub = load_part("Focuser grub")                                      # native
        adapter = load_part("1.25 eyepiece adapter", transform=translate(0, 0, 63))  # → 63..110

        # Saddle: highlighted orange, exploded down by 10mm for clear visibility
        SADDLE_GAP = 10
        SADDLE_Z = -42 - SADDLE_GAP  # saddle top sits here
        saddle = load_part(
            "Focuser saddle",
            base_color=CLR_NEW,                            # orange highlight
            transform=translate(0, 0, SADDLE_Z),           # native -10.6..0 → -62.6..-52
        )

        # Tube: tangent to saddle bottom at Y=0 (where saddle is thinnest, 2.5mm)
        tube_top = SADDLE_Z - 2.5                          # tangent contact Z
        tube_center_z = tube_top - 129                     # tube radius 129
        tube_mesh = trimesh.creation.cylinder(radius=129, height=200, sections=128)
        rot = trimesh.transformations.rotation_matrix(np.radians(90), [0, 1, 0])
        tube_mesh.apply_transform(rot)
        tube_mesh.apply_translation((0, 0, tube_center_z))
        tube_p = mesh_to_polycoll_data(tube_mesh, (0.85, 0.78, 0.65))

        arrows = [((0, 0, -42), (0, 0, SADDLE_Z + 1))]    # focuser ↓ onto saddle
        page_step(
            pdf, 8, total,
            [tube_p, saddle, bottom, top, inner, ring, collet, nut, panel, grub, adapter],
            arrows=arrows,
            center=(0, 0, 0), span=130, elev=8, azim=-60,
        )

    print(f"Wrote {out}")


if __name__ == "__main__":
    build_comic()
