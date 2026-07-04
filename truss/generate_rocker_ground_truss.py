#!/usr/bin/env python3
"""
Наземная «звезда» рокера как ТРУБНАЯ рама (truss) — МИНИМАЛИСТИЧНАЯ версия.

Каждый узел = union ЧИСТЫХ разрезных хомутов (tube_clamp.place_clamp, эталон
truss/_proto_reference.py) + маленькое центральное ядро, ровно достаточное, чтобы
сварить их в одно водонепроницаемое тело, + ТОЛЬКО функциональные фичи (ось M10,
плоская лапа-стопа, плоское седло венца, юстировочный M4). БОЛЬШЕ НИЧЕГО.

УДАЛЕНО навсегда: скользящие площадки, косынки/гуссеты, дуги R200, седло-пьедестал
над прорезью, тонкие шейки, импорт меша сына. Хаб-прототип 57 см³ — цель этого
худого, чистого вида.

Прорезь хомута: ВВЕРХ (+Z) для горизонтальных труб; ядро/фичи не заходят в сектор
прорези и щёк — зажим свободно затягивается.

  z=0        верх опорной доски (пол)
  z=32       ось радиальных труб Ø22 (бор всех хомутов)
  z=50       низ тела венца — верх седла (Rocker_ring_saddle_tube)

Детали / количества:
  1. Rocker_hub_truss.stl         ×1   (= эталонный hub_ground)
  2. Rocker_leg_truss.stl         ×3
  3. Rocker_ring_saddle_tube.stl  ×3

ПОЗА ПЕЧАТИ (мир = координаты сборки, чтобы оси труб стыковались; экспорт =
переориентирован в естественную позу, плоская грань на столе, z_min=0):
  • Rocker_hub_truss — ось M10 ВЕРТИКАЛЬНА, плоское дно ядра на столе (мировая
    поза, только сдвиг z_min=0). Бор M10 вертикален, гекс-карман гайки открыт вниз.
  • Rocker_leg_truss — стопа (плоский прямоугольный пад) ПЛОСКО на столе, z=0;
    хомут-цилиндр сверху, бор горизонтален. Мировая поза, сдвиг z_min=0.
  • Rocker_ring_saddle_tube — ПЕРЕОРИЕНТИРОВАН: бор хомута поставлен ВЕРТИКАЛЬНО
    (канон хомута — печать без поддержек), плоский торец хомута на столе; седло
    венца торчит вбок. Поворот −90° вокруг Y + сдвиг z_min=0.
"""
import math
import sys
from pathlib import Path

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).parent))
from tube_clamp import place_clamp, CLAMP_OD          # noqa: E402 — чистый хомут
from gen_rocker_comic import (                          # noqa: E402 — общий мир
    CORNER_ANGLES, R_ARM_OUT, RING_Z)

# ============================ ПАРАМЕТРЫ ============================
Z_ARM = 32.0            # высота оси радиальных труб (как ground_arms в комиксе)
CLAMP_H_ARM = 42.0      # длина хомута вдоль трубы (грип), мм
TUBE_OD = 22.0          # труба алюминий Ø22

# --- Проверенные посадки этого принтера ---
M4_TAP = 2.7            # Ø под самонарез M4 (юстировочный винт-ножка)
M10_CLR = 10.6          # Ø сквозного M10 (ось азимута)
NUT10_AF = 17.4         # гекс-карман гайки M10 «под ключ»
NUT10_DEPTH = 8.0       # глубина кармана гайки M10 (как эталон)

# --- 1. Хаб (= эталонный hub_ground) ---
HUB_CLAMP_H = 40.0      # длина хомутов хаба (эталон)
HUB_CORE_R = 15.0       # радиус центрального ядра-склейки (эталон, ≈ OD/2)
HUB_CORE_H = 44.0       # высота ядра (эталон)

# --- 2. Лапа (Rocker_leg_truss) ---
LEG_CLAMP_R0 = 243.0    # внутренний торец хомута лапы (грип R243..R285)
LEG_FOOT_W = 34.0       # ширина стопы тангенциально
LEG_FOOT_TOP = 30.0     # верх стопы z=0..30 (сваривается с низом хомута)

# --- 3. Трубное седло венца (Rocker_ring_saddle_tube) ---
SAD_CLAMP_R0 = 150.0    # хомут на трубе (грип R150..R192), прорезь ВВЕРХ свободна
SEAT_R_IN = 168.0       # плоский седловой таб СБОКУ (+Y), радиально наружу
SEAT_R_OUT = 214.0      # до-под тела венца (венец R200..218)
SEAT_Y_IN = 12.0        # внутр. грань таба по +Y: >11 (мимо трубы Ø22), <15.2 (варит к хомуту)
SEAT_Y_OUT = 30.0
SEAT_Z0 = 18.0          # низ таба
SEAT_TOP = RING_Z       # верх седла = низ тела венца (z=50)

SEG = 96
OUTDIR = Path(__file__).parent / "stl"

TUBE_SPAN = R_ARM_OUT - 35.0    # ≈ 250 мм (радиальный пролёт хаб→лапа, для отчёта)


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


def roty(ang_deg):
    return trimesh.transformations.rotation_matrix(math.radians(ang_deg), [0, 1, 0])


def radial_clamp(r0, ang_deg, height, slit_up=True):
    """Чистый хомут: бор ВДОЛЬ радиуса горизонтально, ось на z=Z_ARM, внутренний
    торец на радиусе r0, прорезь вверх (+Z). r0=0 → хомут стартует из центра."""
    a = math.radians(ang_deg)
    tube_dir = (math.cos(a), math.sin(a), 0.0)
    slit = (0.0, 0.0, 1.0) if slit_up else (0.0, 0.0, -1.0)
    origin = (r0 * math.cos(a), r0 * math.sin(a), Z_ARM)
    return place_clamp(height, origin, tube_dir, slit)


def finish(mesh, name, reorient=None):
    """Сварить вершины, валидировать, ВЫБРОСИТЬ мусорные тела (оставить самое
    крупное), опционально переориентировать в позу печати, посадить z_min=0."""
    OUTDIR.mkdir(parents=True, exist_ok=True)
    mesh.merge_vertices(digits_vertex=5)
    mesh.process(validate=True)
    # выбросить отпавшие мусорные тела — оставить самое крупное по объёму
    parts = mesh.split(only_watertight=False)
    if len(parts) > 1:
        mesh = max(parts, key=lambda m: m.volume)
    if reorient is not None:
        mesh.apply_transform(reorient)
    mesh.merge_vertices()
    mesh.process(validate=True)
    mesh.apply_translation([0, 0, -mesh.bounds[0, 2]])   # плоская грань на стол
    out = OUTDIR / f"{name}.stl"
    mesh.export(out)
    bb = mesh.bounds
    print(f"  {name}.stl  watertight={mesh.is_watertight}  vol={mesh.volume/1000:.2f}cm³  "
          f"bbox={bb[1,0]-bb[0,0]:.0f}×{bb[1,1]-bb[0,1]:.0f}×{bb[1,2]-bb[0,2]:.0f}mm")
    return mesh


# ============================ 1. ХАБ (= эталон hub_ground) ============================
def rocker_hub_truss():
    """EXACTLY эталонный hub_ground: 3 чистых хомута из центра под 120°
    (CORNER_ANGLES) + маленькое ядро-цилиндр + сквозной бор M10 и гекс-карман
    гайки. Ничего лишнего. Поза печати: ось M10 вертикальна, плоское дно на столе."""
    clamps = [radial_clamp(0.0, ang, HUB_CLAMP_H, slit_up=True) for ang in CORNER_ANGLES]
    core = cyl(HUB_CORE_R, HUB_CORE_H, T=tr(0, 0, Z_ARM))     # минимальное ядро-склейка
    part = core.union(clamps)

    m10 = cyl(M10_CLR / 2, 80, T=tr(0, 0, Z_ARM))
    nut = cyl(NUT10_AF / math.sqrt(3), NUT10_DEPTH, seg=6,
              T=tr(0, 0, Z_ARM - 24 + 4))                     # карман открыт вниз
    part = part.difference([m10, nut])
    return finish(part, "Rocker_hub_truss")


# ============================ 2. ЛАПА ============================
def rocker_leg_truss():
    """Один горизонтальный радиальный хомут (грип R243..R285, ось z=32) + одна
    МИНИМАЛЬНАЯ плоская стопа-пад (прямоугольная коробка, НЕ дуга) на пол +
    юстировочный M4 по центру. Поза печати: стопа плоско на столе (z=0)."""
    clamp = radial_clamp(LEG_CLAMP_R0, 0.0, CLAMP_H_ARM, slit_up=True)

    r_ctr = LEG_CLAMP_R0 + CLAMP_H_ARM / 2.0                  # центр хомута ≈ R264
    foot = box(CLAMP_H_ARM, LEG_FOOT_W, LEG_FOOT_TOP,
               T=tr(r_ctr, 0, LEG_FOOT_TOP / 2))              # z=0..30, варится с низом хомута
    part = clamp.union(foot)

    tap = cyl(M4_TAP / 2, 24, seg=32, T=tr(r_ctr, 0, 11))     # M4 винт-ножка (самонарез)
    part = part.difference([tap])
    return finish(part, "Rocker_leg_truss")


# ============================ 3. ТРУБНОЕ СЕДЛО ВЕНЦА ============================
def rocker_ring_saddle_tube():
    """Один чистый хомут на трубе (грип R150..R192, прорезь ВВЕРХ свободна) + один
    МИНИМАЛЬНЫЙ плоский седловой таб СБОКУ (смещён по +Y, мимо трубы и мимо
    прорези), радиально наружу до-под тела венца, верх плоский на z=50. Никаких
    дуг R200. Поза печати: бор поставлен ВЕРТИКАЛЬНО (канон хомута), торец на столе."""
    clamp = radial_clamp(SAD_CLAMP_R0, 0.0, CLAMP_H_ARM, slit_up=True)

    seat = box(SEAT_R_OUT - SEAT_R_IN, SEAT_Y_OUT - SEAT_Y_IN, SEAT_TOP - SEAT_Z0,
               T=tr((SEAT_R_IN + SEAT_R_OUT) / 2,
                    (SEAT_Y_IN + SEAT_Y_OUT) / 2,
                    (SEAT_Z0 + SEAT_TOP) / 2))
    part = clamp.union(seat)

    # переориентация: бор радиальный (+X) → вертикаль (+Z), печать без поддержек
    return finish(part, "Rocker_ring_saddle_tube", reorient=roty(-90))


def main():
    print("Генерация наземной звезды рокера (трубная рама, минимал)…")
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
