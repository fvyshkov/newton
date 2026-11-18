#!/usr/bin/env python3
"""КОСЫНКИ УГЛОВ РАМЫ — жёсткость верхнего яруса ВБОК (X-Z параллелограмм).

Зачем: каждая башня — треугольник в СВОЕЙ плоскости x=±170: вдоль Y-Z жёстко,
а вбок (X) обе башни качаются на изгибе гнёзд — параллелограмм. Раскосы между
башнями НЕВОЗМОЖНЫ: выше z≈170 весь центр метёт телескоп (в зените труба Ø240
стоит между башнями; зад-низ метут труба+ящик до радиуса 522 от оси). Свободна
только зона углов (z<130) — там и триангулируем: косынка жёстко связывает НОГУ
с ПРОДОЛЬНОЙ (вдоль X) базовой трубкой, диагональная плита лежит в плоскости
ноги и трубки ≈ X-Z → гасит именно параллелограмм. Верхнюю связь башен даёт сам
телескоп: щёчки v2 пленят фланцы колёс (база 340), анти-раскрытие оттуда же.

Конструкция: 2 ГИЛЬЗЫ (бор Ø22.4, стенка ~7, БЕЗ прорези — момент передаётся
упором бора в трубу, стяжка не нужна) + плита-раскос 8мм. Фиксация от сползания:
по 1 радиальному отверстию Ø3.4 под самонарез M4 в дальнем конце гильзы.
Надеваются на трубки при сборке (насквозь), болты не нужны.
Гильзы на s=55..115 от узла — хомуты угла (0..46) и их болты не задеты.
Печать: плитой плашмя (низ гильз подрезан флэтом), боры горизонтально
с teardrop-сводом → без поддержек. 4 шт: FR/BR/FL/BL.
Запуск: /opt/homebrew/bin/python3 generate_alt_corner_gusset.py
"""
import math
from pathlib import Path
import numpy as np
import trimesh
from shapely.geometry import Polygon
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import tube_clamp as tc
import generate_alt_tower as T

OUT = T.OUT
ENGINE = "manifold"

S0, S1 = 55.0, 115.0          # гильзы вдоль трубок, мм от узла (хомут угла: 0..46)
SLEEVE_R = 18.0               # наружный R гильзы (бор 22.4 → стенка 6.8)
WEB_T = 8.0                   # толщина плиты-раскоса
WEB_NEAR = 72.0               # ближняя диагональ плиты (зазор к ушам/болтам узла)
FLAT_Z = -14.0                # подрез низа гильз (пятно на столе в позе печати)
SCREW_S = 108.0               # позиция самонареза M4 (от узла)

OPEN_HALF = 65.0              # C-раскрытие гильзы базовой трубки, ±° от низа (−Y лок.)
                              # низ гильзы иначе нырял бы до z=−5 под плоскость фет;
                              # с раскрытием ±65° материал не ниже z≈2 (губы держат трубу)

apR = np.array([T.WX, 0, T.APEX_Z]); apL = np.array([-T.WX, 0, T.APEX_Z])
# угол: (имя, узел, апекс своей башни, продольная трубка, соседи для проверки)
CORNERS = [
    ("FR", T.FR, apR, np.array([-1.0, 0, 0]), [T.FL, T.BR]),
    ("FL", T.FL, apL, np.array([+1.0, 0, 0]), [T.FR, T.BL]),
    ("BR", T.BR, apR, np.array([-1.0, 0, 0]), [T.BL, T.FR]),
    ("BL", T.BL, apL, np.array([+1.0, 0, 0]), [T.BR, T.FL]),
]


def prism(poly_pts, axis, span, plane_map):
    """Экструзия полигона вдоль оси с переустановкой осей. plane_map: матрица 4×4."""
    p = trimesh.creation.extrude_polygon(Polygon(poly_pts), span[1]-span[0])
    M = plane_map.copy(); M[:3, 3] += M[:3, 2]*span[0]
    p.apply_transform(M)
    if p.volume < 0: p.invert()
    return p


def gusset_local():
    """Локальная рама: X = вдоль базовой трубки, Y = вдоль ноги, Z = нормаль плиты."""
    br = tc.BORE/2
    def sleeve(axis):   # цилиндр R18 вдоль axis∈{'x','y'} на s∈[S0,S1]
        c = trimesh.creation.cylinder(radius=SLEEVE_R, height=S1-S0, sections=64)
        M = trimesh.geometry.align_vectors([0, 0, 1], [1, 0, 0] if axis == 'x' else [0, 1, 0])
        M[:3, 3] = [(S0+S1)/2, 0, 0] if axis == 'x' else [0, (S0+S1)/2, 0]
        c.apply_transform(M); return c
    # плита у НИЗА гильз (z −15..−6, флэт срежет до −14): в позе печати лежит на
    # столе. По центру боров (±4) она висела на z=10..18 — потолок 2513мм² требовал
    # поддержек (аудит печати 2026-07-23). Смещение вдоль нормали функции не вредит.
    web = prism([(WEB_NEAR, 0), (S1, 0), (0, S1), (0, WEB_NEAR)], 'z', (FLAT_Z-1.0, FLAT_Z+WEB_T),
                np.eye(4))
    body = trimesh.boolean.union([web, sleeve('x'), sleeve('y')], engine=ENGINE)
    # боры + teardrop-свод (45°, печать борами горизонтально без поддержек)
    cuts = []
    # C-раскрытие базовой гильзы вниз (−Y лок. = вдоль ноги вниз ≈ мировой низ ∓12°)
    oa = math.radians(OPEN_HALF)
    tri = [(0.0, 0.0), (-45*math.cos(oa), -45*math.sin(oa)), (-45*math.cos(oa), 45*math.sin(oa))]
    A = np.array([[0,0,1,0],[1,0,0,0],[0,1,0,0],[0,0,0,1.]])
    cuts.append(prism(tri, 'x', (S0-16, S1+16), A))
    for ax in ('x', 'y'):
        A = np.array([[0,0,1,0],[1,0,0,0],[0,1,0,0],[0,0,0,1.]]) if ax == 'x' else \
            np.array([[1,0,0,0],[0,0,1,0],[0,1,0,0],[0,0,0,1.]])
        # бор как полигон круг+треугольник (teardrop) в плоскости ⊥ оси
        a = np.linspace(math.pi*0.02, math.pi*1.98, 48)
        circ = [(br*math.cos(t), br*math.sin(t)) for t in a]
        tear = [(br, 0), (0, br*1.414), (-br, 0)]
        cuts.append(prism(circ+[], ax, (S0-16, S1+16), A))
        cuts.append(prism(tear, ax, (S0-16, S1+16), A))
        # самонарез M4 радиально сверху (в позе печати — вертикально, чисто)
        s = trimesh.creation.cylinder(radius=1.7, height=SLEEVE_R+4, sections=20)
        s.apply_translation([SCREW_S if ax == 'x' else 0, SCREW_S if ax == 'y' else 0,
                             (SLEEVE_R+4)/2 - 1])
        cuts.append(s)
    # флэт снизу: срез всего ниже FLAT_Z → пятно на столе
    cuts.append(T.box(-30, S1+30, -30, S1+30, -SLEEVE_R-10, FLAT_Z))
    body = trimesh.boolean.difference([body]+cuts, engine=ENGINE)
    body.merge_vertices(); body.process(validate=True)
    return body


def place(base, cn, apex, bdir):
    """Локальная→мировая: X→bdir (трубка), Y→d (нога), Z→b×d (нормаль плиты)."""
    o = np.array(cn, float)+[0, 0, 13]
    d = (np.array(apex, float)-np.array(cn, float)); d /= np.linalg.norm(d)
    n = np.cross(bdir, d)
    M = np.eye(4); M[:3, 0] = bdir; M[:3, 1] = d; M[:3, 2] = n; M[:3, 3] = o
    m = base.copy(); m.apply_transform(M)
    if m.volume < 0: m.invert()
    return m, o, d


def swing_clearance(meshes, step=1.0):
    """Мин. зазор вершин деталей до РАЗМАХА телескопа 0..90°: труба R120
    (осевое −416..+560 от оси высоты) + ящик R150 (−500..−415). Аналитика."""
    C = np.array([0, 0, T.AXIS_H])
    V = np.vstack([m.vertices for m in meshes] +
                  [m.sample(30000) for m in meshes])       # + сэмплы граней (длинные рёбра)
    rel = V - C
    worst = 1e9
    for a in np.arange(0, 90+1e-9, step):
        p = np.array([0, math.cos(math.radians(a)), math.sin(math.radians(a))])
        t = rel @ p
        rad = np.linalg.norm(rel - np.outer(t, p), axis=1)
        # зазор до трубы и ящика: + = снаружи (по радиусу или по торцу)
        def gap(t0, t1, R):
            dr = rad - R
            dt = np.maximum(t0 - t, t - t1)
            return np.where(dt > 0, np.maximum(dr, dt), dr)
        g = np.minimum(gap(-416, 560, 120), gap(-500, -415, 150))
        worst = min(worst, g.min())
    return worst


def checks(gussets):
    print("Проверки:")
    # 1) не задевает угловые узлы (с хомутами обоих соседей) и сами трубки Ø22
    for (nm, cn, ap, bdir, nbrs), (g, o, d) in zip(CORNERS, gussets):
        node = T.ground_node(cn, ap, nbrs, "c", assemble=True)
        vi = trimesh.boolean.intersection([g, node], engine=ENGINE)
        vi = abs(vi.volume) if (vi is not None and len(vi.vertices)) else 0.0
        tubes = [T.axis_cyl(d, -5, 550, 22.0, origin=o),
                 T.axis_cyl(bdir, -5, 330, 22.0, origin=o)]
        vt = trimesh.boolean.intersection([g, trimesh.boolean.union(tubes, engine=ENGINE)],
                                          engine=ENGINE)
        vt = abs(vt.volume) if (vt is not None and len(vt.vertices)) else 0.0
        print(f"  {nm}: ∩узел={vi/1000:.2f}см³ (норма 0), ∩трубки Ø22={vt/1000:.2f}см³ (норма 0)")
        assert vi < 0.05e3 and vt < 0.05e3, f"косынка {nm} задевает узел/трубку"
    # 2) размах телескопа 0..90°
    worst = swing_clearance([g for g, _, _ in gussets])
    print(f"  зазор косынки ↔ размах телескопа (0..90°, шаг 1°): min {worst:.0f} мм")
    assert worst > 25, "косынка лезет в размах"
    # 3) не ныряет под плоскость фет (z=0 — дорожка венца)
    zmin = min(g.bounds[0, 2] for g, _, _ in gussets)
    print(f"  косынки над плоскостью фет: min z = {zmin:.1f} мм (норма > 1.5)")
    assert zmin > 1.5, "косынка ниже плоскости фет"
    # 3) башни v2 (щёчки!) тоже прогоним через размах
    tw = [T.build(s, assemble=True) for s in (+1, -1)]
    wt = swing_clearance(tw)
    print(f"  зазор башни v2 (с щёчками) ↔ размах: min {wt:.0f} мм")
    assert wt > 3, "башня/щёчка лезет в размах"


def make_plate(base):
    """Стол: 4 косынки (одна и та же деталь, углы отличаются только позицией)."""
    BEDX, BEDY, GAP = 350, 320, 12
    p = base.copy(); p.apply_translation(-p.bounds[0])
    w, dp = p.extents[0], p.extents[1]
    scene = trimesh.Scene()
    for i in range(4):
        q = p.copy(); q.apply_translation([(BEDX-2*w-GAP)/2 + (i % 2)*(w+GAP),
                                           (BEDY-2*dp-GAP)/2 + (i//2)*(dp+GAP), 0])
        assert q.is_watertight
        scene.add_geometry(q, node_name=f"gusset_{i+1}", geom_name=f"gusset_{i+1}")
    scene.export(OUT/"STOL_3_gussets.3mf")
    trimesh.util.concatenate(list(scene.geometry.values())).export(OUT/"STOL_3_gussets.stl")
    bb = (scene.bounds[1]-scene.bounds[0]).round(1)
    vol = sum(g.volume for g in scene.geometry.values())/1000
    print(f"→ STOL_3_gussets.3mf/.stl: 4 дет., {vol:.0f} см³ (~{vol*1.27:.0f} г PETG), "
          f"раскладка {bb[0]}×{bb[1]}, H={bb[2]}")


def scheme(gussets):
    """_RIGID_V2.png: почему балку между сёдлами нельзя и как жёсткость собрана."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 7))
    # ЛЕВО: вид сбоку (Y-Z) — размах и запретная зона
    th = np.linspace(0, math.pi/2, 60)
    for a in th[::3]:
        p = np.array([math.cos(a), math.sin(a)])
        for s, r, c in ((560, 120, "#f4b8b8"), (-416, 120, "#f4b8b8"), (-500, 150, "#e69898")):
            pts = np.array([[0, 700]]) + np.outer([0, s], p) + np.outer([r, r], [p[1], -p[0]])
            ax1.plot(pts[:, 0], pts[:, 1], color=c, lw=2, alpha=0.5)
    ax1.add_patch(plt.Circle((0, 700), 8, color="#333"))
    ax1.annotate("ось высоты (700)", (8, 700), (110, 760), fontsize=9,
                 arrowprops=dict(arrowstyle="->"))
    for y0 in (123, -123):
        ax1.plot([y0, 0], [0, 585], color="#8a6d4b", lw=5, solid_capstyle="round")
    ax1.plot([-260, 260], [0, 0], color="#555", lw=3)
    ax1.plot([-20, -20], [478, 502], color="#c0392b", lw=8)
    ax1.text(-255, 480, "связка z=490 (вариант A)\nв зените — ВНУТРИ трубы ✗",
             fontsize=9.5, color="#c0392b", fontweight="bold")
    ax1.add_patch(plt.Rectangle((-15, 20), 130, 95, fc="#27ae60", alpha=0.35, ec="#27ae60"))
    ax1.text(120, 55, "свободно только тут:\nкосынки углов ✓", fontsize=10,
             color="#1d7a44", fontweight="bold")
    ax1.set_title("Вид сбоку: размах трубы (0–90°) + ящика метёт ВЕСЬ центр выше z≈170.\n"
                  "Балка между сёдлами где угодно сверху = удар о трубу.", fontsize=10.5)
    ax1.set_xlim(-560, 620); ax1.set_ylim(-40, 1300); ax1.set_aspect("equal")
    ax1.set_xlabel("Y мм (перёд →)"); ax1.set_ylabel("Z мм"); ax1.grid(alpha=0.2)
    # ПРАВО: вид спереди (X-Z) — параллелограмм и что его держит
    for sx in (+1, -1):
        ax2.plot([sx*170, sx*170], [0, 585], color="#8a6d4b", lw=5, solid_capstyle="round")
        ax2.add_patch(plt.Circle((sx*170, 700), 100, fill=False, ec="#444", lw=2))
        ax2.plot([sx*170-40, sx*170+40], [585, 585], color="#4d8fd1", lw=7)
        tri = plt.Polygon([[sx*170, 20], [sx*170, 110], [sx*(170-90), 20]],
                          fc="#27ae60", alpha=0.8)
        ax2.add_patch(tri)
    ax2.plot([-170, 170], [0, 0], color="#555", lw=4)
    ax2.add_patch(plt.Rectangle((-150, 200), 300, 1060, fc="#d9d9de", alpha=0.55, ec="#999"))
    ax2.text(0, 900, "труба в зените\n(центр занят)", ha="center", fontsize=10, color="#666")
    ax2.annotate("", (90, 660), (-90, 660),
                 arrowprops=dict(arrowstyle="<->", color="#8e44ad", lw=2.5))
    ax2.text(0, 615, "верхняя «балка» = сам телескоп:\nщёчки пленят фланцы, база колёс 340",
             ha="center", fontsize=10, color="#8e44ad", fontweight="bold")
    ax2.text(0, 60, "косынки: нога+продольная трубка,\nплита в плоскости X-Z — параллелограмм зажат",
             ha="center", fontsize=10, color="#1d7a44", fontweight="bold")
    ax2.set_title("Вид спереди: жёсткость вбок = телескоп сверху (щёчки) + косынки снизу",
                  fontsize=10.5)
    ax2.set_xlim(-320, 320); ax2.set_ylim(-40, 1300); ax2.set_aspect("equal")
    ax2.set_xlabel("X мм"); ax2.grid(alpha=0.2)
    plt.tight_layout(); plt.savefig(OUT/"_RIGID_V2.png", dpi=125, facecolor="white")
    print("→ _RIGID_V2.png")


if __name__ == "__main__":
    print(f"Косынки углов: гильзы Ø{tc.BORE} s{S0:.0f}..{S1:.0f}, плита {WEB_T:.0f}мм, "
          f"диагональ от {WEB_NEAR:.0f}; самонарез M4 на s={SCREW_S:.0f}")
    base = gusset_local()
    print(f"  деталь: watertight={base.is_watertight} vol={base.volume/1000:.0f}см³ "
          f"bbox={np.ptp(base.bounds,axis=0).round(0)}")
    single = base.copy(); single.apply_translation([0, 0, -single.bounds[0, 2]])
    single.export(OUT/"Rocker_alt_corner_gusset.stl")     # одиночная — в позе печати z=0
    gussets = [place(base, cn, ap, b) for nm, cn, ap, b, nbrs in CORNERS]
    checks(gussets)
    make_plate(base)
    scheme(gussets)
    print(f"→ {OUT}")
