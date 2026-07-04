#!/usr/bin/env python3
"""
Статическая «наземная звезда» рокера как ТРУБНАЯ рама (truss).

Генерит 3 бинарных STL в truss/stl/ через CSG (trimesh + manifold3d),
переиспользуя ПРОВЕРЕННЫЙ хомут сына (tube_clamp.place_clamp) и общие
мировые константы из gen_rocker_comic (z=0 = верх опорной доски).

Идея: центральный узел (ось азимута) и 3 лапы соединены НЕ печатью, а
готовыми алюминиевыми трубами Ø22. Каждое соединение — раздвижной хомут
сына, приваренный (union) к телу узла. Трубы горизонтальны и радиальны,
их ось на высоте Z_ARM=32 (как ground_arms в комиксе). Кольцо-венец
(4×Rocker_ring_segment) по-прежнему ложится на 3 седла на RING_Z=50.

  z=0        верх опорной доски (пол)
  z=0..45    Rocker_hub_truss — центральная бобышка Ø70, ось азимута M10
  z=32       ось радиальных труб (хомуты хаба и лап)
  z=50..60   зубчатый венец на 3 сёдлах (низ тела z=50)
  z=75       ось труб вращающейся рамы (выше, отдельный узел)

Детали / количества:
  1. Rocker_hub_truss.stl         ×1
  2. Rocker_leg_truss.stl         ×3
  3. Rocker_ring_saddle_tube.stl  ×3
  (существующее Rocker_ring_saddle.stl НЕ трогаем — печатается как раньше;
   трубный вариант нужен, т.к. кольцо на R210 стоит там, где под ним нет
   тела хаба, а только радиальная труба.)

Трубы (алюминий Ø22, ручки-защёлки зажимаются хомутом):
  хаб→лапа: одна прямая труба на луч, радиальный пролёт R35→R285 ≈ 250 мм
  ×3. Внутренний конец в хомуте хаба (грип R35..R72), наружный — в хомуте
  лапы (грип R243..R285), лапа стоит стопой на R_FOOT=280.

ОРИЕНТАЦИЯ ПЕЧАТИ (без поддержек «где можно»):
  • Rocker_hub_truss — ось M10 вертикальна (+Z), плоский верх вверх, стол
    = низ бобышки. M10 расточка вертикальна (чисто); гекс-карман гайки
    открыт ВНИЗ (потолок Ø17 мостится); 3 радиальных бора Ø22 —
    ГОРИЗОНТАЛЬНЫ (прорезь вверх облегчает потолок, лёгкая поддержка/мост);
    под свесами воротников — рёбра-опоры к столу.
  • Rocker_leg_truss — стопой ВНИЗ на стол (z=0), M4 юстировочное отверстие
    вертикально (чисто), расширяющаяся стопа самонесущая (выпуклая оболочка
    от базы к воротнику); радиальный бор Ø22 горизонтален (мостится).
  • Rocker_ring_saddle_tube — печатать РАДИАЛЬ ВВЕРХ (ось трубы/бора
    вертикальна = проверенная ориентация хомута сына): бор Ø22 без
    поддержек; седло/гребень становятся боковыми уступами (стенками).
"""
import math
import sys
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import Point
from shapely.geometry import box as shp_box

sys.path.insert(0, str(Path(__file__).parent))
from tube_clamp import place_clamp, CLAMP_OD          # noqa: E402 — хомут сына
from gen_rocker_comic import (                          # noqa: E402 — общий мир
    CORNER_ANGLES, R_CORNER, R_ARM_OUT, R_FOOT, RING_Z, polar)
from generate_rocker_azdrive import BODY_R_IN           # noqa: E402 — R200 (венец)

# ============================ ПАРАМЕТРЫ ============================
Z_ARM = 32.0            # высота оси радиальных труб (как ground_arms в комиксе)
CLAMP_H_ARM = 42.0      # длина хомута вдоль трубы (грип), мм
TUBE_OD = 22.0          # труба алюминий Ø22

# --- Проверенные посадки этого принтера ---
M3_PILOT = 2.7          # Ø пилота под саморез M3
M4_CLR = 4.4            # Ø сквозного M4
M4_TAP = 2.7            # Ø под самонарез M4 (юстировочный винт-ножка)
M10_CLR = 10.6          # Ø сквозного M10 (ось азимута)
NUT10_AF = 17.4         # гекс-карман гайки M10 «под ключ»
NUT10_DEPTH = 7.0       # глубина кармана гайки M10

# --- 1. Хаб (Rocker_hub_truss) ---
HUB_OD = 70.0           # Ø тела бобышки
HUB_H = 45.0            # высота бобышки (плоский верх z=45; как ground_hub)
HUB_CLAMP_R0 = 30.0     # радиус внутреннего торца хомута хаба (грип R30..R72)
HUB_SPINE_W = 18.0      # ширина ребра-опоры под лучом, тангенциально
HUB_SPINE_Z = 7.0       # высота ребра (до низа воротника z≈6.4) → контакт стола

# --- 2. Лапа (Rocker_leg_truss) ---
LEG_CLAMP_R0 = 243.0    # внутренний торец хомута лапы (грип R243..R285)
FOOT_R = R_FOOT         # 280 — центр стопы на полу
FOOT_BASE_R = 30.0      # радиус опорной базы стопы (на z=0)
FOOT_BASE_H = 3.0       # толщина базы (для выпуклой оболочки)
FOOT_PAD_D = 24.0       # Ø проточки под резиновый пятак снизу
FOOT_PAD_DEEP = 2.0     # глубина проточки
FOOT_LEVEL = True       # центральное M4-отверстие под юстировочный винт-ножку

# --- 3. Трубное седло венца (Rocker_ring_saddle_tube) ---
SAD_CLAMP_R0 = 158.0    # хомут ВНУТРИ кольца (грип R158..R200), чтобы высокий
                        # воротник не задел венец: он в открытой зоне r<200
SAD_SEAT_R_IN = 196.0   # низ седла-полки, радиально
SAD_SEAT_R_OUT = 218.0  # вылет полки под тело венца (r200..218)
SAD_SEAT_W = 34.0       # ширина полки/гребня, тангенциально
SAD_SEAT_TOP = RING_Z   # верх полки = низ тела венца (z=50)
SAD_SEAT_T = 6.0        # толщина полки (z=44..50)
RIDGE_W = 3.0           # гребень-упор кольца: ширина (наружная грань = R200)
RIDGE_H = 2.0           # высота гребня (упор в внутреннюю кромку тела венца)

SEG = 96                # фасеты полных окружностей
OUTDIR = Path(__file__).parent / "stl"

# радиальный пролёт трубы хаб→лапа (для отчёта): от R35 (комикс) до R285
TUBE_SPAN = R_ARM_OUT - 35.0    # ≈ 250 мм


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


def rotz(ang_deg):
    return trimesh.transformations.rotation_matrix(math.radians(ang_deg), [0, 0, 1])


def extrude(poly2d, h, z0=0.0):
    m = trimesh.creation.extrude_polygon(poly2d, height=h)
    if z0:
        m.apply_translation([0, 0, z0])
    return m


def radial_clamp(r0, ang_deg, height, slit_up=True):
    """Хомут сына, бор ВДОЛЬ радиуса горизонтально, ось на z=Z_ARM.
    origin = внутренний торец хомута на радиусе r0. Прорезь — вверх."""
    a = math.radians(ang_deg)
    tube_dir = (math.cos(a), math.sin(a), 0.0)
    slit = (0.0, 0.0, 1.0) if slit_up else (0.0, 0.0, -1.0)
    origin = (r0 * math.cos(a), r0 * math.sin(a), Z_ARM)
    return place_clamp(height, origin, tube_dir, slit)


def finish(mesh, name):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    # грубая сварка вершин ДО валидации — гасит sliver-грани на пересечении
    # тел вращения (приём из generate_rocker_azbench)
    mesh.merge_vertices(digits_vertex=5)
    mesh.process(validate=True)
    out = OUTDIR / f"{name}.stl"
    mesh.export(out)
    bb = mesh.bounds
    print(f"  {name}.stl  watertight={mesh.is_watertight}  vol={mesh.volume/1000:.2f}cm³  "
          f"bbox={bb[1,0]-bb[0,0]:.0f}×{bb[1,1]-bb[0,1]:.0f}×{bb[1,2]-bb[0,2]:.0f}mm")
    return mesh


# ============================ 1. ХАБ ============================
def rocker_hub_truss():
    """Центральная бобышка Ø70 z=0..45. Вертикальная ось азимута: бор M10
    Ø10.6 насквозь + гекс-карман гайки M10 СНИЗУ (болт снизу сквозь доску
    тянет гайку). Плоский верх (над ним встаёт вращающаяся рама). 3
    горизонтальных радиальных хомута на CORNER_ANGLES, ось труб z=32,
    прорезь вверх (болт доступен сверху). Под каждым лучом — ребро-опора к
    столу (низ воротника z≈6.4, ребро z=0..7)."""
    body = cyl(HUB_OD / 2, HUB_H, T=tr(0, 0, HUB_H / 2))

    add = []
    for ang in CORNER_ANGLES:
        add.append(radial_clamp(HUB_CLAMP_R0, ang, CLAMP_H_ARM, slit_up=True))
        # ребро-опора: коробка вдоль радиуса от края бобышки до конца хомута
        r_in, r_out = HUB_OD / 2 - 4.0, HUB_CLAMP_R0 + CLAMP_H_ARM
        Lr = r_out - r_in
        T = rotz(ang) @ tr((r_in + r_out) / 2.0, 0, HUB_SPINE_Z / 2)
        add.append(box(Lr, HUB_SPINE_W, HUB_SPINE_Z, T=T))
    part = body.union(add)

    # Резаки оси азимута: сквозной M10 + гекс-карман гайки снизу
    cutters = [cyl(M10_CLR / 2, HUB_H + 2, T=tr(0, 0, HUB_H / 2)),
               cyl(NUT10_AF / math.sqrt(3), NUT10_DEPTH + 1, seg=6,
                   T=tr(0, 0, (NUT10_DEPTH + 1) / 2 - 1))]
    part = part.difference(cutters)
    return finish(part, "Rocker_hub_truss")


# ============================ 2. ЛАПА ============================
def rocker_leg_truss():
    """Лапа (печатается ×3, каноническая на +X). Один горизонтальный
    радиальный хомут (грип R243..R285, ось z=32) + расширяющаяся стопа к
    полу: выпуклая оболочка от опорной базы Ø60 на R_FOOT=280 (z=0) к низу
    воротника. Снизу — проточка Ø24 под резиновый пятак и центральное M4
    отверстие под юстировочный винт-ножку. Труба хаба вставляется в хомут
    наружным концом."""
    ang = 0.0
    clamp = radial_clamp(LEG_CLAMP_R0, ang, CLAMP_H_ARM, slit_up=True)

    # Стопа = выпуклая оболочка (база на полу) + (площадка под воротником).
    # Оба выпуклые → hull watertight и самонесущий (расширяется книзу).
    base = cyl(FOOT_BASE_R, FOOT_BASE_H, T=tr(FOOT_R, 0, FOOT_BASE_H / 2))
    r_pad_ctr = LEG_CLAMP_R0 + CLAMP_H_ARM / 2.0          # центр хомута ≈ R264
    pad = box(CLAMP_H_ARM - 2, 40, 8, T=tr(r_pad_ctr, 0, 10))   # у низа воротника
    foot = trimesh.util.concatenate([base, pad]).convex_hull

    part = clamp.union(foot)

    cutters = []
    # проточка под резиновый пятак (открыта вниз)
    cutters.append(cyl(FOOT_PAD_D / 2, FOOT_PAD_DEEP + 1,
                       T=tr(FOOT_R, 0, FOOT_PAD_DEEP / 2 - 0.5)))
    if FOOT_LEVEL:                                        # M4 винт-ножка (самонарез)
        cutters.append(cyl(M4_TAP / 2, 24, seg=32, T=tr(FOOT_R, 0, 11)))
    part = part.difference(cutters)
    return finish(part, "Rocker_leg_truss")


# ============================ 3. ТРУБНОЕ СЕДЛО ВЕНЦА ============================
def rocker_ring_saddle_tube():
    """Седло венца, сидящее НА радиальной трубе (печатается ×3, каноническое
    на +X, ось азимута в начале координат). База — хомут Ø22 ВНУТРИ кольца
    (грип R158..R200), чтобы высокий воротник хомута оказался в открытой зоне
    r<200 и не задел венец. Сверху — полка на z=50 (низ тела венца) с
    вылетом под тело (r200..218) и гребень-упор (наружная грань R200 =
    BODY_R_IN венца). Полка приварена к наружной стенке воротника и
    нависает над трубой, идущей дальше к лапе."""
    clamp = radial_clamp(SAD_CLAMP_R0, 0.0, CLAMP_H_ARM, slit_up=True)

    # Полка-седло: коробка r=196..218, z=44..50 (низ тела венца z=50)
    seat = box(SAD_SEAT_R_OUT - SAD_SEAT_R_IN, SAD_SEAT_W, SAD_SEAT_T,
               T=tr((SAD_SEAT_R_IN + SAD_SEAT_R_OUT) / 2, 0,
                    SAD_SEAT_TOP - SAD_SEAT_T / 2))
    part = clamp.union(seat)

    # Гребень-упор: кольцевой сектор R197..R200 вокруг оси азимута, z=50..52
    axis = Point(0, 0)
    ann = axis.buffer(BODY_R_IN, quad_segs=512).difference(
        axis.buffer(BODY_R_IN - RIDGE_W, quad_segs=512))
    win = shp_box(SAD_SEAT_R_IN, -SAD_SEAT_W / 2, SAD_SEAT_R_OUT, SAD_SEAT_W / 2)
    ridge2d = ann.intersection(win)
    part = part.union(extrude(ridge2d, RIDGE_H, z0=SAD_SEAT_TOP))
    return finish(part, "Rocker_ring_saddle_tube")


def main():
    print("Генерация наземной звезды рокера (трубная рама)…")
    print(f"  ось труб z={Z_ARM:.0f}, хомут-грип {CLAMP_H_ARM:.0f}мм, воротник "
          f"Ø{CLAMP_OD:.0f}; венец на 3 сёдлах z={RING_Z:.0f}")
    print(f"  труба хаб→лапа: радиальный пролёт R35→R{R_ARM_OUT:.0f} ≈ "
          f"{TUBE_SPAN:.0f}мм, Ø{TUBE_OD:.0f}, ×3")
    rocker_hub_truss()
    rocker_leg_truss()
    rocker_ring_saddle_tube()
    print(f"\nГотово → {OUTDIR}")
    print("Количества: хаб ×1, лапа ×3, трубное седло ×3.")
    print(f"Трубы Ø22 алюминий: 3× по ~{TUBE_SPAN:.0f}мм (R35→R285).")


if __name__ == "__main__":
    main()
