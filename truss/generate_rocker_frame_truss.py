#!/usr/bin/env python3
"""
Нижнее кольцо ВРАЩАЮЩЕЙСЯ рамы рокера как ферма «трубы + узлы» — МИНИМАЛЬНЫЙ
стиль, ТОПОЛОГИЯ v3 (эталон truss/_proto_reference.py, одобрен пользователем,
показаны и приняты все 3 типа узлов).

ИЗМЕНЕНИЕ ТОПОЛОГИИ (v3): вращающаяся рама больше НЕ «углы с радиалями к центру».
Теперь:
  • 3 УГЛОВЫХ узла (30/150/270°): ТОЛЬКО 2 хорды к соседним углам (под 60°) +
    нога(и) башни к ближней(им) вершине(ам). НИКАКОЙ радиали к центру.
  • 3 узла СЕРЕДИНЫ ХОРДЫ (середины AB, BC, CA): хорда проходит как 2 полухорды
    (коллинеарно, 180°) + 1 радиаль к центру (90°).
  • 1 ЦЕНТРАЛЬНЫЙ узел: 3 радиали к 3 СЕРЕДИНАМ хорд (120°) + втулка M10 +
    полка энкодера.
→ в каждом узле трубы разнесены ≥60°, разрезные хомуты не сливаются в кашу.

Каждый узел = union ЧИСТЫХ разрезных цилиндров-хомутов (tube_clamp.place_clamp,
бор Ø22.4 + стенка 4 → воротник Ø≈30.4, щель на +X, проушины M5, БОЛТ у НАРУЖНОГО
(входного) торца воротника, где труба точно внутри) + МАЛЕНЬКОЕ ядро (сфера /
втулка), ровно чтобы сварить их водонепроницаемо, + ТОЛЬКО функциональные детали.
Хомуты выходят прямо из ядра (origin = узел): труба вставляется в воротник до
упора в ядро (глухой упор).

Щель хомута смотрит в СВОБОДНОЕ пространство: горизонтальные трубы (хорды,
полухорды, радиали) — щель строго ВВЕРХ (+Z); крутые ноги башни — щель по
ГОРИЗОНТАЛИ НАРУЖУ (от центра рамы).

Мир (мм, z=0 = верх грунт-доски) ИМПОРТИРУЕТСЯ из gen_rocker_comic (НЕ хардкод):
CORNER_ANGLES=(30,150,270), R_CORNER=210, FRAME_Z=75 (ось труб рамы),
WHEEL_X=170, APEX_Z=530 (вершины башен ±170,0,530), PINION_R=240. Все направления
труб СЧИТАЮТСЯ из координат концов.

Детали:
  1. Rocker_corner_node_30.stl / _150.stl (зеркальная пара) — ядро-сфера + 2
     хорды (к двум соседним углам, щель ВВЕРХ) + 1 нога башни к ближней вершине
     (30→apexR, 150→apexL; щель НАРУЖУ). НИКАКОЙ радиали. Больше ничего.
  2. Rocker_corner_drive.stl (270°) — 2 хорды + 2 ноги башни (270° кормит обе
     вершины) + МИНИМАЛЬНЫЙ плоский пад 4×M4 под Rocker_swing_base и вертикальный
     проём Ø40 под шестерню к венцу на PINION_R. НИКАКОЙ радиали.
  3. Rocker_midchord_node.stl (×3 идентичных — одна деталь, печатается 3×) —
     в середине хорды: 2 полухорды коллинеарно (180°) + 1 радиаль к центру (90°),
     щель ВВЕРХ. Малое ядро. Три середины симметричны поворотом на 120° вокруг Z
     (радиаль ⟂ хорде — перпендикуляр к хорде из равноудалённого центра), поэтому
     ОДНА деталь обслуживает все три.
  4. Rocker_center_node.stl — втулка по оси M10 (бор Ø10.6) + 3 радиальных хомута
     к 3 СЕРЕДИНАМ хорд (120°) + МИНИМАЛЬНАЯ полка энкодера (стойка+таб в свободном
     секторе 270°, 2×M3 холдера AS5048A, чип на оси над магнитом), в стороне от щелей.

ОРИЕНТАЦИЯ ПЕЧАТИ (проектируем в мировых координатах, чтобы оси труб стыковались,
затем разворачиваем каждую деталь в естественную позу печати, z_min=0):
  • Rocker_corner_node/drive: разворот вокруг Z (наружу-радиаль угла → +X). Стол =
    низ горизонтальных воротников хорд (боры Ø22 горизонтальны, мостятся по верху,
    щель вверх); воротники ног башни и приводной пад/проём смотрят вверх.
  • Rocker_midchord_node: все три трубы горизонтальны и копланарны (z=75) → деталь
    плоская. Разворот вокруг Z (радиаль → −X). Плоский низ на стол, боры мостятся,
    щели вверх.
  • Rocker_center_node: без разворота — втулка стоит вертикально, её плоский НИЗ
    на столе (бор M10 вертикален), радиальные хомуты горизонтальны (мост),
    стойка+таб полки уходят вверх (лёгкий свес) в секторе −Y (270°).
"""
import math
from pathlib import Path

import numpy as np
import trimesh

import gen_rocker_comic as W            # общий мир (координаты, polar) — НЕ хардкод
import tube_clamp as TC                 # чистый параметрический хомут + place_clamp

# ============================ ПАРАМЕТРЫ ============================
# --- Мир (из gen_rocker_comic) ---
CORNER_ANGLES = W.CORNER_ANGLES         # (30, 150, 270)
R_CORNER = W.R_CORNER                   # 210
FRAME_Z = W.FRAME_Z                     # 75  (ось труб вращающейся рамы)
WHEEL_X = W.WHEEL_X                     # 170
APEX_Z = W.APEX_Z                       # 530
PINION_R = W.PINION_R                   # 240
APEX_R = np.array([WHEEL_X, 0.0, APEX_Z], float)     # правая вершина (+X)
APEX_L = np.array([-WHEEL_X, 0.0, APEX_Z], float)    # левая вершина (−X)
CENTER = np.array([0.0, 0.0, FRAME_Z], float)

# Ноги башни по углам (из gen_rocker_comic::towers): 30→apexR, 150→apexL,
# 270→обе вершины.
TOWER_LEGS = {30: [APEX_R], 150: [APEX_L], 270: [APEX_R, APEX_L]}

# --- Хомут (чистый разрезной цилиндр из tube_clamp) ---
CLAMP_H = 40.0          # высота воротника вдоль оси трубы, мм
BORE_D = TC.BORE_D      # Ø бора ≈ 22.4 (труба Ø22 + зазор)
CLAMP_OD = TC.CLAMP_OD  # наружный Ø воротника ≈ 30.4
SLIT_UP = (0.0, 0.0, 1.0)   # щель ВВЕРХ для горизонтальных труб

# --- Минимальное ядро узла ---
HUB_R = 15.0            # радиус ядра-сферы: хомуты выходят из него, труба
                        #   упирается в ядро (глухой упор)
ICO_SUB = 3             # подразбиение икосферы ядра

# --- Тест-посадки трубы + сквозная расточка бора (эталон: generate_rocker_towers) ---
TUBE_D = 22.0           # номинал алюминиевой трубы
GRIP = 40.0            # требуемая глубина посадки, мм
DRILL_D = TC.BORE       # Ø22.4 — сквозная расточка бора через ядро
FIT_TOL = 8.0          # порог теста: <8% объёма трубы = PASS
# STAGGER (узел 270°): две ноги башни к apexR/apexL всего ~37.5° апарт → их боры
# пересекаются у ядра и «палка не влезет» (тело одной ноги перекрывает вход другой).
# Заднюю ногу (к apexL) выносим вдоль её оси на DRIVE_LEG_STAGGER: её воротник с
# ушками+болтом уходит наружу, входные торцы двух ног разнесены по оси → каждая
# труба входит на полный грип. Гэп ядро→воротник заполняем струтом, затем сквозная
# расточка бора Ø22.4 (труба садится в ПУСТОЙ бор). Хорды (60°) и радиали не трогаем.
DRIVE_LEG_STAGGER = 24.0
# ЦЕНТР: воротник радиали вынесен за втулку M10 (Ø22), расточка бора только снаружи
CENTER_RADIAL_OFF = 16.0    # вынос воротника радиали наружу от оси, мм (> R втулки 11)
CENTER_DRILL_START = 13.0   # начало сквозной расточки (снаружи втулки r11 → цела)

# --- Привод (узел 270°): минимальный пад 4×M4 + проём под шестерню ---
PAD_X = 56.0            # пад под Rocker_swing_base, X
PAD_Y = 62.0            # пад, Y (тянется наружу к PINION_R)
PAD_T = 8.0             # толщина пада
PAD_TOP_Z = 83.0        # верх пада (низ плиты swing_base здесь)
PAD_CTR_Y = -206.0      # центр пада по Y (у узла 270°, C=(0,−210))
M4_CLR = 4.4            # сквозной M4
M4_NUT_AF = 7.0         # гайка M4 «под ключ» (hex)
M4_NUT_DEEP = 3.2       # глубина hex-кармана гайки
M4_DX = 44.0            # 4×M4: размах по X (болты ±22)
M4_DY = 20.0            # 4×M4: размах по Y (±10)
PINION_CLR_D = 40.0     # вертикальный проём под шестерню на PINION_R

# --- ГЛАЙД-ПАД (только 3 угловых узла, вкл. привод): плоская лапа, на которой рама
# катится по дорожке венца ---
# Рама поднята (FRAME_Z 75→82): низ узла/хомутов теперь ≈ FRAME_Z−CLAMP_OD/2 ≈ 66.8,
# т.е. круглые воротники ВЫШЕ дорожки. Под ядром каждого угла — плоская прямоугольная
# лапа с ПЛОСКИМ низом на z=GLIDE_BOTTOM_Z=63 (= верх дорожки 60 + тефлон 3): рама
# опирается на 3 такие лапы (тефлон клеится/прикручивается к плоскому низу). Середины
# хорд (R105) и центр (ось M10) — БЕЗ падов.
GLIDE_RAD = 15.0        # лапа ПОПЕРЁК дорожки (радиально) — ≤18 (влезть в паз венца)
GLIDE_TAN = 22.0        # лапа ВДОЛЬ дорожки (тангенциально), мм. = размер тефлон-пятака
GLIDE_BOTTOM_Z = 63.0   # мировой z ПЛОСКОГО низа лапы = дорожка(60) + тефлон(3)
GLIDE_RISER_D = 14.0    # шейка-стойка лапа→ядро (жирная сварка ниже бора трубы)
GLIDE_M3_CLR = 3.4      # сквозное M3 под винт тефлона (или просто клей)
GLIDE_CSK_D = 6.5       # зенковка Ø под потайную головку M3 на ПЛОСКОМ (нижнем) лице
GLIDE_CSK_H = 2.0       # глубина конуса зенковки, мм

# --- Центр: втулка по оси M10 ---
BUSH_OD = 22.0          # Ø втулки
M10_BORE = 10.6         # бор по гладкому хвостовику M10
# Низ ВРАЩАЮЩЕЙСЯ втулки поднят до 58: НЕПОДВИЖНОЕ ядро хаба земли (z10..54) больше
# не трётся о вращающийся рукав (раньше втулка z50..110 лезла в хаб на ~4мм). 4мм
# осевой зазор над верхом хаба (54).
BUSH_Z0 = 58.0          # низ втулки (плоский стол) — 4мм зазор над хабом (верх z54)
BUSH_Z1 = 110.0         # верх втулки

# --- Полка энкодера AS5048A (минимальная: стойка + таб), сектор −Y (270°) ---
MAG_TOP_Z = 130.0       # верх колпачка магнита на болте (мир)
AIR_GAP = 1.0           # зазор магнит↔чип
CHIP_T = 1.1            # корпус чипа AS5048A над платой
BRD_T = 1.6             # толщина платы
HLD_BOSS_H = 3.0        # бобышки board_holder
SHELF_TOP_Z = MAG_TOP_Z + AIR_GAP + CHIP_T + BRD_T + HLD_BOSS_H   # ≈136.7
SHELF_T = 6.0           # толщина таба полки
SHELF_W = 28.0          # ширина стойки/таба по X (= лапка холдера)
TAB_CY = -12.0          # центр таба по Y (кроет ось и пилоты), сектор −Y
TAB_DY = 36.0           # глубина таба по Y (−30..+6, кроет ось)
POST_CY = -14.0         # центр стойки по Y (−Y сторона, свободный сектор 270°)
POST_DY = 32.0          # глубина стойки по Y (−30..+2 → варится с втулкой)
POST_Z0 = 90.0          # низ стойки (над воротниками, тонет во втулку z≤110)
M3_SELFTAP = 2.7        # пилот M3 холдера
PILOT_XY = (10.0, -15.5)    # 2 пилота M3 холдера: ±x, −y (чип оказывается на оси)
PILOT_DEPTH = 8.0

SEG = 96
OUTDIR = Path(__file__).parent / "stl"


# ============================ ХЕЛПЕРЫ ============================
def cyl(r, h, seg=SEG, T=None):
    c = trimesh.creation.cylinder(radius=r, height=h, sections=seg)
    if T is not None:
        c.apply_transform(T)
    return c


def box(x, y, z, T=None):
    b = trimesh.creation.box(extents=(x, y, z))
    if T is not None:
        b.apply_transform(T)
    return b


def tr(x, y, z):
    M = np.eye(4)
    M[:3, 3] = (x, y, z)
    return M


def rotx(deg):
    return trimesh.transformations.rotation_matrix(math.radians(deg), [1, 0, 0])


def hexprism(af, h, T=None):
    """Шестигранная призма «под ключ» af (across flats), ось Z."""
    from shapely.geometry import Polygon
    r = af / math.cos(math.radians(30)) / 2.0
    angs = np.radians(np.arange(6) * 60 + 30)
    pts = np.c_[r * np.cos(angs), r * np.sin(angs)]
    m = trimesh.creation.extrude_polygon(Polygon(pts), height=h)
    if T is not None:
        m.apply_transform(T)
    return m


def slit_for(node, d):
    """Щель В СВОБОДНОЕ пространство: горизонтальная труба (|dz|<0.5) → ВВЕРХ;
    крутая труба (нога башни) → по ГОРИЗОНТАЛИ НАРУЖУ от центра рамы."""
    if abs(d[2]) < 0.5:
        return SLIT_UP
    out = np.array([node[0], node[1], 0.0])
    n = np.linalg.norm(out)
    return tuple(out / n) if n > 1e-6 else SLIT_UP


def clamp_toward(node, endpoint, height=CLAMP_H):
    """Разместить чистый хомут: ось бора node→endpoint, нижний торец в узле
    (труба входит в воротник до упора в ядро), щель — в пустоту (slit_for).
    (эталон: _proto_reference.py::place)"""
    node = np.asarray(node, float)
    d = np.asarray(endpoint, float) - node
    d /= np.linalg.norm(d)
    return TC.place_clamp(height, node, tube_dir=d, slit_dir=slit_for(node, d))


def axis_cyl(direction, z0, z1, dia, origin=(0.0, 0.0, 0.0), seg=48):
    """Цилиндр Ø`dia` вдоль `direction`, от параметра z0 до z1 по оси, отсчёт от
    `origin`. Для сквозной расточки бора и для пробника tube-fit."""
    d = np.asarray(direction, float); d /= np.linalg.norm(d)
    o = np.asarray(origin, float)
    L = float(z1 - z0)
    c = trimesh.creation.cylinder(radius=dia / 2.0, height=L, sections=seg)
    T = trimesh.geometry.align_vectors([0, 0, 1], d)
    T[:3, 3] = o + d * (z0 + L / 2.0)
    c.apply_transform(T)
    return c


def drill_bores(part, sockets):
    """Сквозная расточка бора Ø DRILL_D по каждому сокету: от z=−3 (сквозь ядро) до
    входного торца воротника (entry). Бор чист на полный грип, тело соседей на пути
    расточено → труба всегда входит до упора."""
    cuts = [axis_cyl(d, -3.0, entry, DRILL_D, origin=o) for _, o, d, entry in sockets]
    return trimesh.boolean.difference([part] + cuts, engine="manifold")


def tube_fit_test(part, sockets, name):
    """ТЕСТ ПОСАДКИ: Ø22 цилиндр длиной GRIP от входа бора ВНУТРЬ; пересечение с
    телом узла < FIT_TOL% объёма трубы = PASS (труба сидит в ПУСТОМ боре)."""
    tvol = math.pi * (TUBE_D / 2.0) ** 2 * GRIP
    all_pass = True
    for label, o, d, entry in sockets:
        t = axis_cyl(d, entry - GRIP, entry, TUBE_D, origin=o)
        it = trimesh.boolean.intersection([part, t], engine="manifold")
        vol = abs(it.volume) if (it is not None and len(it.vertices)) else 0.0
        frac = vol / tvol * 100.0
        ok = frac < FIT_TOL
        all_pass = all_pass and ok
        print(f"    tube-fit {name}:{label:<14} {frac:5.1f}%  {'PASS' if ok else 'FAIL'}")
    return all_pass


def to_bed(part, T=None):
    """Развернуть в позу печати (опц. T), затем центрировать по XY и опустить
    z_min=0 на стол."""
    if T is not None:
        part.apply_transform(T)
    b = part.bounds
    part.apply_translation([-(b[0, 0] + b[1, 0]) / 2,
                            -(b[0, 1] + b[1, 1]) / 2,
                            -b[0, 2]])
    return part


def finish(mesh, name):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    # Грубая сварка вершин ДО валидации (тела вращения дают sliver-пары ~5e-7 —
    # validate их дырявит); схлопываем в честное ребро.
    mesh.merge_vertices(digits_vertex=5)
    mesh.process(validate=True)
    # выкинуть плавающие boolean-стружки — оставляем только крупнейшее тело
    parts = mesh.split(only_watertight=False)
    if len(parts) > 1:
        mesh = max(parts, key=lambda m: m.volume)
    # убрать вырожденные грани (нулевой площади) — от них 0-см³ «тела»/дефекты
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices(digits_vertex=5)
    # надёжно закрыть дыры (сложные узлы с падом дают 6-12 микро-дыр)
    for _ in range(3):
        if mesh.is_watertight:
            break
        trimesh.repair.fill_holes(mesh)
        trimesh.repair.fix_normals(mesh)
        trimesh.repair.fix_winding(mesh)
        mesh.merge_vertices(digits_vertex=5)
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.remove_unreferenced_vertices()
    # финальная проверка: ровно одно тело
    fin = mesh.split(only_watertight=False)
    if len(fin) > 1:
        mesh = max(fin, key=lambda m: m.volume)
    out = OUTDIR / f"{name}.stl"
    mesh.export(out)
    bb = mesh.bounds
    print(f"  {name}.stl  watertight={mesh.is_watertight}  bodies={len(parts)}  "
          f"vol={mesh.volume/1000:.2f}cm³  "
          f"bbox={bb[1,0]-bb[0,0]:.0f}×{bb[1,1]-bb[0,1]:.0f}×{bb[1,2]-bb[0,2]:.0f}mm")
    return mesh


# ============================ ГЕОМЕТРИЯ ТРУБ ============================
def corner_xyz(ang):
    return np.array(W.polar(R_CORNER, ang, FRAME_Z), float)


def chord_mid(ang_a, ang_b):
    return (corner_xyz(ang_a) + corner_xyz(ang_b)) / 2.0


def endpoints_for_corner(ang):
    """(v3) Трубы углового узла: 2 хорды к соседним углам + нога(и) башни.
    НИКАКОЙ радиали к центру."""
    node = corner_xyz(ang)
    others = [a for a in CORNER_ANGLES if a != ang]
    eps = [(f"chord→{a}°", corner_xyz(a)) for a in others]        # 2 хорды (60°)
    for apex in TOWER_LEGS[ang]:                                  # нога(и) башни
        tag = "tower→apexR" if apex[0] > 0 else "tower→apexL"
        eps.append((tag, apex))
    return node, eps


# ============================ 1/2. УГЛОВОЙ УЗЕЛ ============================
def corner_node(ang, drive=False):
    """(v3) Минимальный угловой узел: ядро-сфера + 2 хорды (щель вверх) +
    нога(и) башни (щель наружу). БЕЗ радиали. drive=True → узел 270°:
    + минимальный пад 4×M4 под Rocker_swing_base и вертикальный проём Ø40 под
    шестерню. Ничего лишнего."""
    node, eps = endpoints_for_corner(ang)
    name = "Rocker_corner_drive" if drive else f"Rocker_corner_node_{int(ang)}"

    part = trimesh.creation.icosphere(subdivisions=ICO_SUB, radius=HUB_R)
    part.apply_translation(node)
    # сокеты: (label, node, dir, entry). Для привода — STAGGER задней ноги (apexL).
    sockets = []
    for tag, ep in eps:
        d = np.asarray(ep, float) - node
        d /= np.linalg.norm(d)
        off = DRIVE_LEG_STAGGER if (drive and tag == "tower→apexL") else 0.0
        origin = node + d * off
        part = part.union(TC.place_clamp(CLAMP_H, origin, tube_dir=d,
                                         slit_dir=slit_for(node, d)))
        if off > 0.5:   # струт ядро→вынесенный воротник (сваривает; потом расточится)
            part = part.union(axis_cyl(d, -8.0, off + 8.0, CLAMP_OD,
                                       origin=node, seg=SEG))
        sockets.append((tag, node.copy(), d, off + CLAMP_H))

    cuts = []
    if drive:
        # Пад привода МОНОЛИТНО с узлом (надёжнее отдельной детали): площадка
        # 4×M4 под Rocker_swing_base + проём под шестерню, на опоре-массиве от
        # ядра (не висит). Обломки boolean вычищаются в finish() (fill_holes).
        pad = box(PAD_X, PAD_Y, PAD_T, tr(0, PAD_CTR_Y, PAD_TOP_Z - PAD_T / 2))
        leg = box(PAD_X, 34.0, PAD_TOP_Z - FRAME_Z + HUB_R,
                  tr(0, -R_CORNER + 4, (PAD_TOP_Z - PAD_T + FRAME_Z - HUB_R) / 2))
        for sx in (-1, 1):
            gus = box(6, 40, PAD_TOP_Z - FRAME_Z + HUB_R,
                      tr(sx * (PAD_X / 2 - 3), -R_CORNER + 6,
                         (PAD_TOP_Z - PAD_T + FRAME_Z - HUB_R) / 2))
            part = part.union(gus)
        part = part.union(pad).union(leg)
        for sx in (-1, 1):
            for sy in (-1, 1):
                hx, hy = sx * M4_DX / 2, PAD_CTR_Y + sy * M4_DY / 2
                cuts.append(cyl(M4_CLR / 2, PAD_T + 2, seg=24,
                                T=tr(hx, hy, PAD_TOP_Z - PAD_T / 2)))
                cuts.append(hexprism(M4_NUT_AF, M4_NUT_DEEP + 0.5,
                                     T=tr(hx, hy, PAD_TOP_Z - PAD_T
                                          + M4_NUT_DEEP / 2 - 0.25)))
        cuts.append(cyl(PINION_CLR_D / 2, 200, seg=48, T=tr(0, -PINION_R, 60)))

    # --- ГЛАЙД-ПАД (все 3 угла): плоская лапа под ядром, ПЛОСКИЙ низ на z=63 ---
    # Плита лапы стоит НИЖЕ горизонтального бора трубы (низ бора = FRAME_Z−DRILL_D/2),
    # поэтому её плоский низ не режется расточкой; шейка Ø14 сваривает лапу с ядром
    # (её верх тонет в ядре, низ — в плите). После разворота (yaw вокруг Z) и to_bed
    # плоский низ (нормаль −Z, к дорожке) ложится на стол z=0 → печатается идеально
    # плоским. Один M3 сквозь + зенковка на плоском лице (винт тефлона заподлицо/клей).
    gx, gy = float(node[0]), float(node[1])
    plate_top = FRAME_Z - DRILL_D / 2.0 - 1.0        # ниже горизонтального бора
    plate_h = plate_top - GLIDE_BOTTOM_Z
    # площадка = размер тефлон-пятака (GLIDE_RAD×GLIDE_TAN), повёрнута по РАДИУСУ:
    # узкая сторона (RAD=15) поперёк дорожки → влезает в паз венца (тело 18мм)
    glide = box(GLIDE_RAD, GLIDE_TAN, plate_h)
    glide.apply_transform(trimesh.transformations.rotation_matrix(math.radians(ang), [0, 0, 1]))
    glide.apply_translation([gx, gy, (GLIDE_BOTTOM_Z + plate_top) / 2])
    riser = cyl(GLIDE_RISER_D / 2, (FRAME_Z + 4) - (GLIDE_BOTTOM_Z + 3), seg=48,
                T=tr(gx, gy, ((GLIDE_BOTTOM_Z + 3) + (FRAME_Z + 4)) / 2))
    part = part.union(glide).union(riser)
    # Крепёж тефлона — НЕ через скользящую грань! Низ лапы (z=GLIDE_BOTTOM_Z)
    # остаётся ПЛОСКИМ и ЧИСТЫМ (на него клеится тефлон-пятак: скотч 3M VHB
    # или контактный клей по зашкуренному тефлону). Опционально винт СВЕРХУ:
    # глухое M3-отверстие из тела лапы ВНИЗ, НЕ доходя до плоского лица на 1.5мм
    # (винт входит в тефлон снизу через глухое, скользящую грань не пробивает).
    hole_h = plate_h - 1.5                         # глухое: не доходит до низа
    cuts.append(cyl(GLIDE_M3_CLR / 2, hole_h, seg=24,
                    T=tr(gx, gy, plate_top - hole_h / 2)))

    if cuts:
        part = part.difference(cuts)

    part = drill_bores(part, sockets)          # сквозной пустой бор на каждый сокет
    ok = tube_fit_test(part, sockets, name)
    assert ok, f"{name}: tube-fit FAIL — палка не влезет"

    # поза печати: развернуть вокруг Z (наружу-радиаль угла → +X)
    yaw = trimesh.transformations.rotation_matrix(math.radians(-ang), [0, 0, 1])
    part = to_bed(part, yaw)
    return finish(part, name)


# ============================ 3. СЕРЕДИНА ХОРДЫ ============================
def midchord_node():
    """(v3) Узел середины хорды (эталон — середина хорды 30–150 = AB): 2 полухорды
    коллинеарно к A и к B (180°) + 1 радиаль к центру (90°), все щели ВВЕРХ.
    Три середины хорд симметричны поворотом на 120° вокруг Z (радиаль — перпендикуляр
    к хорде из равноудалённого центра) → одна деталь печатается 3×."""
    m = chord_mid(30, 150)
    eps = [("half→30°", corner_xyz(30)),
           ("half→150°", corner_xyz(150)),
           ("radial→center", CENTER)]

    part = trimesh.creation.icosphere(subdivisions=ICO_SUB, radius=HUB_R)
    part.apply_translation(m)
    sockets = []
    for tag, ep in eps:
        part = part.union(clamp_toward(m, ep))
        d = np.asarray(ep, float) - m; d /= np.linalg.norm(d)
        sockets.append((tag, np.asarray(m, float), d, CLAMP_H))

    part = drill_bores(part, sockets)          # сквозной пустой бор на каждый сокет
    ok = tube_fit_test(part, sockets, "Rocker_midchord_node")
    assert ok, "Rocker_midchord_node: tube-fit FAIL"

    # поза печати: развернуть вокруг Z так, что радиаль-к-центру → −X.
    # радиаль mAB→центр = (0,−1,0); yaw −90° переводит −Y → −X.
    yaw = trimesh.transformations.rotation_matrix(math.radians(-90), [0, 0, 1])
    part = to_bed(part, yaw)
    return finish(part, "Rocker_midchord_node")


# ============================ 4. ЦЕНТРАЛЬНЫЙ УЗЕЛ ============================
def center_node():
    """(v3) Минимальный центр: ядро-втулка по оси M10 (бор Ø10.6) + 3 радиальных
    хомута к 3 СЕРЕДИНАМ хорд (120°, щель вверх) + минимальная полка энкодера
    (стойка+таб в свободном секторе −Y, 2×M3, чип на оси над магнитом). Без арок."""
    node = CENTER
    mids = [chord_mid(30, 150), chord_mid(150, 270), chord_mid(270, 30)]

    part = trimesh.creation.icosphere(subdivisions=ICO_SUB, radius=HUB_R)
    part.apply_translation(node)
    part = part.union(cyl(BUSH_OD / 2, BUSH_Z1 - BUSH_Z0,
                          T=tr(0, 0, (BUSH_Z0 + BUSH_Z1) / 2)))

    # 3 радиали к серединам хорд. Центр занят ВТУЛКОЙ M10 (Ø22) — бор радиали нельзя
    # сверлить через ось. Поэтому воротник радиали ВЫНОСИМ наружу за втулку на
    # CENTER_RADIAL_OFF, тело ядро→воротник — струт, а сквозная расточка бора идёт
    # только ОТ CENTER_DRILL_START (снаружи втулки) наружу → втулка/M10 целы, а
    # тестовая зона трубы [off, off+GRIP] лежит в ПУСТОМ боре за втулкой.
    node0 = np.asarray(node, float)
    sockets = []
    for m in mids:
        d = np.asarray(m, float) - node0; d /= np.linalg.norm(d)
        origin = node0 + d * CENTER_RADIAL_OFF
        part = part.union(TC.place_clamp(CLAMP_H, origin, tube_dir=d,
                                         slit_dir=slit_for(node0, d)))
        part = part.union(axis_cyl(d, 8.0, CENTER_RADIAL_OFF + 8.0, CLAMP_OD,
                                   origin=node0, seg=SEG))     # струт втулка→воротник
        sockets.append((f"radial→{origin[:2].round(0)}", node0, d,
                        CENTER_RADIAL_OFF + CLAMP_H))

    # полка энкодера: стойка (−Y, вне щелей/радиалей) + горизонтальный таб над осью
    post = box(SHELF_W, POST_DY, SHELF_TOP_Z - POST_Z0,
               tr(0, POST_CY, (POST_Z0 + SHELF_TOP_Z) / 2))
    tab = box(SHELF_W, TAB_DY, SHELF_T, tr(0, TAB_CY, SHELF_TOP_Z - SHELF_T / 2))
    part = part.union(post).union(tab)

    cuts = [cyl(M10_BORE / 2, BUSH_Z1 - BUSH_Z0 + 40, seg=48,
                T=tr(0, 0, (BUSH_Z0 + BUSH_Z1) / 2))]
    for sx in (-1, 1):
        cuts.append(cyl(M3_SELFTAP / 2, PILOT_DEPTH + 1, seg=24,
                        T=tr(sx * PILOT_XY[0], PILOT_XY[1],
                             SHELF_TOP_Z + 1 - (PILOT_DEPTH + 1) / 2)))
    # сквозная расточка бора радиалей — ТОЛЬКО за втулкой (от CENTER_DRILL_START)
    for _tag, o, d, entry in sockets:
        cuts.append(axis_cyl(d, CENTER_DRILL_START, entry, DRILL_D, origin=o))
    part = part.difference(cuts)

    ok = tube_fit_test(part, sockets, "Rocker_center_node")
    assert ok, "Rocker_center_node: tube-fit FAIL"

    part = to_bed(part)        # втулка вертикальна, плоский низ на стол
    return finish(part, "Rocker_center_node")


# ============================ ОТЧЁТ ПО ТРУБАМ ============================
def report_tubes():
    def L(a, b):
        return float(np.linalg.norm(np.asarray(a, float) - np.asarray(b, float)))
    print("\nСегменты труб этой топологии (из координат концов, мм):")
    print(f"  полухорда угол→середина (все 6 равны): "
          f"{L(corner_xyz(30), chord_mid(30, 150)):.1f}")
    print(f"  радиаль центр→середина хорды (все 3 равны): "
          f"{L(CENTER, chord_mid(30, 150)):.1f}")
    print(f"  (полная хорда угол↔угол = 2×полухорды: "
          f"{L(corner_xyz(30), corner_xyz(150)):.1f})")
    for ang in CORNER_ANGLES:
        node = corner_xyz(ang)
        for apex in TOWER_LEGS[ang]:
            tag = "apexR(+170)" if apex[0] > 0 else "apexL(−170)"
            print(f"  нога башни {int(ang):>3}°→{tag}: {L(node, apex):.1f}")


def main():
    print("Генерация фермы нижнего кольца вращающейся рамы (v3, минимальный стиль)…")
    print(f"  углы {CORNER_ANGLES} на R{R_CORNER}, ось труб z={FRAME_Z}; "
          f"вершины башен ±{WHEEL_X},0,{APEX_Z}; бор хомута Ø{BORE_D} воротник Ø{CLAMP_OD}")
    corner_node(30)
    corner_node(150)
    corner_node(270, drive=True)
    midchord_node()
    center_node()
    report_tubes()
    print(f"\nГотово → {OUTDIR}")
    print("Количества: угловой узел ×2 (30°,150°), приводной узел ×1 (270°), "
          "середина хорды ×3 (одна деталь), центральный узел ×1.")


if __name__ == "__main__":
    main()
