#!/usr/bin/env python3
"""
Азимут v2 — ОСЕВОЙ («ленивая Сюзанна») поворотный узел вместо бокового венца.

Альтернатива существующему `generate_rocker_azdrive.py`. Два плоских кольца лежат
друг на друге торцами (упорный подшипник скольжения по тефлону), НЕ вложены сбоку.

Зацепление, модуль, шестерня, магнит энкодера — 1:1 из существующего азимута
(модуль 2, венец 224 зуба Ø448, шестерня 16T, магнит Ø6×2.5). Меняется только
механика опоры и привода.

Система координат: z=0 — верх фанеры, +z вверх, начало (0,0) — ось азимута.
Пинион на R=CENTER_DIST=240 (межосевое венец+шестерня = 224+16).

СТЕК ПО Z:
   0..8   НЕПОДВИЖНОЕ кольцо (тело), прикручено к фанере 4×M4/сегмент
   8..17  центрирующий БУРТИК по внутренней окружности (R185) неподвижного кольца
   9..17  ВРАЩАЮЩЕЕСЯ кольцо (тело 8 мм), внутр. бортом трётся о буртик
   9..19  зубья вращающегося кольца (обод 10 мм), торчат НАРУЖУ
  ~9      тефлон-пятачки в дне вращающегося кольца → скользят по дорожке неподв.
  17..20  СПАЙДЕР (4 луча) на верху вращающегося кольца → магнит по центру, вниз
 ~15.5    чип AS5048A на неподвижной колонне по центру, смотрит вверх (зазор ~1.2)
   8..18  ШЕСТЕРНЯ 16T на валу Ø5 мотора (перевёрнут осью вниз)
  30..~66 корпус NEMA17 на ПОДСТАВКЕ; прорези-натяг сдвигают мотор по радиусу

Детали (всё печатается, кроме крепежа/тефлона/подшипника-нет):
  1. az2_ring_fixed_seg     ×4  — неподвижное кольцо (сегмент 90°) + буртик
  2. az2_ring_rot_seg       ×4  — вращающееся кольцо (сегмент 90°) + зубья + гнёзда
  3. az2_magnet_spider      ×1  — крестовина магнита (вращается)
  4. az2_encoder_column     ×1  — неподвижная колонна с посадкой платы AS5048A
  5. az2_motor_pedestal     ×1  — подставка мотора (перевёрнут), прорези-натяг
  6. az2_pinion_16T_bore5   ×1  — шестерня 16T под вал Ø5 обычного NEMA17 (уже куплен)

Передача ПРЯМАЯ 14:1 (шестерня прямо на валу NEMA17 — ничего не покупать). Мотор на
подставке, перевёрнут осью вниз (высоту PED_TOP_Z подогнать под длину вала).
Если нужен больший момент/тоньше трекинг — добавить ПЕЧАТНУЮ ступень редукции
(spur 3:1 → 42:1) на уже купленный вал Ø8 + 2×608ZZ (см. README) — тоже без покупок.
"""
import math
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import Polygon
from shapely.ops import unary_union

# ============================ ЗАЦЕПЛЕНИЕ (1:1 из azdrive) ============================
MODULE = 2.0
PRESSURE_DEG = 20.0
ADDENDUM = 1.0 * MODULE          # 2.0
DEDENDUM = 1.25 * MODULE         # 2.5
BACKLASH = 0.30
TOOTH_EMBED = 0.5

RING_TEETH = 224
N_SEG = 4
SEG_ANG = 360.0 / N_SEG          # 90
TEETH_PER_SEG = RING_TEETH // N_SEG   # 56
RING_PITCH_R = MODULE * RING_TEETH / 2.0   # 224
RING_TIP_R = RING_PITCH_R + ADDENDUM       # 226
RING_ROOT_R = RING_PITCH_R - DEDENDUM      # 221.5

PIN_TEETH = 16
PIN_PITCH_R = MODULE * PIN_TEETH / 2.0     # 16
PIN_TIP_R = PIN_PITCH_R + ADDENDUM         # 18
PIN_ROOT_R = PIN_PITCH_R - DEDENDUM        # 13.5
CENTER_DIST = RING_PITCH_R + PIN_PITCH_R   # 240

# ============================ ГЕОМЕТРИЯ КОЛЕЦ ============================
BODY_T = 8.0                     # толщина тела обоих колец
RIM_H = 10.0                     # высота зубчатого обода (зубья)

# --- неподвижное кольцо (низ) ---
FIX_Z0 = 0.0
FIX_Z1 = BODY_T                  # 8
FIX_R_IN = 176.0                 # внутренний край тела
FIX_R_OUT = 218.0                # наружный край (зубьев тут НЕТ)
LIP_R_IN = 180.0                 # буртик: внутренняя стенка
LIP_R_OUT = 185.0                # буртик: наружная стенка = центрирует вращ. кольцо
LIP_Z1 = 17.0                    # верх буртика (перекрывает высоту тела вращ. кольца)
FIX_M4 = 4.5                     # Ø сквозного M4 к фанере
FIX_M4_CSK = 9.0                 # Ø зенковки под потайную головку
FIX_M4_R = 213.0                 # радиус крепёжных отверстий (вне зоны пятачков)
FIX_M4_PER_SEG = (-30.0, 0.0, 30.0)   # 3 болта/сегмент

# --- зазор тефлона ---
PTFE_GAP = 1.0                   # номинальный зазор торцов (тефлон 1.5 → 0.5 проступ)

# --- вращающееся кольцо (верх) ---
ROT_Z0 = FIX_Z1 + PTFE_GAP       # 9
ROT_Z1 = ROT_Z0 + BODY_T         # 17
ROT_RIM_Z1 = ROT_Z0 + RIM_H      # 19
ROT_R_IN = LIP_R_OUT + 0.5       # 185.5 — бортик на буртике (0.5 зазор)
RIM_R_IN = RING_ROOT_R - 4.0     # 217.5 — внутр. R обода зубьев
BODY_R_OUT = RING_ROOT_R + 0.5   # 222.0 — перекрытие тела с ободом

# --- тефлоновые пятачки (в дне вращающегося кольца) ---
PAD_R = 201.0                    # радиус центров пятачков
PAD_N = 24                       # штук по кругу (много, равномерно)
PAD_D = 15.0                     # Ø кармана пятачка
PAD_DEPTH = 1.0                  # глубина кармана (тефлон 1.5 мм → 0.5 проступ)

# --- гнёзда стоек (верх вращающегося кольца) ---
POST_N = 4                       # 4 стойки (по центру каждого сегмента); можно 3
POST_R = 201.0                   # PCD центров стоек: Ø30 босс = R186..216 — внутр. край
                                 # НЕ лезет за борт (R185.5) и на буртик, наруж. до зубьев 1.5мм
POST_TUBE_D = 22.0               # Ø трубки-стойки (та же швабра Ø22)
POST_BORE = POST_TUBE_D + 0.6    # посадка трубки (печать уже номинала)
POST_BOSS_D = 30.0               # Ø бобышки гнезда
POST_BOSS_H = 22.0               # высота бобышки над телом кольца
POST_SET = 3.4                   # радиальный M4-стопор трубки в гнезде

# --- точка крепления спайдера (винт на теле кольца, В СТОРОНЕ от гнезда стойки) ---
SPD_BOSS_D = 12.0
SPD_TAP = 2.5                    # саморез M3 в пластик (самонарез)
SPD_MOUNT_R = 196.0             # радиус точки: на теле, внутр. борт НЕ рвёт (R190>185.5)
SPD_MOUNT_ANG = 30.0            # угол смещения от центра сегмента: уводим ОТ гнезда стойки

# --- замок сегментов (half-lap + 2×M3), общий для обоих колец ---
LAP_ANG = 4.0                    # угловая длина языка, °
LAP_R_IN = 200.0
LAP_R_OUT = 216.0
LAP_Z_BOT = BODY_T / 2.0         # язык = верхняя половина тела (z 4..8 локально)
LAP_CLR_R = 0.2
LAP_CLR_T = 0.2
LAP_M3 = 3.4
LAP_M3_R = (204.0, 212.0)        # два M3 стыка

# ============================ МАГНИТ / ЭНКОДЕР ============================
MAGNET_D = 6.0
MAGNET_H = 2.5
MAG_FIT = 0.20
MAG_RECESS = 0.4
AIR_GAP = 1.2                    # зазор магнит↔чип
CHIP_TOP_Z = 15.5                # верх чипа (посадка платы это обеспечивает)
MAG_FACE_Z = CHIP_TOP_Z + AIR_GAP    # 16.7 — рабочий торец магнита

# плата AS5048A (как в board_holder) — посадка встроена в колонну
BOARD_HOLE_DX = 18.0
BOARD_HOLE_DY = 11.0
BOARD_SELFTAP = 2.2
BOARD_BOSS_OD = 6.0
BOARD_BOSS_H = 3.0
BOARD_WALL = 3.0
CHIP_WIN = 8.0

# ============================ МОТОР / ПОДСТАВКА ============================
NEMA_PITCH = 15.5                # M3 на квадрате 31×31 (полушаг)
NEMA_PILOT_D = 23.0              # окно под буртик Ø22 + вал
NEMA_M3 = 3.4
PED_TOP_Z = 30.0                 # верх подставки = фланец мотора (вал вниз)
PED_PLATE_T = 6.0                # толщина верхней плиты
PED_SLOT_TRAVEL = 3.5            # ±ход прорезей мотора (по радиусу = натяг)
PED_LEG_R_IN = 232.0             # ноги подставки — снаружи венца (tip R226)
PINION_XY = (0.0, -CENTER_DIST)  # ось шестерни/мотора: на −Y, R=240

# --- шестерня 16T под вал Ø5 ОБЫЧНОГО NEMA17 (мотор УЖЕ куплен — ничего не покупать) ---
PIN_FACE = 10.0
PIN_BORE = 5.0 + 0.25            # вал NEMA17 Ø5 (печать уже номинала); стопор на D-флэт
PIN_SET = 3.2                    # радиальный M3-стопор на лыску вала
PIN_SET_Z = PIN_FACE / 2.0
NUT_AF = 5.5
NUT_T = 2.4
NUT_SLOT_W = NUT_AF + 0.3
NUT_SLOT_T = NUT_T + 0.4
NUT_R_CTR = 6.6

SEG_ARC = 64
SEG_CIRC = 96
OUTDIR = Path(__file__).parent / "stl"


# ============================ ХЕЛПЕРЫ (из azdrive) ============================
def rot2d(pts, ang_deg):
    a = math.radians(ang_deg)
    c, s = math.cos(a), math.sin(a)
    return [(c * x - s * y, s * x + c * y) for x, y in pts]


def tooth_poly(pitch_r, tip_r, root_r, half_w_pitch, ang_deg):
    tan_a = math.tan(math.radians(PRESSURE_DEG))
    r0 = root_r - TOOTH_EMBED
    w0 = half_w_pitch + (pitch_r - r0) * tan_a
    w1 = half_w_pitch - (tip_r - pitch_r) * tan_a
    assert w1 > 0.3, f"вершинка зуба слишком острая: {2*w1:.2f}мм"
    pts = [(r0, -w0), (tip_r, -w1), (tip_r, w1), (r0, w0)]
    return Polygon(rot2d(pts, ang_deg))


def sector_annulus(r_in, r_out, a0_deg, a1_deg, n=SEG_ARC):
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


def rotz(deg):
    return trimesh.transformations.rotation_matrix(math.radians(deg), [0, 0, 1])


def roty(deg):
    return trimesh.transformations.rotation_matrix(math.radians(deg), [0, 1, 0])


def ring_arc_teeth(a0_deg, n_teeth, height, z0=0.0):
    """Дуга обода венца с зубьями наружу (как в azdrive)."""
    pitch_ang = 360.0 / RING_TEETH
    half_w = (math.pi * MODULE / 2.0 - BACKLASH) / 2.0
    rim = sector_annulus(RIM_R_IN, RING_ROOT_R, a0_deg, a0_deg + n_teeth * pitch_ang)
    teeth = [tooth_poly(RING_PITCH_R, RING_TIP_R, RING_ROOT_R, half_w,
                        a0_deg + (k + 0.5) * pitch_ang) for k in range(n_teeth)]
    return extrude(unary_union([rim] + teeth), height, z0=z0)


def lap_joint(part, body_z0, body_z1):
    """Half-lap + 2×M3 на обоих концах сегмента 90° (в локальной рамке ±45°).
    Язык = верхняя половина тела на конце A (+45°); карман на конце B (−45°)."""
    half = SEG_ANG / 2.0
    lug_z0 = body_z0 + LAP_Z_BOT
    # язык на конце A
    lug = extrude(sector_annulus(LAP_R_IN, LAP_R_OUT, half, half + LAP_ANG),
                  body_z1 - lug_z0, z0=lug_z0)
    part = part.union(lug)
    # карман на конце B (чуть шире/глубже)
    clr_ang = math.degrees(LAP_CLR_T / LAP_M3_R[0])
    pocket = extrude(sector_annulus(LAP_R_IN - LAP_CLR_R, LAP_R_OUT + LAP_CLR_R,
                                    -half - clr_ang, -half + LAP_ANG + clr_ang),
                     body_z1 - (lug_z0 - 0.2) + 1.0, z0=lug_z0 - 0.2)
    part = part.difference(pocket)
    # 2×M3 на каждом стыке
    m3 = []
    for ang in (half + LAP_ANG / 2.0, -half + LAP_ANG / 2.0):
        a = math.radians(ang)
        for r in LAP_M3_R:
            m3.append(cyl(LAP_M3 / 2, (body_z1 - body_z0) + 4, seg=32,
                          T=tr(r * math.cos(a), r * math.sin(a), (body_z0 + body_z1) / 2)))
    return part.difference(m3)


def finish(mesh, name):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    mesh.process(validate=True)
    out = OUTDIR / f"{name}.stl"
    mesh.export(out)
    bb = mesh.bounds
    print(f"  {name}.stl  watertight={mesh.is_watertight}  vol={mesh.volume/1000:.1f}cm³  "
          f"bbox={bb[1,0]-bb[0,0]:.0f}×{bb[1,1]-bb[0,1]:.0f}×{bb[1,2]-bb[0,2]:.0f}mm")
    return mesh


# ============================ 1. НЕПОДВИЖНОЕ КОЛЬЦО ============================
def ring_fixed_seg():
    """Сегмент 90° неподвижного кольца: плоское тело z0..8 + буртик по ВНУТР.
    окружности (R180..185, z8..17) центрирует вращающееся кольцо. Гладкий верх
    тела = дорожка скольжения (обклеить ламинатом/PET). 3×M4 потай к фанере.
    Наружной стенки-ограничителя НЕТ (зубьям соседнего кольца ничто не мешает)."""
    half = SEG_ANG / 2.0
    body = extrude(sector_annulus(FIX_R_IN, FIX_R_OUT, -half, half), BODY_T)
    lip = extrude(sector_annulus(LIP_R_IN, LIP_R_OUT, -half, half), LIP_Z1 - FIX_Z1,
                  z0=FIX_Z1)
    part = body.union(lip)
    part = lap_joint(part, FIX_Z0, FIX_Z1)

    # 3×M4 потай сверху (головка заподлицо с z=8) — крепёж к фанере
    rs, rc = FIX_M4 / 2.0, FIX_M4_CSK / 2.0
    z_meet = BODY_T - (rc - rs)
    profile = np.array([[0.0, -1.0], [rs, -1.0], [rs, z_meet],
                        [rc + 1.0, BODY_T + 1.0], [0.0, BODY_T + 1.0]])
    csks = []
    for ang in FIX_M4_PER_SEG:
        a = math.radians(ang)
        c = trimesh.creation.revolve(profile, sections=48)
        c.apply_translation([FIX_M4_R * math.cos(a), FIX_M4_R * math.sin(a), 0])
        csks.append(c)
    part = part.difference(csks)

    part.apply_transform(rotz(-LAP_ANG / 2.0))
    bb = part.bounds
    part.apply_translation([-(bb[0, 0] + bb[1, 0]) / 2, -(bb[0, 1] + bb[1, 1]) / 2, 0])
    return finish(part, "az2_ring_fixed_seg")


# ============================ 2. ВРАЩАЮЩЕЕСЯ КОЛЬЦО (венец) ============================
# --- наклонные гнёзда ног башен: хомут Ø30 под трубу Ø22, целит в апекс ---
# Направление ноги = (апекс − угол). Апексы неподвижны (±170,0). Угол на R_LEG —
# ВНУТРЬ от зубьев (R217.5), чтобы хомут Ø30 не трогал зубья/шестерню (нога входит
# в апекс ~1.3° мимо расчёта под R210 — съедается люфтом трубы).
R_LEG = 201.0
APEX_XY = {"R": (170.0, 0.0), "L": (-170.0, 0.0)}
CORNER_Z_V1, APEX_Z_V1 = 82.0, 460.0        # только для расчёта НАКЛОНА
LEG_COLLAR_D = 30.0
LEG_BORE = 22.6
LEG_H = 44.0
LEG_SET = 3.4
_c30, _s30 = math.cos(math.radians(30)), math.sin(math.radians(30))
# 4 РАЗНЫХ сегмента: (имя, центр C, [(base_x, base_y, apex_side)])
ROT_CFGS = [
    ("az2_ring_rot_A_leg30",  0.0,   [(R_LEG * _c30,  R_LEG * _s30, "R")]),   # угол 30 → apexR
    ("az2_ring_rot_B_plain",  90.0,  []),                                     # без ног
    ("az2_ring_rot_C_leg150", 180.0, [(R_LEG * _c30, -R_LEG * _s30, "L")]),   # угол 150 (лок −30) → apexL
    ("az2_ring_rot_D_leg270", 270.0, [(R_LEG, 12.0, "R"), (R_LEG, -12.0, "L")]),  # ведущий: 2 ноги (боры разведены)
]


def _rotz3(deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def cyl_along(r, L, base, d, seg=SEG_CIRC):
    """Цилиндр r×L, ось вдоль единичного d, один торец в base."""
    d = np.asarray(d, float); d = d / np.linalg.norm(d)
    T = trimesh.geometry.align_vectors([0.0, 0.0, 1.0], d)
    c = trimesh.creation.cylinder(radius=r, height=L, sections=seg)
    c.apply_transform(T)
    c.apply_translation(np.asarray(base, float) + d * (L / 2.0))
    return c


def _leg_dir_local(C, base_xy, side):
    """Единичное направление ноги в ЛОКАЛЬНОЙ рамке сегмента (центр C→мир)."""
    cw = _rotz3(C) @ np.array([base_xy[0], base_xy[1], CORNER_Z_V1])
    aw = np.array([APEX_XY[side][0], APEX_XY[side][1], APEX_Z_V1])
    dl = _rotz3(-C) @ (aw - cw)
    return dl / np.linalg.norm(dl)


def ring_rot_seg(name, C, legs):
    """Сегмент 90° венца (вращается): зубья наружу + тефлон-карманы в дне +
    бобышка спайдера + НАКЛОННЫЕ гнёзда ног (0/1/2 по конфигу). Внутр. борт
    R185.5 центрируется буртиком нижнего кольца. 4 сегмента РАЗНЫЕ."""
    half = SEG_ANG / 2.0
    rim = ring_arc_teeth(-half, TEETH_PER_SEG, RIM_H)
    body = extrude(sector_annulus(ROT_R_IN, BODY_R_OUT, -half, half), BODY_T)
    part = rim.union(body)
    part = lap_joint(part, 0.0, BODY_T)

    # бобышка спайдера (на теле, смещена от центра)
    spd_a = math.radians(SPD_MOUNT_ANG)
    spd_x, spd_y = SPD_MOUNT_R * math.cos(spd_a), SPD_MOUNT_R * math.sin(spd_a)
    part = part.union(cyl(SPD_BOSS_D / 2, BODY_T, T=tr(spd_x, spd_y, BODY_T / 2)))

    leg_cuts = []
    for (bx, by, side) in legs:
        d = _leg_dir_local(C, (bx, by), side)
        base = np.array([bx, by, BODY_T])                     # низ хомута = верх тела
        part = part.union(cyl_along(LEG_COLLAR_D / 2, LEG_H + 6, base - d * 6, d))
        # БОР от верха тела (z=BODY_T) ВВЕРХ — НЕ сквозь низ (скольз. грань цела).
        leg_cuts.append(cyl_along(LEG_BORE / 2, LEG_H + 12, base, d, seg=48))
        h = np.array([d[0], d[1], 0.0]); h = h / np.linalg.norm(h)   # горизонт. наружу
        ss = base + d * (LEG_H - 8)
        leg_cuts.append(cyl_along(LEG_SET / 2, LEG_COLLAR_D + 8,
                                  ss - h * (LEG_COLLAR_D / 2 + 4), h, seg=24))

    cuts = list(leg_cuts)
    cuts.append(cyl(SPD_TAP / 2, BODY_T + 1, seg=24, T=tr(spd_x, spd_y, BODY_T / 2)))
    pad_step = 360.0 / PAD_N
    for k in range(PAD_N):
        ang = -180.0 + (k + 0.5) * pad_step
        if -half + 1 < ang < half - 1:
            a = math.radians(ang)
            cuts.append(cyl(PAD_D / 2, PAD_DEPTH * 2, seg=32,
                            T=tr(PAD_R * math.cos(a), PAD_R * math.sin(a), 0)))
    part = part.difference(cuts)
    # ОБРЕЗАТЬ всё ниже нижней плоскости (наклонный хомут нижним краем уходит под z0)
    if legs:
        part = part.intersection(box(1000, 1000, 200, T=tr(0, 0, 100)))

    part.apply_transform(rotz(-LAP_ANG / 2.0))
    bb = part.bounds
    part.apply_translation([-(bb[0, 0] + bb[1, 0]) / 2, -(bb[0, 1] + bb[1, 1]) / 2, 0])
    return finish(part, name)


# ============================ 3. СПАЙДЕР МАГНИТА ============================
def magnet_spider():
    """Крестовина: 4 луча от внутр. края вращающегося кольца (R185.5) к центру,
    в центре ступица с карманом магнита СНИЗУ (магнит смотрит вниз на чип).
    Прикручивается к 4 бобышкам сегментов (винт M3 сверху). Плоская, лёгкая.
    Печатается ступицей вверх; карман магнита — на нижнем торце (на стол)."""
    arm_z0 = ROT_Z1                       # верх кольца = низ спайдера (z17)
    arm_t = 3.0                           # толщина луча
    arm_w = 10.0                          # ширина луча
    hub_d = 20.0
    hub_h = 5.0                           # ступица чуть толще (карман магнита)
    r_out = SPD_MOUNT_R                    # до бобышек спайдера на теле кольца (R196)
    solids = []
    # ступица
    solids.append(cyl(hub_d / 2, hub_h, T=tr(0, 0, arm_z0 + hub_h / 2)))
    # 4 луча к бобышкам (angle сегментов: 45,135,225,315 в мире, но спайдер печатаем
    # в своей рамке — совпадение по сборке; тут просто крест 0/90/180/270 + смещение)
    for ang in (45, 135, 225, 315):
        a = math.radians(ang)
        arm = box(r_out, arm_w, arm_t, T=tr(0, 0, arm_z0 + arm_t / 2))
        arm.apply_transform(rotz(ang))
        # сдвинуть луч так, чтобы шёл от центра к r_out
        arm2 = box(r_out - hub_d / 2, arm_w, arm_t)
        arm2.apply_translation([(hub_d / 2 + r_out) / 2, 0, arm_z0 + arm_t / 2])
        arm2.apply_transform(rotz(ang))
        solids.append(arm2)
        # проушина с отверстием под винт M3 к бобышке
        ear = cyl(arm_w / 2, arm_t, T=tr(r_out, 0, arm_z0 + arm_t / 2))
        ear.apply_transform(rotz(ang))
        solids.append(ear)
    part = trimesh.boolean.union(solids)

    cuts = []
    # карман магнита снизу ступицы (магнит смотрит вниз, торец на MAG_FACE_Z)
    # ступица: z17..22; магнит утоплен так, чтобы торец был на MAG_FACE_Z
    mag_pocket_bot = MAG_FACE_Z - MAG_RECESS
    cuts.append(cyl((MAGNET_D + MAG_FIT) / 2, (MAGNET_H + MAG_RECESS) + 0.5,
                    seg=48, T=tr(0, 0, mag_pocket_bot + (MAGNET_H + MAG_RECESS) / 2)))
    # отверстия M3 в проушинах
    for ang in (45, 135, 225, 315):
        a = math.radians(ang)
        cuts.append(cyl(3.4 / 2, arm_t + 2, seg=24,
                        T=tr(r_out * math.cos(a), r_out * math.sin(a), arm_z0 + arm_t / 2)))
    part = part.difference(cuts)
    part.apply_translation([0, 0, -part.bounds[0][2]])   # низ на стол для печати
    return finish(part, "az2_magnet_spider")


# ============================ 4. КОЛОННА ЭНКОДЕРА ============================
def encoder_column():
    """Неподвижная колонна по центру (на фанере, 3×M4), поднимает плату AS5048A
    так, что чип на CHIP_TOP_Z=15.5 смотрит ВВЕРХ на магнит спайдера (зазор 1.2).
    Верхняя площадка — посадка платы (4 бобышки 18×11, самонарез M2.5, окно чипа).
    Плата НЕ проходит через ось вращения проводами — всё неподвижно."""
    plat_top = CHIP_TOP_Z - BOARD_WALL - BOARD_BOSS_H   # верх плиты (плата на бобышках)
    col_d = 40.0
    foot_d = 70.0
    foot_t = 6.0
    solids = []
    solids.append(cyl(foot_d / 2, foot_t, T=tr(0, 0, foot_t / 2)))          # башмак на фанеру
    solids.append(cyl(col_d / 2, plat_top, T=tr(0, 0, plat_top / 2)))       # колонна
    # площадка платы
    plat = box(BOARD_HOLE_DX + BOARD_BOSS_OD + 6, BOARD_HOLE_DY + BOARD_BOSS_OD + 6,
               BOARD_WALL, T=tr(0, 0, plat_top + BOARD_WALL / 2))
    solids.append(plat)
    # 4 бобышки платы
    for sx in (-1, 1):
        for sy in (-1, 1):
            solids.append(cyl(BOARD_BOSS_OD / 2, BOARD_BOSS_H,
                              T=tr(sx * BOARD_HOLE_DX / 2, sy * BOARD_HOLE_DY / 2,
                                   plat_top + BOARD_WALL + BOARD_BOSS_H / 2)))
    part = trimesh.boolean.union(solids)

    cuts = []
    # самонарезы платы
    for sx in (-1, 1):
        for sy in (-1, 1):
            cuts.append(cyl(BOARD_SELFTAP / 2, BOARD_BOSS_H + BOARD_WALL + 2, seg=24,
                            T=tr(sx * BOARD_HOLE_DX / 2, sy * BOARD_HOLE_DY / 2,
                                 plat_top + (BOARD_WALL + BOARD_BOSS_H) / 2)))
    # окно чипа в центре площадки (чип смотрит вверх на магнит вплотную)
    cuts.append(box(CHIP_WIN, CHIP_WIN, BOARD_WALL + 4,
                    T=tr(0, 0, plat_top + BOARD_WALL / 2)))
    # 3×M4 в башмаке к фанере
    for ang in (90, 210, 330):
        a = math.radians(ang)
        cuts.append(cyl(FIX_M4 / 2, foot_t + 2, seg=24,
                        T=tr(28 * math.cos(a), 28 * math.sin(a), foot_t / 2)))
    part = part.difference(cuts)
    return finish(part, "az2_encoder_column")


# ============================ 5. ПОДСТАВКА МОТОРА ============================
def motor_pedestal():
    """Подставка под NEMA17, ПЕРЕВЁРНУТЫЙ осью вниз. Верхняя плита на PED_TOP_Z=30 —
    мотор садится сверху, вал/шестерня уходят ВНИЗ через окно Ø23 к зубьям (z9..19).
    4×M3 (31×31) — ПРОРЕЗИ по радиусу (к центру азимута): двигаешь мотор → ставишь
    зазор зацепления, затягиваешь. Ноги стоят на фанере снаружи венца (R≥232)."""
    mx, my = PINION_XY                    # (0,−240)
    # линия натяга = радиус к центру = вдоль +Y (от мотора к центру)
    solids, cuts = [], []

    # верхняя плита вокруг оси мотора. Внутр. край на y=-220 (R220) — снаружи мётлы
    # стоек (боссы теперь до R216), чтобы стойка при повороте не билась о плиту.
    plate = box(74.0, 54.0, PED_PLATE_T, T=tr(mx, my - 7.0, PED_TOP_Z - PED_PLATE_T / 2))
    solids.append(plate)

    # две ноги от плиты до фанеры, снаружи венца (tip R226): внутр. угол ~R234
    for sx in (-1, 1):
        leg = box(12.0, 34.0, PED_TOP_Z,
                  T=tr(mx + sx * 28.0, my - 10.0, PED_TOP_Z / 2))
        solids.append(leg)
        foot = box(24.0, 34.0, 6.0, T=tr(mx + sx * 28.0, my - 10.0, 3.0))
        solids.append(foot)
    # задняя стенка-косынка (жёсткость консоли), со стороны ДАЛЬШЕ от центра (−Y)
    solids.append(box(74.0, 8.0, PED_TOP_Z, T=tr(mx, my - 26.0, PED_TOP_Z / 2)))

    # === вырезы ===
    # окно вала+буртика через плиту (вал и шестерня идут вниз)
    cuts.append(cyl(NEMA_PILOT_D / 2, PED_PLATE_T + 2, seg=48,
                    T=tr(mx, my, PED_TOP_Z - PED_PLATE_T / 2)))
    # 4×M3 ПРОРЕЗИ вдоль Y (радиально к центру) — натяг
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx = mx + sx * NEMA_PITCH
            cy = my + sy * NEMA_PITCH
            slot = box(NEMA_M3, 2 * PED_SLOT_TRAVEL + NEMA_M3, PED_PLATE_T + 2,
                       T=tr(cx, cy, PED_TOP_Z - PED_PLATE_T / 2))
            cuts.append(slot)
            # карман головки M3 сверху
            cuts.append(box(6.5, 2 * PED_SLOT_TRAVEL + 6.5, 3.0,
                            T=tr(cx, cy, PED_TOP_Z - 1.5)))
    # 4×M4 к фанере в башмаках ног
    for sx in (-1, 1):
        for sy in (-1, 1):
            cuts.append(cyl(FIX_M4 / 2, 8, seg=24,
                            T=tr(mx + sx * 28.0, my - 10.0 + sy * 11.0, 3.0)))

    part = trimesh.boolean.union(solids)
    part = trimesh.boolean.difference([part] + cuts)
    part.apply_translation([-mx, -my, 0])            # к началу координат по XY
    return finish(part, "az2_motor_pedestal")


# ============================ 6. ШЕСТЕРНЯ 16T (вал Ø5) ============================
def pinion_bore5():
    """16T модуль 2, плоская z0..10, бор Ø5.25 под вал ОБЫЧНОГО NEMA17 (уже куплен).
    Радиальный M3-стопор на лыску (D-флэт) вала, гайка в паз-карман (как в azdrive).
    Прямой привод 14:1 — без ремня, без покупок."""
    half_w = math.pi * MODULE / 4.0
    core = Polygon([(PIN_ROOT_R * math.cos(a), PIN_ROOT_R * math.sin(a))
                    for a in np.linspace(0, 2 * math.pi, SEG_CIRC, endpoint=False)])
    teeth = [tooth_poly(PIN_PITCH_R, PIN_TIP_R, PIN_ROOT_R, half_w,
                        k * 360.0 / PIN_TEETH) for k in range(PIN_TEETH)]
    part = extrude(unary_union([core] + teeth), PIN_FACE)

    bore = cyl(PIN_BORE / 2, PIN_FACE + 2, T=tr(0, 0, PIN_FACE / 2))
    ss_len = PIN_TIP_R + 8.0
    setscrew = cyl(PIN_SET / 2, ss_len, seg=32)
    setscrew.apply_transform(roty(90))
    setscrew.apply_translation([ss_len / 2 - 3.0, 0, PIN_SET_Z])
    slot_top = PIN_FACE + 1.0
    slot_bot = PIN_SET_Z - (NUT_AF / math.cos(math.radians(30)) / 2 + 0.2)
    nut_slot = box(NUT_SLOT_T, NUT_SLOT_W, slot_top - slot_bot,
                   T=tr(NUT_R_CTR, 0, (slot_top + slot_bot) / 2))
    part = part.difference([bore, setscrew, nut_slot])
    return finish(part, "az2_pinion_16T_bore5")


def main():
    print("Азимут v2 (осевой, ленивая Сюзанна)…")
    print(f"  венец: m={MODULE} z={RING_TEETH} делит.Ø{2*RING_PITCH_R:.0f} вершины Ø{2*RING_TIP_R:.0f}")
    print(f"  привод: 16T прямой {RING_TEETH/PIN_TEETH:.0f}:1 (обычный NEMA17, вал Ø5), "
          f"межосевое {CENTER_DIST:.0f}, пинион z8..18 в зубьях z9..19")
    ring_fixed_seg()
    for nm, C, legs in ROT_CFGS:
        ring_rot_seg(nm, C, legs)
    magnet_spider()
    encoder_column()
    motor_pedestal()
    pinion_bore5()
    print(f"\nГотово → {OUTDIR}")
    print("Печать: сначала 1×fixed + 1×rot сегмент + pinion + pedestal — проверить")
    print("зацепление и высоту вала, потом ещё 3+3 сегмента.")


if __name__ == "__main__":
    main()
