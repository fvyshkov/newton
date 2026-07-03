#!/usr/bin/env python3
"""
Азимутальный зубчатый венец рокера + шестерня (GoTo, Этап 2).

Генерит 3 бинарных STL в truss/stl/ через CSG (trimesh + manifold3d):

  1. Rocker_ring_segment.stl — сегмент 45° внешнего зубчатого венца
     (модуль 2, 224 зуба всего = 28 на сегмент, делительный Ø448мм).
     8 одинаковых сегментов скручиваются в полное кольцо через
     полунахлёстные замки (half-lap) с 2×M3 на каждом стыке.
     Плюс 3 потайных M4 на сегмент — крепление к лучам рокера.
     Сегмент влезает на стол 220×220 (хорда 45° ≈ 174мм — см. bbox).
  2. Rocker_pinion_16T.stl — шестерня 16T модуль 2, венец 12мм,
     бор Ø8 (+0.2), ступица Ø20×8 с M3-фиксатором в карман под гайку
     (идея кармана — из truss/stl/generate_truss_socket.py).
  3. Rocker_mesh_test.stl — тест-купон: дуга венца на 5 зубов на
     плоском основании + вилка-держатель оси шестерни (ось = болт М8 /
     пруток Ø8). Шестерня печатается отдельно, вставляется, крутится
     рукой — проверка зацепления ДО печати всех 8 сегментов.

Профиль зуба — симметричная ТРАПЕЦИЯ, аппроксимирующая эвольвенту
(угол профиля 20°, головка 1.0·m, ножка 1.25·m, плоская вершинка,
0.3мм припуск на боковой зазор на венце). Для 41:1 на малой скорости
с энкодером, замыкающим петлю, — этого достаточно; никаких gear-либ,
зубья строятся булевым объединением экструзий 2D-полигонов по кругу.

Передача: 224/16 = 14:1 по венцу (полное 41:1 — с редуктором мотора).
"""
import math
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import Polygon
from shapely.ops import unary_union

# ============================ ПАРАМЕТРЫ ============================
# --- Зацепление (общие для венца и шестерни) ---
MODULE = 2.0            # модуль, мм
PRESSURE_DEG = 20.0     # угол профиля трапеции (≈ угол зацепления)
ADDENDUM = 1.0 * MODULE     # головка зуба, мм
DEDENDUM = 1.25 * MODULE    # ножка зуба, мм
BACKLASH = 0.30         # припуск на боковой зазор (снимается с зубьев ВЕНЦА)
TOOTH_EMBED = 0.5       # заглубление трапеции под корень (чистый union), мм

# --- Венец (внешнее зацепление, зубья наружу) ---
RING_TEETH = 224        # зубьев всего
N_SEGMENTS = 4          # сегментов в кольце (Bambu H2D: стол 350×320)
TEETH_PER_SEG = RING_TEETH // N_SEGMENTS   # 56
SEG_ANG = 360.0 / N_SEGMENTS               # 45°
RING_PITCH_R = MODULE * RING_TEETH / 2.0   # 224 (делительный R)
RING_TIP_R = RING_PITCH_R + ADDENDUM       # 226
RING_ROOT_R = RING_PITCH_R - DEDENDUM      # 221.5
RIM_H = 10.0            # высота зубчатого обода (и зубьев), мм
RIM_R_IN = RING_ROOT_R - 4.0               # внутренний R обода (217.5)
BODY_T = 8.0            # толщина плоского кольцевого тела, мм
BODY_R_IN = 200.0       # внутренний R тела
BODY_R_OUT = RING_ROOT_R + 0.5             # перекрытие с ободом (чистый union)

# --- Замок сегментов (half-lap + 2×M3 на стык) ---
LUG_ANG = 4.0           # угловая длина нахлёста, ° (≈14.7мм дуги на R210)
LUG_R_IN = 202.0        # радиальный размах языка
LUG_R_OUT = 216.0       #   (не задевает обод соседа: < RIM_R_IN)
LUG_Z_BOT = 4.0         # язык = верхняя половина: z 4..8
POCKET_Z_BOT = 3.8      # карман соседа чуть глубже (0.2 зазор)
LAP_CLR_R = 0.2         # радиальный зазор кармана, мм
LAP_CLR_T = 0.2         # тангенциальный зазор кармана, мм (переводится в °)
M3_HOLE = 3.4           # Ø сквозных M3 в замке
M3_R1, M3_R2 = 206.0, 212.0   # радиусы двух M3 стыка

# --- Крепление к лучам рокера (3×M4 потай на сегмент) ---
M4_HOLE = 4.5           # Ø сквозного M4
M4_CSK_D = 9.0          # Ø зенковки 90° под потайную головку
M4_R = 210.0            # радиус окружности отверстий
M4_ANGLES = (-15.0, 0.0, 15.0)   # углы в системе сегмента, °

# --- Шестерня 16T ---
PIN_TEETH = 16
PIN_PITCH_R = MODULE * PIN_TEETH / 2.0     # 16
PIN_TIP_R = PIN_PITCH_R + ADDENDUM         # 18
PIN_ROOT_R = PIN_PITCH_R - DEDENDUM        # 13.5
PIN_FACE = 12.0         # ширина венца шестерни, мм
PIN_BORE = 8.0 + 0.2    # бор под вал Ø8 (+0.2 посадка)
HUB_D = 20.0            # Ø ступицы
HUB_H = 8.0             # высота ступицы
SET_HOLE = 3.2          # Ø радиального отверстия под M3-фиксатор
SET_Z = PIN_FACE + HUB_H / 2.0 + 0.5       # ось фиксатора, z=16.5
NUT_AF = 5.5            # M3 гайка «под ключ»
NUT_T = 2.4             # толщина гайки
NUT_SLOT_W = NUT_AF + 0.3    # паз-карман: тангенциально (грани держат от прокрутки)
NUT_SLOT_T = NUT_T + 0.4     # паз: радиально (по оси винта)
NUT_R_CTR = 6.6         # радиус центра гайки (наружная стенка 2мм держит реакцию)

# --- Тест-купон ---
TEST_TEETH = 5          # зубьев в дуге
TEST_BASE_T = 5.0       # толщина основания
CENTER_DIST = RING_PITCH_R + PIN_PITCH_R   # 240 — межосевое
BOSS_H = 2.0            # подпятник шестерни (зубья 2..14 против дуги 0..10)

SEG_ARC = 64            # точек на дугах секторов (>=64)
SEG_CIRC = 96           # фасеты полных окружностей
OUTDIR = Path(__file__).parent / "stl"


# ============================ ХЕЛПЕРЫ ============================
def rot2d(pts, ang_deg):
    a = math.radians(ang_deg)
    c, s = math.cos(a), math.sin(a)
    return [(c * x - s * y, s * x + c * y) for x, y in pts]


def tooth_poly(pitch_r, tip_r, root_r, half_w_pitch, ang_deg):
    """Трапеция зуба внешнего зацепления, зуб наружу вдоль радиуса.
    half_w_pitch — полутолщина зуба на делительном радиусе (тангенциально).
    Тангенциальное смещение боковин линейно по радиусу (аппроксимация)."""
    tan_a = math.tan(math.radians(PRESSURE_DEG))
    r0 = root_r - TOOTH_EMBED
    w0 = half_w_pitch + (pitch_r - r0) * tan_a
    w1 = half_w_pitch - (tip_r - pitch_r) * tan_a
    assert w1 > 0.3, f"вершинка зуба слишком острая: {2*w1:.2f}мм"
    pts = [(r0, -w0), (tip_r, -w1), (tip_r, w1), (r0, w0)]
    return Polygon(rot2d(pts, ang_deg))


def sector_annulus(r_in, r_out, a0_deg, a1_deg, n=SEG_ARC):
    """2D сектор кольца (полигон), дуги по n точек."""
    angs = np.linspace(math.radians(a0_deg), math.radians(a1_deg), n)
    outer = [(r_out * math.cos(a), r_out * math.sin(a)) for a in angs]
    inner = [(r_in * math.cos(a), r_in * math.sin(a)) for a in angs[::-1]]
    return Polygon(outer + inner)


def extrude(poly2d, h, z0=0.0):
    m = trimesh.creation.extrude_polygon(poly2d, height=h)
    if z0:
        m.apply_translation([0, 0, z0])
    return m


def cyl(r, h, seg=SEG_CIRC, T=None):
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


def ring_arc_teeth(a0_deg, n_teeth, height):
    """Дуга обода венца с n_teeth зубьями, начиная от угла a0 (z=0..height).
    Зубья центрированы в своих шагах — стык сегментов попадает во впадину."""
    pitch_ang = 360.0 / RING_TEETH
    half_w = (math.pi * MODULE / 2.0 - BACKLASH) / 2.0   # утонение на зазор
    rim = sector_annulus(RIM_R_IN, RING_ROOT_R, a0_deg, a0_deg + n_teeth * pitch_ang)
    teeth = [tooth_poly(RING_PITCH_R, RING_TIP_R, RING_ROOT_R, half_w,
                        a0_deg + (k + 0.5) * pitch_ang) for k in range(n_teeth)]
    return extrude(unary_union([rim] + teeth), height)


def finish(mesh, name):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    mesh.process(validate=True)
    out = OUTDIR / f"{name}.stl"
    mesh.export(out)
    bb = mesh.bounds
    print(f"  {name}.stl  watertight={mesh.is_watertight}  vol={mesh.volume/1000:.2f}cm³  "
          f"bbox={bb[1,0]-bb[0,0]:.0f}×{bb[1,1]-bb[0,1]:.0f}×{bb[1,2]-bb[0,2]:.0f}mm")
    return mesh


# ============================ 1. СЕГМЕНТ ВЕНЦА ============================
def rocker_ring_segment():
    """Сегмент 45° = 28 зубьев. Обод с зубьями z=0..10, тело z=0..8.
    Конец A (+22.5°): язык-нахлёст (верхняя половина, z=4..8) торчит наружу.
    Конец B (−22.5°): карман под язык соседа (снята верхняя половина тела).
    2×M3 сквозь каждый стык (одни координаты в мире у языка и кармана).
    3×M4 потай сверху — к лучам рокера. Все 8 сегментов ОДИНАКОВЫЕ."""
    half = SEG_ANG / 2.0   # 22.5

    # Обод с зубьями + плоское тело
    rim = ring_arc_teeth(-half, TEETH_PER_SEG, RIM_H)
    body = extrude(sector_annulus(BODY_R_IN, BODY_R_OUT, -half, half), BODY_T)
    part = rim.union(body)

    # Язык на конце A: сектор (22.5°..26.5°), z=4..8
    lug = extrude(sector_annulus(LUG_R_IN, LUG_R_OUT, half, half + LUG_ANG),
                  BODY_T - LUG_Z_BOT, z0=LUG_Z_BOT)
    part = part.union(lug)

    # Карман на конце B: чуть шире/глубже языка, насквозь через верх тела
    clr_ang = math.degrees(LAP_CLR_T / M4_R)   # тангенциальный зазор в °
    pocket = extrude(sector_annulus(LUG_R_IN - LAP_CLR_R, LUG_R_OUT + LAP_CLR_R,
                                    -half - clr_ang, -half + LUG_ANG + clr_ang),
                     BODY_T - POCKET_Z_BOT + 1.0, z0=POCKET_Z_BOT)
    part = part.difference(pocket)

    # M3 стыков: конец A — сквозь язык; конец B — сквозь дно кармана.
    # Углы подобраны так, что при сборке (сосед повёрнут на 45°) совпадают.
    m3 = []
    for ang in (half + LUG_ANG / 2.0, -half + LUG_ANG / 2.0):
        a = math.radians(ang)
        for r in (M3_R1, M3_R2):
            m3.append(cyl(M3_HOLE / 2, RIM_H + 2, seg=32,
                          T=tr(r * math.cos(a), r * math.sin(a), RIM_H / 2)))
    part = part.difference(m3)

    # M4 потай (зенковка 90° сверху, головка заподлицо с z=8).
    # Резак — ОДНО тело вращения «стержень + конус»: коаксиальные цилиндр и
    # конус по отдельности дают почти совпадающие вершины на линии их
    # пересечения → sliver-грани → не watertight после merge_vertices.
    rs = M4_HOLE / 2.0
    rc = M4_CSK_D / 2.0
    z_meet = BODY_T - (rc - rs)          # конус 90° встречает стержень (5.75)
    profile = np.array([[0.0, -1.0], [rs, -1.0], [rs, z_meet],
                        [rc + 1.0, BODY_T + 1.0], [0.0, BODY_T + 1.0]])
    m4 = []
    for ang in M4_ANGLES:
        a = math.radians(ang)
        csk = trimesh.creation.revolve(profile, sections=48)
        csk.apply_translation([M4_R * math.cos(a), M4_R * math.sin(a), 0])
        m4.append(csk)
    part = part.difference(m4)

    # Повернуть на −LUG_ANG/2 (симметрия с языком) и отцентрировать XY на столе
    part.apply_transform(trimesh.transformations.rotation_matrix(
        math.radians(-LUG_ANG / 2.0), [0, 0, 1]))
    bb = part.bounds
    part.apply_translation([-(bb[0, 0] + bb[1, 0]) / 2, -(bb[0, 1] + bb[1, 1]) / 2, 0])
    return finish(part, "Rocker_ring_segment")


# ============================ 2. ШЕСТЕРНЯ 16T ============================
def rocker_pinion():
    """16T модуль 2. Венец z=0..12 (печатается зубьями вниз), ступица Ø20
    z=12..20. Бор Ø8.2 насквозь. Радиальный M3-фиксатор на z=16.5 давит на
    вал через гайку в пазу-кармане (гайка вставляется сверху ступицы; идея
    захвата гайки — из generate_truss_socket.py, тут паз вместо сквозного
    hex: реакция затяжки прижимает гайку к НАРУЖНОЙ стенке паза)."""
    half_w = math.pi * MODULE / 4.0   # номинальная полутолщина (зазор дан венцом)
    core = Polygon([(PIN_ROOT_R * math.cos(a), PIN_ROOT_R * math.sin(a))
                    for a in np.linspace(0, 2 * math.pi, SEG_CIRC, endpoint=False)])
    teeth = [tooth_poly(PIN_PITCH_R, PIN_TIP_R, PIN_ROOT_R, half_w,
                        k * 360.0 / PIN_TEETH) for k in range(PIN_TEETH)]
    part = extrude(unary_union([core] + teeth), PIN_FACE)

    hub = cyl(HUB_D / 2, HUB_H, T=tr(0, 0, PIN_FACE + HUB_H / 2 - 0.005))
    part = part.union(hub)

    total_h = PIN_FACE + HUB_H
    bore = cyl(PIN_BORE / 2, total_h + 2, T=tr(0, 0, total_h / 2))

    # Радиальное отверстие фиксатора вдоль +X (ось по Z → повернуть на Y)
    setscrew = cyl(SET_HOLE / 2, HUB_D, seg=32)
    setscrew.apply_transform(trimesh.transformations.rotation_matrix(
        math.pi / 2, [0, 1, 0]))
    setscrew.apply_translation([HUB_D / 4, 0, SET_Z])

    # Паз под гайку: сверху ступицы вниз, до захвата гайки на оси винта
    slot_top = total_h + 1.0
    slot_bot = SET_Z - (NUT_AF / math.cos(math.radians(30)) / 2 + 0.2)  # низ по углам гайки
    nut_slot = box(NUT_SLOT_T, NUT_SLOT_W, slot_top - slot_bot,
                   T=tr(NUT_R_CTR, 0, (slot_top + slot_bot) / 2))

    part = part.difference([bore, setscrew, nut_slot])
    return finish(part, "Rocker_pinion_16T")


# ============================ 3. ТЕСТ-КУПОН ============================
def rocker_mesh_test():
    """Дуга венца на 5 зубьев + вилка оси шестерни на одном основании.
    Межосевое = 224+16 = 240мм выдержано геометрией купона. Ось — болт M8
    или пруток Ø8 сквозь верхнее ухо вилки, шестерню и подпятник в основание.
    Шестерня (Rocker_pinion_16T) печатается отдельно и крутится рукой."""
    pitch_ang = 360.0 / RING_TEETH
    a_half = TEST_TEETH * pitch_ang / 2.0   # ±4.02°

    # Дуга венца вокруг +X, центр кольца в (0,0); чуть утоплена в основание
    arc = ring_arc_teeth(-a_half, TEST_TEETH, RIM_H + 0.5)
    arc.apply_translation([0, 0, -0.5])

    # Основание: от дуги до колонны вилки
    base = box(58, 44, TEST_BASE_T, T=tr(242, 0, -TEST_BASE_T / 2))
    part = base.union(arc)

    # Подпятник шестерни (зубья соседа z=2..14 против дуги z=0..10)
    boss = cyl(8.0, BOSS_H + 1, T=tr(CENTER_DIST, 0, (BOSS_H + 1) / 2 - 1))
    part = part.union(boss)

    # Колонна вилки — за вершинами зубьев шестерни (tip R18 от оси 240)
    col = box(10, 16, 34, T=tr(264, 0, 34 / 2 - 2))
    part = part.union(col)
    # Верхнее ухо над осью: низ z=26 (шестерня+ступица до z=22 → зазор 4мм)
    arm = box(36, 16, 6, T=tr(251, 0, 29))
    part = part.union(arm)

    # Ось Ø8.2: сквозь ухо, воздух и подпятник в основание
    axle = cyl(PIN_BORE / 2, 42, seg=48, T=tr(CENTER_DIST, 0, 13))
    part = part.difference(axle)

    part.apply_translation([-242, 0, TEST_BASE_T])   # к началу координат, низ z=0
    return finish(part, "Rocker_mesh_test")


def main():
    print("Генерация азимутального привода рокера…")
    print(f"  венец: m={MODULE} z={RING_TEETH} (делительный Ø{2*RING_PITCH_R:.0f}, "
          f"вершины Ø{2*RING_TIP_R:.0f}), {N_SEGMENTS}×45° по {TEETH_PER_SEG} зубьев")
    print(f"  передача венец/шестерня: {RING_TEETH}/{PIN_TEETH} = "
          f"{RING_TEETH/PIN_TEETH:.0f}:1, межосевое {CENTER_DIST:.0f}мм")
    rocker_ring_segment()
    rocker_pinion()
    rocker_mesh_test()
    print(f"\nГотово → {OUTDIR}")
    print("Сначала печатаем Rocker_mesh_test + шестерню, проверяем зацепление,")
    print("потом 4× Rocker_ring_segment (сегмент 90° ~320×92мм — стол H2D 350×320).")


if __name__ == "__main__":
    main()
