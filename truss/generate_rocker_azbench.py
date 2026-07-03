#!/usr/bin/env python3
"""
Стендовый ("bench") азимутальный комплект: венец на фанере + прямой привод.

Генерит 5 бинарных STL в truss/stl/ через CSG (trimesh + manifold3d).
Мир стенда: z=0 = ВЕРХ опорной фанерной доски. Ось азимута = болт M10
в начале координат, остриём ВВЕРХ.

  z=0        верх опорной доски
  z=0..24    Rocker_hub_ground — втулка-гайка оси, прикручена к доске
  z=12..22   венец (4×Rocker_ring_segment из generate_rocker_azdrive)
             лежит на 3 сёдлах Rocker_ring_saddle (высота 12)
  z=20       верх тела венца = дорожка мебельных подпятников (~5мм)
  z=25..37   вращающийся фанерный диск 12мм (режет пользователь; в центре
             сверлит Ø11 под болт)
  z=37..43   Rocker_az_motor_plate на краю диска над выпилом (NEMA17
             сверху, вал вниз сквозь плиту и выпил)
  z=12..24   Rocker_pinion_16T_direct на валу мотора (зона зубьев венца
             12..22; торец вала NEMA17 на z≈18 → хват верхних 6мм шестерни)
  z=37..     Rocker_pivot_flange — втулка по болту + стойка с полкой под
             существующий board_holder (чип AS5048A смотрит ВНИЗ, на оси,
             в ~1мм над колпачком магнита, впрессованным на конец болта)

Печать PETG, все детали без поддержек: расточки вертикальные, под
нависаниями — фаски 45° (конус над ушами втулки, клин под полкой стойки).

Детали / количества:
  1. Rocker_hub_ground.stl       ×1  (STL уже ПЕРЕВЁРНУТ верхом вниз —
                                      гекс-карман и зенковки печатаются без
                                      поддержек; в мире плоский верх = стол)
  2. Rocker_ring_saddle.stl      ×3
  3. Rocker_az_motor_plate.stl   ×1
  4. Rocker_pinion_16T_direct.stl ×1 (зубья — импорт из generate_rocker_azdrive)
  5. Rocker_pivot_flange.stl     ×1
"""
import math
import sys
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import Point, Polygon
from shapely.geometry import box as shp_box
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).parent))
from generate_rocker_azdrive import (          # noqa: E402 — переиспользуем зубья
    MODULE, PIN_TEETH, PIN_PITCH_R, PIN_TIP_R, PIN_ROOT_R, PIN_FACE,
    RING_PITCH_R, RING_TEETH, BODY_R_IN, SEG_CIRC, tooth_poly)

# ============================ ПАРАМЕТРЫ ============================
# --- Мир стенда (z=0 = верх опорной доски) ---
RING_Z0 = 12.0          # низ венца (верх сёдел)
DISC_BOT_Z = 25.0       # низ вращающегося диска (подпятники ~5мм на z=20)
DISC_TOP_Z = 37.0       # верх вращающегося диска (фанера 12мм)

# --- Проверенные посадки этого принтера ---
M3_CLR = 3.4            # Ø сквозного M3
M3_PILOT = 2.7          # Ø пилота под саморез M3
M5_CLR = 5.4            # Ø сквозного M5 (не используется, для справки)
M10_CLR = 10.6          # Ø сквозного M10
WOOD_D = 4.4            # Ø потайного отверстия под саморез по дереву
WOOD_CSK_D = 9.0        # Ø зенковки 90° под головку самореза
NUT3_AF = 5.6           # M3 гайка «под ключ» (карман)
NUT3_T = 2.6            # глубина кармана гайки M3

# --- 1. Втулка оси на доске (Rocker_hub_ground) ---
HUB_OD = 70.0           # Ø тела
HUB_H = 24.0            # высота (низ диска на 25 → 1мм зазора сверху)
NUT10_AF = 17.4         # гекс-карман гайки M10 «под ключ»
NUT10_DEPTH = 7.0       # глубина кармана (снизу: болт снизу доски тянет гайку)
EAR_HOLE_R = 39.0       # радиус окружности саморезов ушей
EAR_LOBE_R = 6.5        # радиус лепестка уха (вершина уха на R45)
EAR_LOBE_CTR = 38.5     # радиус центра лепестка
EAR_T = 6.0             # толщина уха
EAR_ANGLES = (90.0, 210.0, 330.0)
EAR_CONE_R0 = 45.5      # фаска 45° над ушами: от R45.5 на z=6 к R35 на z=16.5
ACCESS_D = 9.5          # Ø вертикального колодца доступа к головке сквозь фаску
RIM_CHAMF = 1.0         # фаска верхней кромки (= кромка у стола при печати)

# --- 2. Седло венца (Rocker_ring_saddle, ×3) ---
SAD_L = 44.0            # вдоль радиуса (X)
SAD_W = 32.0            # тангенциально (Y)
SAD_H = 12.0            # высота (низ венца z=12)
SAD_R = 210.0           # радиус центра седла от оси азимута
RIDGE_W = 3.0           # гребень-упор: ширина
RIDGE_H = 2.0           # гребень-упор: высота (тело венца 8мм — упор в бок)
# наружная грань гребня = дуга R200 = BODY_R_IN венца (регистрация кольца)
SAD_SLOT_LEN = 12.0     # полная длина радиального слота (ход ±(12-4.4)/2)
SAD_SLOT_X = 0.0        # слот в центре (под кольцом — юстировка до укладки)
SAD_HOLE_X = 17.0       # круглое отверстие снаружи кольца (доступно всегда)

# --- 3. Плита мотора (Rocker_az_motor_plate) ---
MP_L = 90.0             # вдоль радиуса (X)
MP_W = 80.0             # тангенциально (Y)
MP_T = 6.0              # толщина (лежит на диске: z=37..43)
MP_CTR_HOLE = 23.0      # центральное отверстие: пилот Ø22 + вал (с запасом юстировки)
NEMA_SQ = 31.0          # квадрат крепёжных M3 NEMA17
M3_TRAVEL = 8.0         # ход радиальных слотов M3 (±4)
WS_TRAVEL = 12.0        # ход радиальных слотов саморезов (±6)
WS_POS = (35.0, 32.0)   # |x|,|y| саморезов к диску
POCKET_W = 42.5         # карман-регистратор корпуса мотора (42.3 + зазор)
POCKET_DEEP = 1.0       # глубина кармана

# --- 4. Шестерня прямого привода (Rocker_pinion_16T_direct) ---
PIN_BORE_D = 5.2        # бор под вал NEMA17 Ø5
FLAT_DEPTH = 0.5        # D-лыска: хорда на 2.6-0.5=2.1 от центра (лыска вала на 2.0)
SET_HOLE = 3.2          # Ø радиального отверстия фиксатора M3
SET_Z = 10.5            # ось фиксатора. НЕ середина венца: торец вала на
                        # мире z≈18 (плита 43 − карман 1 − вал 24), шестерня
                        # 12..24 → вал только в локальных 6..12; z=10.5 давит
                        # серединой хвата и выше зоны зацепления венца (22)
NUT_R_CTR = 6.6         # радиус центра гайки (наружная стенка 6.9мм до корня)

# --- 5. Стойка-втулка энкодера (Rocker_pivot_flange) ---
FL_SQ = 50.0            # фланец 50×50
FL_T = 6.0              # толщина фланца
BUSH_OD = 22.0          # Ø втулки
BUSH_H = 20.0           # высота втулки
PIV_BORE = 10.6         # бор по болту M10
FL_SCREW_XY = 19.5      # |x|=|y| четырёх потайных саморезов к диску

MAG_TOP_Z = 75.0        # ← ВЕРХ колпачка магнита на болте, мир. МЕНЯТЬ ЗДЕСЬ
                        #   после примерки болта M10×110 (полка пересчитается)
AIR_GAP = 1.0           # воздушный зазор магнит↔чип
CHIP_T = 1.1            # высота корпуса чипа AS5048A над платой
BRD_T = 1.6             # толщина платы (из gen_encoder_holders)
HLD_BOSS_H = 3.0        # бобышки board_holder
HLD_WALL = 3.0          # толщина пластины board_holder
HLD_PLATE_X = 28.0      # пластина board_holder (чип в центре)
HLD_PLATE_Y = 21.0
HLD_TAB_W = 10.0        # лапка с 2 слотами M3 (центры слотов ±10, y=-15.5)
# верх полки: холдер ВВЕРХ НОГАМИ лапкой на полку, чип свисает вниз на ось
SHELF_TOP_Z = MAG_TOP_Z + AIR_GAP + CHIP_T + BRD_T + HLD_BOSS_H   # 81.7 мир
SHELF_T = 6.0           # толщина полки
SHELF_W = 28.0          # ширина полки/стойки (X) = ширина лапки холдера
SHELF_Y_FRONT = -12.0   # передний край полки (плата 22мм свисает до y=-11 →
                        #   1мм зазора; лапка нависает на 1.5мм — не страшно)
POST_Y_FRONT = -17.0    # стойка 8×28 у заднего края фланца
POST_Y_BACK = -25.0
PILOT_XY = (10.0, -15.5)   # пилоты M3 ±x, y (= слоты лапки board_holder)
PILOT_DEPTH = 8.0

SEG = 96                # фасеты полных окружностей
OUTDIR = Path(__file__).parent / "stl"

CENTER_DIST = RING_PITCH_R + PIN_PITCH_R    # 240 — ось мотора от оси азимута


# ============================ ХЕЛПЕРЫ ============================
def extrude(poly2d, h, z0=0.0):
    m = trimesh.creation.extrude_polygon(poly2d, height=h)
    if z0:
        m.apply_translation([0, 0, z0])
    return m


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


def rotz(ang_deg):
    return trimesh.transformations.rotation_matrix(math.radians(ang_deg), [0, 0, 1])


def slot_cutter(travel, r, h, T=None):
    """Слот со скруглёнными концами вдоль X: ход = travel (центры на ±travel/2)."""
    body = box(travel, 2 * r, h)
    c1 = cyl(r, h, seg=48, T=tr(-travel / 2, 0, 0))
    c2 = cyl(r, h, seg=48, T=tr(travel / 2, 0, 0))
    s = body.union([c1, c2])
    if T is not None:
        s.apply_transform(T)
    return s


def csk_cutter(rs, rc, z_top, z_bot=-1.0):
    """Потай 90°: стержень Ø2rs снизу + конус до Ø2rc на z_top (одно тело
    вращения — приём из generate_rocker_azdrive против sliver-граней)."""
    z_meet = z_top - (rc - rs)
    profile = np.array([[0.0, z_bot], [rs, z_bot], [rs, z_meet],
                        [rc + 1.0, z_top + 1.0], [0.0, z_top + 1.0]])
    return trimesh.creation.revolve(profile, sections=48)


def cone_solid(r0, z0, r1, z1):
    """Сплошной усечённый конус (тело вращения от оси)."""
    profile = np.array([[0.0, z0], [r0, z0], [r1, z1], [0.0, z1]])
    return trimesh.creation.revolve(profile, sections=SEG)


def csk_slot_cutter(travel, rs, rc, z_top, h, T=None):
    """Потайной СЛОТ вдоль X: сквозной слот + V-жёлоб 90° (= выпуклая
    оболочка двух конусов-потаев — конус выпуклый, hull честный)."""
    shank = slot_cutter(travel, rs, h)
    z_meet = z_top - (rc - rs)
    cones = []
    for sx in (-1, 1):
        c = cone_solid(rs, z_meet, rc + 1.0, z_top + 1.0)
        c.apply_translation([sx * travel / 2, 0, 0])
        cones.append(c)
    trough = cones[0].union(cones[1]).convex_hull
    s = shank.union(trough)
    if T is not None:
        s.apply_transform(T)
    return s


def finish(mesh, name):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    # Сварка вершин на 1e-5 ДО валидации: manifold на пересечении колодца
    # доступа с конусом-фаской (обе поверхности — тела вращения) оставляет
    # пары вершин в ~5e-7 друг от друга; validate убивает sliver-грань и
    # дырявит меш. Грубая сварка схлопывает sliver до честного ребра.
    mesh.merge_vertices(digits_vertex=5)
    mesh.process(validate=True)
    out = OUTDIR / f"{name}.stl"
    mesh.export(out)
    bb = mesh.bounds
    print(f"  {name}.stl  watertight={mesh.is_watertight}  vol={mesh.volume/1000:.2f}cm³  "
          f"bbox={bb[1,0]-bb[0,0]:.0f}×{bb[1,1]-bb[0,1]:.0f}×{bb[1,2]-bb[0,2]:.0f}mm")
    return mesh


# ============================ 1. ВТУЛКА ОСИ ============================
def rocker_hub_ground():
    """Цилиндр Ø70 z=0..24 на доске, задаёт ось: бор M10 Ø10.6 насквозь,
    гекс-карман гайки СНИЗУ (болт идёт снизу сквозь доску и тянет гайку —
    втулка зажата). Верх ПЛОСКИЙ (над ним на z=25 проходит диск, болт — в
    его Ø11). 3 уха-лепестка (вершина R45) с потайными саморезами на 120°.
    Печать ВЕРХОМ ВНИЗ (STL уже перевёрнут): карман и зенковки открываются
    вверх; над ушами (в печати — ПОД ними) — конус-фаска 45°, к головкам —
    вертикальные колодцы Ø9.5 сквозь фаску."""
    body = cyl(HUB_OD / 2, HUB_H, T=tr(0, 0, HUB_H / 2))

    # Уши + конус-фаска над ними (кусок конуса, обрезанный лепестком)
    cone = cone_solid(EAR_CONE_R0, EAR_T, HUB_OD / 2,
                      EAR_T + (EAR_CONE_R0 - HUB_OD / 2))
    add = []
    for ang in EAR_ANGLES:
        a = math.radians(ang)
        cx, cy = EAR_LOBE_CTR * math.cos(a), EAR_LOBE_CTR * math.sin(a)
        add.append(cyl(EAR_LOBE_R, EAR_T, T=tr(cx, cy, EAR_T / 2)))
        prism = cyl(EAR_LOBE_R, 20, T=tr(cx, cy, 10))
        add.append(cone.intersection(prism))
    part = body.union(add)

    # Резаки: бор M10, гекс-карман снизу, потаи + колодцы доступа, фаска кромки
    cutters = [cyl(M10_CLR / 2, HUB_H + 2, T=tr(0, 0, HUB_H / 2)),
               cyl(NUT10_AF / math.sqrt(3), NUT10_DEPTH + 1, seg=6,
                   T=tr(0, 0, (NUT10_DEPTH + 1) / 2 - 1))]
    for ang in EAR_ANGLES:
        a = math.radians(ang)
        hx, hy = EAR_HOLE_R * math.cos(a), EAR_HOLE_R * math.sin(a)
        # потай + колодец доступа сквозь фаску — ОДНИМ телом вращения
        # (коаксиальные конус и цилиндр по отдельности дают sliver-грани)
        rs, rc, ra = WOOD_D / 2, WOOD_CSK_D / 2, ACCESS_D / 2
        z_meet = EAR_T - (rc - rs)      # конус 45°: Ø9 ровно на верхе уха…
        z_acc = z_meet + (ra - rs)      # …и дальше тем же конусом до Ø9.5
        profile = np.array([[0.0, -1.0], [rs, -1.0], [rs, z_meet],
                            [ra, z_acc], [ra, 18.0], [0.0, 18.0]])
        csk = trimesh.creation.revolve(profile, sections=48)
        csk.apply_translation([hx, hy, 0])
        cutters.append(csk)
    # фаска 45° верхней кромки (в печати — кромка у стола)
    ring = cyl(HUB_OD / 2 + 1.5, 2.5, T=tr(0, 0, HUB_H - 0.25))
    keep = cone_solid(HUB_OD / 2 + RIM_CHAMF, HUB_H - 2 * RIM_CHAMF,
                      HUB_OD / 2 - 2 * RIM_CHAMF, HUB_H + RIM_CHAMF)
    cutters.append(ring.difference(keep))
    part = part.difference(cutters)

    # Перевернуть для печати плоским верхом вниз
    part.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0]))
    part.apply_translation([0, 0, HUB_H])
    return finish(part, "Rocker_hub_ground")


# ============================ 2. СЕДЛО ВЕНЦА ============================
def rocker_ring_saddle():
    """Блок 44×32×12 (X — радиально, центр седла на R210 от оси). Сверху
    гребень 3×2 мм, НАРУЖНАЯ грань — дуга R200 = внутренняя кромка тела
    венца (регистрация кольца по радиусу). Крепёж: радиальный потайной
    слот в центре (юстировка до укладки кольца) + круглое потайное Ø4.4
    снаружи кольца (фиксация при уложенном кольце). Печатать ×3."""
    base = box(SAD_L, SAD_W, SAD_H, T=tr(0, 0, SAD_H / 2))

    # Гребень: кольцо R197..R200 вокруг оси азимута (она в локальных (-210,0))
    axis = Point(-SAD_R, 0)
    ann = axis.buffer(BODY_R_IN, quad_segs=256).difference(
        axis.buffer(BODY_R_IN - RIDGE_W, quad_segs=256))
    ridge2d = ann.intersection(shp_box(-SAD_L / 2, -SAD_W / 2, SAD_L / 2, SAD_W / 2))
    part = base.union(extrude(ridge2d, RIDGE_H, z0=SAD_H))

    travel = SAD_SLOT_LEN - WOOD_D          # полная длина слота 12
    slot = csk_slot_cutter(travel, WOOD_D / 2, WOOD_CSK_D / 2, SAD_H, SAD_H + 2,
                           T=tr(SAD_SLOT_X, 0, SAD_H / 2))
    hole = csk_cutter(WOOD_D / 2, WOOD_CSK_D / 2, SAD_H)
    hole.apply_translation([SAD_HOLE_X, 0, 0])
    part = part.difference([slot, hole])
    return finish(part, "Rocker_ring_saddle")


# ============================ 3. ПЛИТА МОТОРА ============================
def rocker_az_motor_plate():
    """Плита 90×80×6 на верху диска (мир z=37..43) над выпилом в его краю.
    NEMA17 сверху в кармане-регистраторе 42.5×42.5×1, вал вниз сквозь
    центральное Ø23 (пилот Ø22 + запас юстировки). 4 радиальных слота M3
    (ход ±4) на квадрате 31×31 + 4 потайных радиальных слота саморезов к
    диску (ход ±6). X — радиально (ось мотора ставится на R240 от оси)."""
    part = box(MP_L, MP_W, MP_T, T=tr(0, 0, MP_T / 2))

    cutters = [cyl(MP_CTR_HOLE / 2, MP_T + 2, T=tr(0, 0, MP_T / 2)),
               box(POCKET_W, POCKET_W, POCKET_DEEP + 1,
                   T=tr(0, 0, MP_T + 0.5 - POCKET_DEEP / 2))]
    for sx in (-1, 1):
        for sy in (-1, 1):
            cutters.append(slot_cutter(M3_TRAVEL, M3_CLR / 2, MP_T + 2,
                                       T=tr(sx * NEMA_SQ / 2, sy * NEMA_SQ / 2, MP_T / 2)))
            cutters.append(csk_slot_cutter(WS_TRAVEL, WOOD_D / 2, WOOD_CSK_D / 2,
                                           MP_T, MP_T + 2,
                                           T=tr(sx * WS_POS[0], sy * WS_POS[1], MP_T / 2)))
    part = part.difference(cutters)
    return finish(part, "Rocker_az_motor_plate")


# ============================ 4. ШЕСТЕРНЯ ПРЯМАЯ ============================
def rocker_pinion_direct():
    """16T модуль 2 (зубья — импорт из generate_rocker_azdrive), венец 12мм
    БЕЗ ступицы. Бор Ø5.2 с D-лыской (хорда на 2.1 от центра — лыска вала
    NEMA17 на 2.0 → 0.1 зазора, лыска смотрит на фиксатор). Радиальный M3
    в гайку в вертикальном пазу (вставка сбоку-снизу ИЛИ сверху — паз
    сквозной по высоте, он внутри корня зубьев и зацеплению не мешает).
    Зубья повёрнуты на полшага, чтобы фиксатор выходил во впадину (лёгкие
    царапины по бокам впадины ≪ бокового зазора 0.3 венца)."""
    half_w = math.pi * MODULE / 4.0
    core = Polygon([(PIN_ROOT_R * math.cos(a), PIN_ROOT_R * math.sin(a))
                    for a in np.linspace(0, 2 * math.pi, SEG_CIRC, endpoint=False)])
    teeth = [tooth_poly(PIN_PITCH_R, PIN_TIP_R, PIN_ROOT_R, half_w,
                        (k + 0.5) * 360.0 / PIN_TEETH) for k in range(PIN_TEETH)]
    part = extrude(unary_union([core] + teeth), PIN_FACE)

    # Бор Ø5.2 минус сегмент-лыска (круг ∩ полуплоскость x ≤ 2.1)
    bore2d = Point(0, 0).buffer(PIN_BORE_D / 2, quad_segs=48).intersection(
        shp_box(-4, -4, PIN_BORE_D / 2 - FLAT_DEPTH, 4))
    bore = extrude(bore2d, PIN_FACE + 2, z0=-1)

    # Радиальный фиксатор вдоль +X (в лыску), z=SET_Z (в зоне хвата вала)
    setscrew = cyl(SET_HOLE / 2, 16, seg=32)
    setscrew.apply_transform(trimesh.transformations.rotation_matrix(
        math.pi / 2, [0, 1, 0]))
    setscrew.apply_translation([10.0, 0, SET_Z])

    # Вертикальный паз гайки: сквозной по высоте (грани держат от прокрутки,
    # затяжка прижимает гайку к наружной стенке паза; вставка снизу = «из-под
    # выпила», как просили, или сверху — как удобнее)
    nut_slot = box(NUT3_T, NUT3_AF, PIN_FACE + 2, T=tr(NUT_R_CTR, 0, PIN_FACE / 2))

    part = part.difference([bore, setscrew, nut_slot])
    return finish(part, "Rocker_pinion_16T_direct")


# ============================ 5. СТОЙКА-ВТУЛКА ЭНКОДЕРА ============================
def rocker_pivot_flange():
    """Фланец 50×50×6 саморезами к ВЕРХУ диска (мир z=37), втулка Ø22×20
    бором Ø10.6 вверх по болту — подшипник вращения диска. Сзади (−Y)
    стойка до полки: на полку ВВЕРХ НОГАМИ ложится лапка board_holder
    (2 пилота M3 Ø2.7 на ±10, чип оказывается на оси M10, гранью ВНИЗ,
    в AIR_GAP над магнитом). Высота полки — от MAG_TOP_Z (менять там!).
    Под свесом полки — клин 45°, печать без поддержек (фланец на столе,
    бор вертикальный). Локальный z=0 = мир 37 (верх диска)."""
    shelf_top = SHELF_TOP_Z - DISC_TOP_Z            # 44.7 локально
    shelf_bot = shelf_top - SHELF_T                 # 38.7
    wedge_z0 = shelf_bot - (SHELF_Y_FRONT - POST_Y_FRONT)   # 45°: 33.7

    part = box(FL_SQ, FL_SQ, FL_T, T=tr(0, 0, FL_T / 2))
    part = part.union(cyl(BUSH_OD / 2, BUSH_H, T=tr(0, 0, BUSH_H / 2)))

    # Стойка + клин + полка одним профилем в плоскости (Y,Z), экструзия по X
    prof = Polygon([(POST_Y_BACK, 0), (POST_Y_FRONT, 0),
                    (POST_Y_FRONT, wedge_z0), (SHELF_Y_FRONT, shelf_bot),
                    (SHELF_Y_FRONT, shelf_top), (POST_Y_BACK, shelf_top)])
    post = trimesh.creation.extrude_polygon(prof, height=SHELF_W)
    # локальные оси профиля (x=Y, y=Z, z=X) → мировые
    M = np.array([[0, 0, 1, -SHELF_W / 2],
                  [1, 0, 0, 0],
                  [0, 1, 0, 0],
                  [0, 0, 0, 1.0]])
    post.apply_transform(M)
    part = part.union(post)

    # Резаки: бор, 4 потая к диску, 2 пилота M3 в полке
    cutters = [cyl(PIV_BORE / 2, BUSH_H + 2, T=tr(0, 0, BUSH_H / 2))]
    for sx in (-1, 1):
        for sy in (-1, 1):
            csk = csk_cutter(WOOD_D / 2, WOOD_CSK_D / 2, FL_T)
            csk.apply_translation([sx * FL_SCREW_XY, sy * FL_SCREW_XY, 0])
            cutters.append(csk)
    for sx in (-1, 1):
        cutters.append(cyl(M3_PILOT / 2, PILOT_DEPTH + 1, seg=32,
                           T=tr(sx * PILOT_XY[0], PILOT_XY[1],
                                shelf_top + 1 - (PILOT_DEPTH + 1) / 2)))
    part = part.difference(cutters)
    return finish(part, "Rocker_pivot_flange")


def main():
    print("Генерация стендового азимутального комплекта…")
    print(f"  венец z={RING_Z0:.0f}..{RING_Z0+10:.0f} на 3 сёдлах, диск "
          f"z={DISC_BOT_Z:.0f}..{DISC_TOP_Z:.0f}, ось мотора на R{CENTER_DIST:.0f}")
    print(f"  полка энкодера: верх магнита z={MAG_TOP_Z:.0f} + зазор {AIR_GAP:.0f} "
          f"→ верх полки z={SHELF_TOP_Z:.1f} (менять MAG_TOP_Z)")
    rocker_hub_ground()
    rocker_ring_saddle()
    rocker_az_motor_plate()
    rocker_pinion_direct()
    rocker_pivot_flange()
    print(f"\nГотово → {OUTDIR}")
    print("Количества: втулка ×1, седло ×3, плита ×1, шестерня ×1, стойка ×1.")
    print("Втулка уже перевёрнута для печати (плоским верхом на стол).")


if __name__ == "__main__":
    main()
