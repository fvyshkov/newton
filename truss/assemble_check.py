#!/usr/bin/env python3
"""
assemble_check.py — VIRTUAL ASSEMBLY of the full tube-rocker in WORLD space.

Builds every printed node in world coordinates (bypassing the print-bed
reorientation of each generator), drops in the Ø22 tubes between mating
sockets, adds the Ø200 altitude wheels + drives, then runs a collision / fit
diagnosis and renders the whole frame as one shaded image.

This is a DIAGNOSIS script — it does NOT export/overwrite any printed STL and
does NOT modify the generators (it monkey-patches finish/to_bed IN MEMORY so the
build functions hand back their pre-reorientation, world-coordinate mesh).

Outputs:
  • assembly_full.png   — iso / front / top / side shaded render
  • a printed collision/fit table + concrete problem list
"""
import math
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).parent
ENGINE = "manifold"

# ----------------------------------------------------------------------------
# 1.  Import generators and PATCH them so build functions return WORLD meshes.
#     (finish/to_bed normally reorient to the print bed + drop z_min=0 + export)
# ----------------------------------------------------------------------------
import gen_rocker_comic as W
import generate_rocker_frame_truss as FR
import generate_rocker_ground_truss as GND
import generate_rocker_towers as TW


def _clean(mesh):
    """Weld + validate + keep the largest body (same cleanup finish() does) —
    but NO reorientation, NO z-drop, NO export."""
    mesh.merge_vertices(digits_vertex=5)
    mesh.process(validate=True)
    parts = mesh.split(only_watertight=False)
    if len(parts) > 1:
        mesh = max(parts, key=lambda m: abs(m.volume))
    return mesh


# frame: build in world -> to_bed(part, yaw) -> finish(part, name)
FR.to_bed = lambda part, T=None: part
FR.finish = lambda mesh, name: _clean(mesh)
FR.tube_fit_test = lambda *a, **k: True
# ground: build in world -> finish(part, name, reorient=...)  (reorient+zdrop inside)
GND.finish = lambda mesh, name, reorient=None: _clean(mesh)
GND.run_tube_fit = lambda *a, **k: True
# towers: build in world(apex) / local-print(cradle,drive) -> finish(part, name, pose=...)
TW.finish = lambda mesh, name, pose=None: _clean(mesh)
TW.tube_fit_test = lambda *a, **k: True
TW.tube_fit = lambda *a, **k: True
TW.seat_enclosure_test = lambda *a, **k: True


# ----------------------------------------------------------------------------
# transforms
# ----------------------------------------------------------------------------
def rotz(deg):
    return trimesh.transformations.rotation_matrix(math.radians(deg), [0, 0, 1])


def roty(deg):
    return trimesh.transformations.rotation_matrix(math.radians(deg), [0, 1, 0])


def tr(x, y, z):
    M = np.eye(4)
    M[:3, 3] = (x, y, z)
    return M


def placed(mesh, *mats):
    m = mesh.copy()
    for M in mats:
        m.apply_transform(M)
    return m


# ----------------------------------------------------------------------------
# World coordinates (from gen_rocker_comic)
# ----------------------------------------------------------------------------
FRAME_Z = W.FRAME_Z          # 75
R_CORNER = W.R_CORNER        # 210
WHEEL_X = W.WHEEL_X          # 170
APEX_Z = W.APEX_Z            # 530
Z_ARM = GND.Z_ARM            # 32 (ground tube axis)


def corner_xyz(a):
    return np.array(W.polar(R_CORNER, a, FRAME_Z), float)


def mid(a, b):
    return (corner_xyz(a) + corner_xyz(b)) / 2.0


C30, C150, C270 = corner_xyz(30), corner_xyz(150), corner_xyz(270)
M_AB, M_BC, M_CA = mid(30, 150), mid(150, 270), mid(270, 30)
CENTER = np.array([0.0, 0.0, FRAME_Z])
APEX_R = np.array([WHEEL_X, 0.0, APEX_Z])
APEX_L = np.array([-WHEEL_X, 0.0, APEX_Z])
WHEEL_AXIS_Z = W.ALT_AXIS[2]          # 590

# ground legs (leg core = tube outer terminal R285) & hub center
R_LEG = GND.R_TUBE_OUT                # 285
R_HUB_IN = GND.R_TUBE_IN              # 35
LEG = {a: np.array(W.polar(R_LEG, a, Z_ARM)) for a in (30, 150, 270)}
HUB0 = np.array([0.0, 0.0, Z_ARM])


# ----------------------------------------------------------------------------
# 2.  BUILD ALL NODE BODIES IN WORLD COORDINATES
# ----------------------------------------------------------------------------
print("Building node bodies in world coordinates (CSG, this takes a moment)...")
nodes = {}

# --- rotating frame ---
nodes["corner_30"] = FR.corner_node(30)
nodes["corner_150"] = FR.corner_node(150)
nodes["corner_drive_270"] = FR.corner_node(270, drive=True)
_mid = FR.midchord_node()                       # built at M_AB
nodes["mid_AB"] = _mid
nodes["mid_BC"] = placed(_mid, rotz(120))       # M_AB -> M_BC
nodes["mid_CA"] = placed(_mid, rotz(240))       # M_AB -> M_CA
nodes["center"] = FR.center_node()

# --- ground star ---
nodes["hub"] = GND.rocker_hub_truss()           # built at origin, z=32 (world)
_leg = GND.rocker_leg_truss()                   # built on +X (ang 0)
_sad = GND.rocker_ring_saddle_tube()            # built on +X (ang 0), world (reorient skipped)
for a in (30, 150, 270):
    nodes[f"leg_{a}"] = placed(_leg, rotz(a))
    nodes[f"saddle_{a}"] = placed(_sad, rotz(a))

# --- towers / cradles / alt drive ---
nodes["apex_R"] = placed(TW.rocker_tower_apex(+1, "Rocker_tower_apex_R"), tr(WHEEL_X, 0, APEX_Z))
nodes["apex_L"] = placed(TW.rocker_tower_apex(-1, "Rocker_tower_apex_L"), tr(-WHEEL_X, 0, APEX_Z))
# cradle/alt_drive built in local print frame: local +Z = world +X  ->  roty(90) FIRST
# (orient local->world), THEN translate onto the cross tube.
nodes["cradle_R"] = placed(TW.rocker_cradle(+1, "Rocker_cradle_R"), roty(90), tr(WHEEL_X, 0, APEX_Z))
nodes["cradle_L"] = placed(TW.rocker_cradle(-1, "Rocker_cradle_L"), roty(90), tr(-WHEEL_X, 0, APEX_Z))
nodes["alt_drive"] = placed(TW.rocker_alt_drive("Rocker_alt_drive"), roty(90), tr(WHEEL_X, 0, APEX_Z))

for k, v in nodes.items():
    v.metadata["name"] = k
print(f"  built {len(nodes)} node bodies.")


# ----------------------------------------------------------------------------
# 3.  TUBES  (Ø22 cylinders, core-to-core / per tube_cut_list.md)
#     each: id -> (p1, p2, {target node names}, {allowed pass-through names})
# ----------------------------------------------------------------------------
TUBE_R = 11.0
tubes = {}


def T(tid, p1, p2, targets, passthru=()):
    tubes[tid] = dict(p1=np.asarray(p1, float), p2=np.asarray(p2, float),
                      targets=set(targets), passthru=set(passthru))


# half-chords corner->midchord ×6
T("halfchord_30-AB", C30, M_AB, ["corner_30", "mid_AB"])
T("halfchord_150-AB", C150, M_AB, ["corner_150", "mid_AB"])
T("halfchord_150-BC", C150, M_BC, ["corner_150", "mid_BC"])
T("halfchord_270-BC", C270, M_BC, ["corner_drive_270", "mid_BC"])
T("halfchord_270-CA", C270, M_CA, ["corner_drive_270", "mid_CA"])
T("halfchord_30-CA", C30, M_CA, ["corner_30", "mid_CA"])
# radials center->midchord ×3
T("radial_C-AB", CENTER, M_AB, ["center", "mid_AB"])
T("radial_C-BC", CENTER, M_BC, ["center", "mid_BC"])
T("radial_C-CA", CENTER, M_CA, ["center", "mid_CA"])
# tower legs ×4
T("towerleg_30-apexR", C30, APEX_R, ["corner_30", "apex_R"])
T("towerleg_150-apexL", C150, APEX_L, ["corner_150", "apex_L"])
T("towerleg_270-apexR", C270, APEX_R, ["corner_drive_270", "apex_R"])
T("towerleg_270-apexL", C270, APEX_L, ["corner_drive_270", "apex_L"])
# cross tube ×1 (slides through both cradles + the alt-drive lug)
T("cross_apexR-apexL", APEX_R, APEX_L, ["apex_R", "apex_L"],
  passthru=["cradle_R", "cradle_L", "alt_drive"])
# ground radials hub->leg ×3 (pass through the ring saddle clamp)
for a in (30, 150, 270):
    pin = np.array(W.polar(R_HUB_IN, a, Z_ARM))
    T(f"ground_hub-leg_{a}", pin, LEG[a], ["hub", f"leg_{a}"], passthru=[f"saddle_{a}"])


def tube_mesh(td, r=TUBE_R, seg=24):
    return trimesh.creation.cylinder(radius=r, segment=[td["p1"], td["p2"]], sections=seg)


# ----------------------------------------------------------------------------
# 4.  WHEELS Ø200×15 (axis X) + rough drives
# ----------------------------------------------------------------------------
def disc(x_sign):
    m = trimesh.creation.cylinder(radius=100.0, height=15.0, sections=48)
    m.apply_transform(roty(90))                              # axis -> X
    m.apply_transform(tr(x_sign * WHEEL_X, 0, WHEEL_AXIS_Z))
    return m


wheels = {"wheel_R": disc(+1), "wheel_L": disc(-1)}
# rough azimuth pinion + alt friction roller (for the render / rough drives)
pinion = trimesh.creation.cylinder(radius=18, height=14, sections=24)
pinion.apply_transform(tr(0, -W.PINION_R, 50))
roller = placed(TW.rocker_alt_roller("Rocker_alt_roller"), roty(90), tr(WHEEL_X, 0, 472.5))


# ----------------------------------------------------------------------------
# 5.  COLLISION / FIT CHECK
# ----------------------------------------------------------------------------
def bbox_overlap(a, b, pad=1.0):
    la, ha = a.bounds
    lb, hb = b.bounds
    return all(ha[i] + pad >= lb[i] and hb[i] + pad >= la[i] for i in range(3))


def inter_vol(a, b):
    """Volume (mm^3) of the boolean intersection, 0 if disjoint/empty."""
    if not bbox_overlap(a, b):
        return 0.0
    try:
        it = trimesh.boolean.intersection([a, b], engine=ENGINE)
    except Exception:
        return float("nan")
    if it is None or len(it.faces) == 0:
        return 0.0
    return abs(it.volume)


# grip probe: annular shell (r 11.5..14.5) around the tube axis; its intersection
# volume with a node measures the axial length over which node WALL surrounds the
# tube = engagement / grip depth.  grip_mm = vol / ring_area.
GRIP_RIN, GRIP_ROUT = 11.5, 14.5
GRIP_AREA = math.pi * (GRIP_ROUT ** 2 - GRIP_RIN ** 2)      # mm^2


def grip_mm(node, td):
    outer = trimesh.creation.cylinder(radius=GRIP_ROUT, segment=[td["p1"], td["p2"]], sections=32)
    inner = trimesh.creation.cylinder(radius=GRIP_RIN, segment=[td["p1"], td["p2"]], sections=32)
    ring = trimesh.boolean.difference([outer, inner], engine=ENGINE)
    if not bbox_overlap(ring, node):
        return 0.0
    try:
        it = trimesh.boolean.intersection([ring, node], engine=ENGINE)
    except Exception:
        return float("nan")
    if it is None or len(it.faces) == 0:
        return 0.0
    return abs(it.volume) / GRIP_AREA


COLLIDE_MM3 = 250.0        # solid tube ∩ wrong node > this  -> real collision
GRIP_FAIL, GRIP_MARG = 8.0, 20.0

print("\nRunning fit / collision checks (booleans)...")
tube_rows = []
for tid, td in tubes.items():
    tm = tube_mesh(td)
    grips = {}
    for tgt in sorted(td["targets"]):
        grips[tgt] = grip_mm(nodes[tgt], td)
    passgr = {}
    for pt in sorted(td["passthru"]):
        passgr[pt] = grip_mm(nodes[pt], td)
    collisions = []
    allow = td["targets"] | td["passthru"]
    for nname, nmesh in nodes.items():
        if nname in allow:
            continue
        v = inter_vol(tm, nmesh)
        if v > COLLIDE_MM3:
            collisions.append((nname, v))
    tube_rows.append((tid, grips, passgr, collisions))

# node-node overlaps (nodes should only touch via tubes)
print("Running node-node overlap checks...")
nlist = list(nodes.items())
node_overlaps = []
for i in range(len(nlist)):
    for j in range(i + 1, len(nlist)):
        na, ma = nlist[i]
        nb, mb = nlist[j]
        if not bbox_overlap(ma, mb, pad=0.0):
            continue
        v = inter_vol(ma, mb)
        if v > COLLIDE_MM3:
            node_overlaps.append((na, nb, v))

# wheel checks (level pose) + swept-OTA envelope vs cross/towers
print("Running wheel / swing checks...")
wheel_hits = []
struct_for_wheel = dict(nodes)
struct_for_wheel.update({f"tube:{k}": tube_mesh(v) for k, v in tubes.items()})
for wn, wm in wheels.items():
    for sn, sm in struct_for_wheel.items():
        v = inter_vol(wm, sm)
        if v > COLLIDE_MM3:
            wheel_hits.append((wn, sn, v))

# swept OTA envelope: mirror-box tube Ø300 x length spanning the wheels, rotated
# about the ALT axis (world X through (0,y=0,z=590)); flag min clearance to cross
def ota_swept_min_clearance():
    axis_z = WHEEL_AXIS_Z
    cross = tube_mesh(tubes["cross_apexR-apexL"])
    legs = [tube_mesh(tubes[k]) for k in tubes if k.startswith("towerleg")]
    worst = ("", 0.0)          # (label, biggest interference volume mm^3)
    for ang in range(0, 91, 15):
        # OTA modelled as a Ø300 cylinder, axis along the tilted optical direction
        d = np.array([0.0, math.cos(math.radians(ang)), math.sin(math.radians(ang))])
        p1 = np.array([0, 0, axis_z]) - d * 420
        p2 = np.array([0, 0, axis_z]) + d * 420
        ota = trimesh.creation.cylinder(radius=150.0, segment=[p1, p2], sections=24)
        for label, mesh in [("cross", cross)] + [(f"towerleg{i}", m) for i, m in enumerate(legs)]:
            v = inter_vol(ota, mesh)
            if v > COLLIDE_MM3 and v > worst[1]:
                worst = (f"tilt {ang}° vs {label}", v)
    return worst


ota_worst = ota_swept_min_clearance()

# analytic roller-vs-wheel engagement (Ø200 wheel vs roller ring radius)
ROLL_R_FROM_AXIS = math.hypot(TW.ROLL_Y, TW.ROLL_DZ)     # roller center dist from alt axis
roller_gap = ROLL_R_FROM_AXIS - 100.0 - 0.0              # to wheel rim R100 (roller Ø35 -> r17.5)
roller_surface_gap = ROLL_R_FROM_AXIS - 17.5 - 100.0     # roller OUTER surface vs wheel rim


# ----------------------------------------------------------------------------
# 6.  RENDER
# ----------------------------------------------------------------------------
def render():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    def shade(mesh, base):
        tri = mesh.vertices[mesh.faces]
        n = mesh.face_normals
        light = np.array([0.4, 0.3, 1.0]); light /= np.linalg.norm(light)
        inten = np.clip(0.40 + 0.60 * (n @ light), 0.25, 1.0)
        base = np.array(base)
        fc = (base[None, :] * inten[:, None]).clip(0, 1)
        return tri, fc

    groups = []
    for m in nodes.values():
        groups.append(shade(m, (0.95, 0.55, 0.25)))          # nodes orange
    for td in tubes.values():
        groups.append(shade(tube_mesh(td), (0.62, 0.64, 0.68)))   # tubes grey
    for m in wheels.values():
        groups.append(shade(m, (0.20, 0.20, 0.22)))
    groups.append(shade(pinion, (0.30, 0.30, 0.33)))
    groups.append(shade(roller, (0.30, 0.30, 0.33)))

    allv = np.vstack([g[0].reshape(-1, 3) for g in groups])
    lo, hi = allv.min(0), allv.max(0)
    ctr = (lo + hi) / 2
    span = (hi - lo).max() * 0.56

    views = [("iso", 18, -60), ("front", 6, -90), ("top", 88, -90), ("side", 6, 0)]
    fig = plt.figure(figsize=(16, 15), dpi=120)
    for i, (name, elev, azim) in enumerate(views):
        ax = fig.add_subplot(2, 2, i + 1, projection="3d")
        ax.computed_zorder = False
        tri = np.vstack([g[0] for g in groups])
        fc = np.vstack([g[1] for g in groups])
        pc = Poly3DCollection(tri, facecolors=fc, edgecolor="none", linewidth=0)
        pc.set_rasterized(True)
        ax.add_collection3d(pc)
        ax.set_xlim(ctr[0] - span, ctr[0] + span)
        ax.set_ylim(ctr[1] - span, ctr[1] + span)
        ax.set_zlim(ctr[2] - span, ctr[2] + span)
        ax.set_box_aspect((1, 1, 1))
        ax.view_init(elev=elev, azim=azim)
        ax.set_title(name, fontsize=15)
        ax.set_axis_off()
    fig.suptitle("Tube-rocker virtual assembly (world space) — nodes orange, tubes grey, wheels dark",
                 fontsize=15)
    fig.tight_layout()
    out = ROOT / "assembly_full.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return out


render_path = render()


# ----------------------------------------------------------------------------
# 7.  REPORT
# ----------------------------------------------------------------------------
def gflag(g):
    if g != g:            # nan
        return "ERR"
    if g < GRIP_FAIL:
        return "FAIL"
    if g < GRIP_MARG:
        return "MARG"
    return "OK"


print("\n" + "=" * 78)
print("TUBE FIT / COLLISION TABLE")
print("=" * 78)
print(f"{'tube id':26s} {'target sockets (grip mm)':34s} collides with?")
print("-" * 78)
problems = []
for tid, grips, passgr, coll in tube_rows:
    gtxt = "  ".join(f"{t.split('_')[-1] if False else t}={g:.0f}[{gflag(g)}]" for t, g in grips.items())
    ptxt = ""
    if passgr:
        ptxt = "  (thru: " + ", ".join(f"{p}={g:.0f}" for p, g in passgr.items()) + ")"
    ctxt = "none" if not coll else ", ".join(f"{n}:{v/1000:.1f}cm3" for n, v in coll)
    print(f"{tid:26s} {gtxt}")
    if ptxt:
        print(f"{'':26s} {ptxt}")
    print(f"{'':26s} collide -> {ctxt}")
    for t, g in grips.items():
        if g < GRIP_MARG:
            problems.append(f"[{gflag(g)}] tube '{tid}' engages node '{t}' only {g:.0f} mm "
                            f"(clamp grip target ~40 mm)")
    for n, v in coll:
        problems.append(f"[COLLISION] tube '{tid}' passes through node '{n}' "
                        f"({v/1000:.1f} cm^3 of solid overlap)")

print("\n" + "=" * 78)
print("NODE-NODE OVERLAPS (nodes should touch only through tubes)")
print("=" * 78)
if not node_overlaps:
    print("  none")
else:
    for na, nb, v in node_overlaps:
        print(f"  {na} <-> {nb} : {v/1000:.2f} cm^3 overlap")
        problems.append(f"[NODE OVERLAP] '{na}' and '{nb}' bodies overlap {v/1000:.2f} cm^3")

print("\n" + "=" * 78)
print("WHEEL / SWING")
print("=" * 78)
if not wheel_hits:
    print("  wheels clear of frame at level pose")
else:
    for wn, sn, v in wheel_hits:
        print(f"  {wn} intersects {sn} : {v/1000:.2f} cm^3")
        problems.append(f"[WHEEL] '{wn}' intersects '{sn}' at level pose ({v/1000:.2f} cm^3)")
print(f"  roller ring radius from alt axis = {ROLL_R_FROM_AXIS:.1f} mm; Ø200 wheel rim = 100 mm")
print(f"    -> roller-center-to-rim gap {roller_gap:+.1f} mm; "
      f"roller-surface(Ø35)-to-rim gap {roller_surface_gap:+.1f} mm "
      f"({'INTERFERENCE' if roller_surface_gap < 0 else 'GAP (no contact)'})")
if roller_surface_gap > 1.0:
    problems.append(f"[ALT ROLLER] friction/support rollers sit {roller_surface_gap:.1f} mm "
                    f"OFF the Ø200 wheel rim (rollers placed for ~Ø{2*(ROLL_R_FROM_AXIS-17.5):.0f})")
elif roller_surface_gap < -1.0:
    problems.append(f"[ALT ROLLER] rollers over-penetrate the Ø200 wheel rim by "
                    f"{-roller_surface_gap:.1f} mm")
if ota_worst[0]:
    print(f"  swept OTA(Ø300) envelope worst interference: {ota_worst[0]} "
          f"({ota_worst[1]/1000:.1f} cm^3)  [approximate proxy]")
    problems.append(f"[OTA SWING, approx] Ø300 OTA envelope interferes at {ota_worst[0]}")
else:
    print("  swept OTA(Ø300) envelope: no cross/tower interference over 0-90° tilt")

print("\n" + "=" * 78)
print("CONCRETE PROBLEMS FOUND")
print("=" * 78)
if not problems:
    print("  none — assembly fits, all tubes seat, nothing collides.")
else:
    for p in problems:
        print("  - " + p)

print(f"\nRender written -> {render_path}")
