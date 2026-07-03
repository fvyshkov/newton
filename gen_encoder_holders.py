#!/usr/bin/env python3
"""
Печатные держатели энкодеров AS5048A (push-to, Этап 1).

Генерит 4 бинарных STL в stl/encoder/ через CSG (trimesh + manifold3d):

  1. magnet_cap_azimuth.stl   — колпачок с магнитом, ВПРЕССОВЫВАЕТСЯ на конец
                                 болта M10 (азимутальная ось). Магнит смотрит вниз.
  2. magnet_cap_altitude.stl  — колпачок с магнитом, ПРИКРУЧИВАЕТСЯ винтом в центр
                                 бокового круга R100 (высотная ось). Спигот центрует.
  3. bracket_azimuth.stl      — кронштейн чипа ПОД опорной доской, чип смотрит ВВЕРХ
                                 на магнит. Слот-отверстия = регулировка зазора.
  4. bracket_altitude.stl     — кронштейн чипа на стенке рокера, чип смотрит ВБОК на
                                 магнит в центре круга. Вылет ARM регулируется.

Ключевые принципы (из datasheet AS5048A):
  * магнит ДИАМЕТРАЛЬНЫЙ, соосно чипу, зазор ~0.5–1.5 мм (воздух);
  * ≥5 мм пластика между магнитом и сталью болта (сталь искажает поле);
  * чип — на неподвижной детали (к нему провода), магнит — на вращающейся.

Размеры — параметрические (блок констант ниже). Уточняются под реальную плату/магнит.
"""
import math
from pathlib import Path

import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix as rotmat

# ============================ ПАРАМЕТРЫ ============================
# --- Магнит (диаметральный цилиндр из набора AS5048A) ---
# Проверено: kit к ams-клону AS5048-AB идёт с Ø6×2.5 диаметральным магнитом.
MAGNET_D = 6.0          # Ø магнита, мм
MAGNET_H = 2.5          # высота магнита, мм
MAG_FIT  = 0.20         # припуск кармана на впрессовку (карман = D + FIT)
MAG_RECESS = 0.4        # магнит утоплен на столько ниже торца колпачка (защита)

# --- Зазор магнит↔чип ---
AIR_GAP = 1.0           # целевой воздушный зазор, мм (slot-отверстия дают подстройку)

# --- Сталь под магнитом ---
STEEL_STANDOFF = 5.0    # минимум пластика между магнитом и сталью болта

# --- Болт M10 (азимут) ---
M10_SHANK = 10.0
M10_BORE  = M10_SHANK + 0.5   # Ø расточки под впрессовку на конец болта (10.5)
BORE_DEPTH = 12.0             # глубина посадки на болт

# --- Винт крепления колпачка высоты (саморез/винт ~M4) ---
ALT_SCREW_CLR = 4.3     # Ø сквозного отверстия под винт
ALT_SCREW_HEAD = 8.0    # Ø зенковки под головку
ALT_SPIGOT_D = 6.0      # центрующий спигот (сверлишь Ø6 в центре круга)
ALT_SPIGOT_H = 4.0

# --- Плата AS5048A (ПРОВЕРЕНО: ams AS5048-AB клон) ---
# 28×22 мм; 4 отв. Ø2.6 по прямоугольнику 18×11; ЧИП (=ось магнита) в ЦЕНТРЕ
# прямоугольника отверстий (НЕ в центре платы — сверху гребень 1×8 2.54мм).
BOARD_L = 28.0          # длина платы, мм
BOARD_W = 22.0          # ширина платы, мм
BOARD_T = 1.6           # толщина платы (typ FR4; замерить на месте)
HOLE_DX = 18.0          # расстояние между отв. по X (центр-центр)
HOLE_DY = 11.0          # расстояние между отв. по Y (центр-центр)
HOLE_SELFTAP = 2.2      # Ø бобышек под саморез M2.5 (само-нарезка в пластик)
BOSS_OD = 6.0           # Ø бобышки
BOSS_H  = 3.0           # высота бобышки (board стоит на них, чип-сторона к магниту)
CHIP_WIN = 8.0          # окно под чип (квадрат), чтобы чип смотрел на магнит вплотную

# --- Общие толщины ---
WALL = 3.0              # стенки/полки
CAP_OD = 18.0           # внешний Ø колпачков (даёт площадь под клей)

# --- Кронштейн: крепёж к корпусу ---
FOOT_SCREW = 3.4        # Ø отверстий под M3 (slot)
FOOT_SLOT = 6.0         # длина слота регулировки (для зазора)

# --- Геометрия мостика высоты ---
ALT_ARM_LEN = 60.0      # вылет от стенки рокера до центра круга — ЗАМЕРИТЬ и подставить
ZIPTIE_W = 4.0          # ширина прорези под стяжку
ZIPTIE_T = 2.2          # толщина прорези

SEG = 96                # фасеты цилиндров

OUTDIR = Path(__file__).parent / "stl" / "encoder"


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


def slot(length, r, h, T=None):
    """Прямоугольный слот со скруглёнными концами (для регулировочных отверстий)."""
    body = box(length, 2 * r, h)
    c1 = cyl(r, h, T=tr(-length / 2, 0, 0))
    c2 = cyl(r, h, T=tr(length / 2, 0, 0))
    s = body.union([c1, c2])
    if T is not None:
        s.apply_transform(T)
    return s


def finish(mesh, name):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    mesh.process(validate=True)
    out = OUTDIR / f"{name}.stl"
    mesh.export(out)
    bb = mesh.bounds
    print(f"  {name}.stl  watertight={mesh.is_watertight}  vol={mesh.volume/1000:.2f}cm³  "
          f"bbox={bb[1,0]-bb[0,0]:.0f}×{bb[1,1]-bb[0,1]:.0f}×{bb[1,2]-bb[0,2]:.0f}mm")
    return mesh


# ============================ 1. КОЛПАЧОК АЗИМУТА ============================
def magnet_cap_azimuth():
    """Болт M10 торчит вниз; колпачок надевается снизу, магнит смотрит ВНИЗ.
    Стопка снизу→вверх: [магнит карман] [5мм пластик] [расточка под болт].
    Печатается расточкой вверх (на стол ложится торцом с магнитом)."""
    H = BORE_DEPTH + STEEL_STANDOFF + (MAGNET_H + MAG_RECESS)
    body = cyl(CAP_OD / 2, H, T=tr(0, 0, H / 2))   # ось Z, низ при z=0

    # карман магнита снизу (z=0..magnet_h), магнит утоплен
    pocket = cyl((MAGNET_D + MAG_FIT) / 2, MAGNET_H + MAG_RECESS + 1,
                 T=tr(0, 0, (MAGNET_H + MAG_RECESS) / 2 - 0.5))
    # расточка под болт сверху
    bore = cyl(M10_BORE / 2, BORE_DEPTH + 1,
               T=tr(0, 0, H - (BORE_DEPTH + 1) / 2 + 0.5))

    cap = body.difference([pocket, bore])
    return finish(cap, "magnet_cap_azimuth")


# ============================ 2. КОЛПАЧОК ВЫСОТЫ ============================
def magnet_cap_altitude():
    """Вклеивается спиготом Ø6 в просверленный ЦЕНТР деревянного круга R100, магнит
    смотрит НАРУЖУ. Никакого винта/стали по оси — магнит на сплошном дне кармана.
    Стопка: [спигот на вклейку ↓] [≥4мм сплошного пластика] [карман магнита ↑]."""
    floor = 4.0
    H = floor + (MAGNET_H + MAG_RECESS)
    body = cyl(CAP_OD / 2, H, T=tr(0, 0, H / 2))

    # центрующий спигот снизу — в сверление Ø6 в дереве, на эпоксидку/CA
    spig = cyl(ALT_SPIGOT_D / 2, ALT_SPIGOT_H, T=tr(0, 0, -ALT_SPIGOT_H / 2 + 0.01))
    cap = body.union(spig)

    # карман магнита сверху, дно СПЛОШНОЕ (нет осевого отверстия и стали!)
    pocket = cyl((MAGNET_D + MAG_FIT) / 2, MAGNET_H + MAG_RECESS + 1,
                 T=tr(0, 0, H - (MAGNET_H + MAG_RECESS) / 2 + 0.5))
    cap = cap.difference([pocket])
    return finish(cap, "magnet_cap_altitude")


# ============================ 3. УНИВЕРСАЛЬНЫЙ ДЕРЖАТЕЛЬ ПЛАТЫ ============================
def board_holder():
    """Держатель платы AS5048A. ВАЖНО: начало координат (0,0) = ЧИП = ось магнита
    (центр прямоугольника отверстий 18×11), поэтому при монтаже ось вращения
    проходит ровно через центр детали. Нормаль пластины (Z) = ось вращения.
    Плата кладётся чип-стороной ВВЕРХ (к магниту) на 4 бобышки, прикручивается
    саморезами M2.5 сверху. Снизу — лапка с 2 слотами на крепёж к мостику.
    Годится и как настольный стенд для bench-теста, и как торец мостика."""
    plate_x = HOLE_DX + BOSS_OD + 4      # ~28
    plate_y = HOLE_DY + BOSS_OD + 4      # ~21
    base = box(plate_x, plate_y, WALL, T=tr(0, 0, WALL / 2))

    # 4 бобышки под плату (board стоит чип-стороной вверх на их торце z=WALL+BOSS_H)
    bosses = []
    holes = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * HOLE_DX / 2, sy * HOLE_DY / 2
            bosses.append(cyl(BOSS_OD / 2, BOSS_H, T=tr(cx, cy, WALL + BOSS_H / 2)))
            holes.append(cyl(HOLE_SELFTAP / 2, WALL + BOSS_H + 2, T=tr(cx, cy, (WALL + BOSS_H) / 2)))
    part = base.union(bosses)

    window = box(CHIP_WIN, CHIP_WIN, WALL + 2, T=tr(0, 0, WALL / 2))   # релиф под чип в центре

    # крепёжная лапка снизу (−Y, со стороны без гребня), 2 слот-отверстия M3
    tab = box(plate_x, 10, WALL, T=tr(0, -plate_y / 2 - 5 + 0.01, WALL / 2))
    part = part.union(tab)
    mount = []
    for sx in (-1, 1):
        mount.append(slot(FOOT_SLOT, FOOT_SCREW / 2, WALL + 2,
                          T=tr(sx * (plate_x / 2 - 4), -plate_y / 2 - 5, WALL / 2)))

    part = part.difference([window] + holes + mount)
    return finish(part, "board_holder")


def main():
    print("Генерация держателей энкодеров…")
    magnet_cap_azimuth()
    magnet_cap_altitude()
    board_holder()
    print(f"\nГотово → {OUTDIR}")
    print("Мостик «к оси» (вылет/высота) — под замеры твоей сборки, генерим отдельно.")


if __name__ == "__main__":
    main()
