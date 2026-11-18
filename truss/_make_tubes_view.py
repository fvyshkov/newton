#!/usr/bin/env python3
"""Картинки «как всё вместе» для верхнего яруса v2 НА венце азимут-2 + карта распила.
Венец/кольца — схематично (аннулусы по константам generate_az2), рама/башни — реальные
меши из generate_alt_tower. Трубы раскрашены по типам реза: ноги 534 (оранж),
база перёд/зад 340 (синий), база бок 246 (зелёный).
Выход: print_queue/alt_tower/_TUBES_CUTS_3D.png + _TUBES_TOP.png
Запуск: python3 _make_tubes_view.py
"""
import math, numpy as np, trimesh
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import generate_alt_tower as T
import generate_alt_drive_encoder as E

OUT = T.OUT
WX, APEX_Z, AXIS_H = T.WX, T.APEX_Z, T.AXIS_H
FR, BR, FL, BL = T.FR, T.BR, T.FL, T.BL
apR = np.array([WX, 0, APEX_Z]); apL = np.array([-WX, 0, APEX_Z])

# ---- константы азимута-2 (generate_az2.py) ----
VZ = 17.0            # верх тела венца = z0 рамы (ROT_Z1)
FIX_R = (176., 218.); LIP_R = (180., 185.)          # неподвижное кольцо + буртик
ROT_R = (185.5, 217.5)                              # тело венца z9..17
RIM_R = (217.5, 226.); RIM_Z = (9., 19.)            # зубчатый обод 224T (на 2 выше тела!)

C_LEG  = [232, 129, 42, 255]     # ноги 534
C_FB   = [43, 125, 232, 255]     # база перёд/зад 340
C_SIDE = [43, 181, 115, 255]     # база бок 246

def tube(p0, p1, r=11., col=None, seg=24):
    p0 = np.array(p0, float); p1 = np.array(p1, float); v = p1 - p0; L = np.linalg.norm(v)
    c = trimesh.creation.cylinder(radius=r, height=L, sections=seg)
    M = trimesh.geometry.align_vectors([0, 0, 1], v / L); M[:3, 3] = (p0 + p1) / 2
    c.apply_transform(M); return c

def disc(c, r, w, ax='x', seg=48):
    cc = trimesh.creation.cylinder(radius=r, height=w, sections=seg)
    M = trimesh.geometry.align_vectors([0, 0, 1], {'x': [1, 0, 0], 'z': [0, 0, 1]}[ax])
    M[:3, 3] = c; cc.apply_transform(M); return cc

def ann(r0, r1, z0, z1, seg=128):
    a = trimesh.creation.annulus(r_min=r0, r_max=r1, height=z1 - z0, sections=seg)
    a.apply_translation([0, 0, (z0 + z1) / 2]); return a

def zshift(m, dz=VZ):
    m = m.copy(); m.apply_translation([0, 0, dz]); return m

def boxm(x0, x1, y0, y1, z0, z1):
    b = trimesh.creation.box((x1 - x0, y1 - y0, z1 - z0))
    b.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2]); return b

print("детали рамы/башен (реальные меши)…")
frame = [
    ("башня R", zshift(T.build(+1, assemble=True)), [51, 133, 204, 255]),
    ("башня L", zshift(T.build(-1, assemble=True)), [90, 170, 230, 255]),
    ("угол FR", zshift(T.ground_node(FR, apR, [FL, BR], "c", assemble=True)), [150, 110, 70, 255]),
    ("угол BR", zshift(T.ground_node(BR, apR, [BL, FR], "c", assemble=True)), [150, 110, 70, 255]),
    ("угол FL", zshift(T.ground_node(FL, apL, [FR, BL], "c", assemble=True)), [170, 125, 80, 255]),
    ("угол BL", zshift(T.ground_node(BL, apL, [BR, FL], "c", assemble=True)), [170, 125, 80, 255]),
    ("энкодер", zshift(E.encoder_arm(+1, assemble=True)), [140, 90, 200, 255]),
    ("мотор",   zshift(E.motor_mount(+1, assemble=True)), [225, 120, 60, 255]),
]
# перемычки НЕТ (2026-07-23): жёсткость вбок дают щёчки седла (пара колёс) +
# косынки углов (generate_alt_corner_gusset) — распил остаётся 8 отрезков.
import generate_alt_corner_gusset as G
_gb = G.gusset_local()
for _nm, _cn, _ap, _b, _ in G.CORNERS:
    frame.append((f"косынка {_nm}", zshift(G.place(_gb, _cn, _ap, _b)[0]), [39, 174, 96, 255]))
tubes = [
    ("нога FR", zshift(tube(FR, apR)), C_LEG), ("нога BR", zshift(tube(BR, apR)), C_LEG),
    ("нога FL", zshift(tube(FL, apL)), C_LEG), ("нога BL", zshift(tube(BL, apL)), C_LEG),
    ("база перёд", zshift(tube(FR, FL)), C_FB), ("база зад", zshift(tube(BR, BL)), C_FB),
    ("база бок R", zshift(tube(FR, BR)), C_SIDE), ("база бок L", zshift(tube(FL, BL)), C_SIDE),
]
wheels = [
    ("колесо R", zshift(disc((WX, 0, AXIS_H), 100, 15)), [60, 60, 66, 255]),
    ("колесо L", zshift(disc((-WX, 0, AXIS_H), 100, 15)), [60, 60, 66, 255]),
]
az2 = [
    ("фанера", ann(0.1, 265, -12, 0, 96), [205, 178, 132, 255]),
    ("непод. кольцо", ann(*FIX_R, 0, 8), [160, 165, 175, 255]),
    ("буртик", ann(*LIP_R, 8, 17), [160, 165, 175, 255]),
    ("венец: тело", ann(*ROT_R, 9, 17), [120, 128, 140, 255]),
    ("венец: зубья 224T", ann(*RIM_R, *RIM_Z), [70, 74, 84, 255]),
    ("шестерня 16T", disc((0, -240, 14), 18, 10, ax='z'), [232, 129, 42, 255]),
    ("подставка: плита", boxm(-40, 40, -276, -220, 24, 30), [235, 190, 150, 255]),
    ("NEMA17 азимута", boxm(-21, 21, -269, -227, 30, 70), [200, 160, 120, 255]),
    ("вал", disc((0, -240, 22), 2.6, 18, ax='z'), [120, 120, 120, 255]),
]
for sy in (-1, 1):
    for sx in (-1, 1):
        az2.append(("нога подставки", disc((sx * 32, -248 + sy * 22, 12), 5, 24, ax='z'),
                    [235, 190, 150, 255]))
# спайдер магнита (лучи 120/210/300 к бобышкам R196) + колонна энкодера
for a in (120, 210, 300):
    d = np.array([math.cos(math.radians(a)), math.sin(math.radians(a)), 0])
    az2.append(("спайдер", tube(d * 12 + [0, 0, 19], d * 196 + [0, 0, 19], r=5, seg=12),
                [150, 100, 210, 255]))
az2.append(("колонна энкодера", disc((0, 0, 6.5), 20, 13, ax='z'), [150, 100, 210, 255]))

# призрак ОТА в зените: ящик Ø300 свисает 500 ниже оси, между ногами — ЕЛЕ ЗАМЕТНЫЙ
zbox = AXIS_H - 500 + 42 + VZ
ghost = [("зерк. ящик (зенит)", disc((0, 0, zbox), 150, 85, ax='z', seg=64), [110, 110, 118, 55]),
         ("труба OTA", tube((0, 0, zbox + 42), (0, 0, 985), 120, seg=64), [180, 185, 192, 28])]

ALL = az2 + frame + tubes + wheels

def draw(ax, items, lw=0.05):
    """ВСЕ детали одной Poly3DCollection с пофейсовыми RGBA: глобальная сортировка
    граней по глубине → честные перекрытия (иначе фанера красится поверх венца)."""
    polys, cols = [], []
    for nm, m, col in items:
        polys.append(m.vertices[m.faces])
        cols.append(np.tile(np.array(col, float) / 255, (len(m.faces), 1)))
    coll = Poly3DCollection(np.concatenate(polys), facecolors=np.concatenate(cols),
                            edgecolor="none", zsort="average")
    ax.add_collection3d(coll)

LBL = dict(facecolor="white", alpha=0.78, edgecolor="none", pad=2)

# ================= рис. 1 — два вида полной сборки =================
fig = plt.figure(figsize=(19, 11.5))
for i, (elev, azim, ttl) in enumerate([
        (16, -58, "ВСЁ ВМЕСТЕ: фанера → кольца азимут-2 → венец 224T → 4 угла → ноги → башни → колёса"),
        (4, -90, "спереди: ящик Ø300 (серый призрак) проходит между ногами x=±170")]):
    ax = fig.add_subplot(1, 2, i + 1, projection="3d")
    ax.set_facecolor("white"); draw(ax, ALL + ghost)
    ax.set_box_aspect((1, 1, 1.84)); ax.set_xlim(-280, 280); ax.set_ylim(-280, 280); ax.set_zlim(-30, 1000)
    ax.view_init(elev=elev, azim=azim); ax.set_axis_off()
    ax.set_title(ttl, fontsize=12, fontweight="bold")
    if i == 0:
        leg = (FR + apR) / 2 + [0, 0, VZ]
        ax.text(leg[0] + 45, leg[1] + 70, leg[2] + 30, "ноги 534 ×4", color="#b35b10",
                fontsize=14, fontweight="bold", bbox=LBL)
        ax.text(40, 260, VZ + 15, "база перёд/зад 340 ×2", color="#1b5cb8",
                fontsize=12, fontweight="bold", bbox=LBL)
        ax.text(260, -190, VZ + 45, "база бок 246 ×2", color="#1e8a56",
                fontsize=12, fontweight="bold", bbox=LBL)
        ax.text(-175, -270, 110, "венец 224T (вращается)\n+ шестерня ← NEMA17", color="#222",
                fontsize=11, ha="center", bbox=LBL)
        ax.text(-250, 0, AXIS_H + VZ + 55, "колесо Ø200", color="#333", fontsize=11, ha="right", bbox=LBL)
        ax.text(-250, 0, APEX_Z + VZ - 60, "башня + V-седло", color="#1b5cb8", fontsize=11, ha="right", bbox=LBL)
        ax.text(285, 40, -28, "фанера", color="#8a6d3b", fontsize=11, bbox=LBL)
    else:
        ax.text(0, -140, VZ + 40, "косынки углов: жёсткость вбок\n(гильзы на ногу + продольную базу)",
                color="#1d7a44", fontsize=11, fontweight="bold", ha="center", bbox=LBL)
fig.patch.set_facecolor("white"); plt.tight_layout()
plt.savefig(OUT / "_TUBES_CUTS_3D.png", dpi=110, facecolor="white"); plt.close(fig)
print("→ _TUBES_CUTS_3D.png")

# ================= рис. 2 — вид сверху нижнего яруса =================
low = az2 + [it for it in frame if "угол" in it[0] or "косынка" in it[0]] + \
      [(nm, m, c) for nm, m, c in tubes if "база" in nm]
for nm, p0, p1, c in [("нога FR", FR, apR, C_LEG), ("нога BR", BR, apR, C_LEG),
                      ("нога FL", FL, apL, C_LEG), ("нога BL", BL, apL, C_LEG)]:
    d = (p1 - p0) / np.linalg.norm(p1 - p0)
    low.append((nm, zshift(tube(p0, p0 + d * 150)), c))            # огрызки ног вверх

fig = plt.figure(figsize=(12, 12)); ax = fig.add_subplot(111, projection="3d")
ax.set_facecolor("white"); draw(ax, low, lw=0.08)
ax.set_box_aspect((1, 1, 0.22)); ax.set_xlim(-290, 290); ax.set_ylim(-290, 290); ax.set_zlim(-15, 175)
ax.view_init(elev=88, azim=-90); ax.set_axis_off()
ax.set_title("ВИД СВЕРХУ: ноги приходят НЕ в венец, а в 4 угла; углы (пятки на R210) стоят на венце,\n"
             "прямоугольник базы 340×246 держит их от раскрытия; центр перёд↔зад ОТКРЫТ под ящик",
             fontsize=12, fontweight="bold")
ax.text(0, 128, 60, "база 340", color="#1b5cb8", fontsize=13, fontweight="bold", ha="center", bbox=LBL)
ax.text(0, -150, 60, "база 340", color="#1b5cb8", fontsize=13, fontweight="bold", ha="center", bbox=LBL)
ax.text(148, 40, 60, "бок 246", color="#1e8a56", fontsize=13, fontweight="bold", bbox=LBL)
ax.text(-148, 40, 60, "бок 246", color="#1e8a56", fontsize=13, fontweight="bold", ha="right", bbox=LBL)
for cn in (FR, BR, FL, BL):
    ax.text(cn[0] * 1.32, cn[1] * 1.35, 40, "нога ↑", color="#b35b10", fontsize=11, fontweight="bold",
            ha="center", bbox=LBL)
ax.text(30, -55, 40, "центр открыт", color="#555", fontsize=12, bbox=LBL)
ax.text(0, -287, 100, "NEMA17 + шестерня 16T (на фанере, крутит венец)", color="#333",
        fontsize=10, ha="center", bbox=LBL)
th = math.radians(30)
ax.text(250 * math.cos(th), 250 * math.sin(th), 40, "зубья венца 224T", color="#222", fontsize=10, bbox=LBL)
fig.patch.set_facecolor("white"); plt.tight_layout()
plt.savefig(OUT / "_TUBES_TOP.png", dpi=110, facecolor="white"); plt.close(fig)
print("→ _TUBES_TOP.png")
