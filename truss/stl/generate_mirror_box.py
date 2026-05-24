#!/usr/bin/env python3
"""
Mirror box для truss-варианта 8" Newton.

Печатается на Bambu Lab H2D (стол 350×320, в самый раз для 302×302×130).

Внутреннее пространство 290×290мм рассчитано так чтобы:
  - вмещалась старая Y-плита оправы (Mirror_cell_back, Ø250мм) с запасом
  - помещались 3 шпильки M8 высотной регулировки на радиусе 132мм
    под углами 30°/150°/270° (положения соответствуют ушам Y-плиты)
  - оставался зазор стенки 4-5мм со всех сторон

Сокеты под стойки — отдельные печатные детали, болтами к 4 углам коробки.
Это сделано чтобы при смене диаметра стоек не перепечатывать большую
коробку (12+ ч печати), а только 4 маленьких клипса.

Особенности:
  * Дно с 3 Ø9 clearance отверстиями (M8 шпилька проходит насквозь,
    держится двумя гайками снизу и сверху).
  * 4 угла усилены вертикальными бобышками с резьбовыми отверстиями
    под M5 (M5 нарезается саморезом по пластику или печатается, или
    используется hex-карман на гайку).
  * Стенки имеют сквозные прямоугольные окна для облегчения и охлаждения
    (вес пластика и сток тёплого воздуха от зеркала).
  * Скруглённые внешние углы R5 — приятнее на ощупь, лучше адгезия к
    столу.

Печать:
  * Ориентация: дном на стол, открытым верхом вверх — поддержки НЕ нужны.
  * 0.4мм сопло · 0.2мм слой · 5-6 периметров · 25-30% gyroid.
  * PETG-HF или ASA (PLA не годится: внутри летом может быть жарко от
    солнца на зеркале).
  * brim 5мм для адгезии (деталь высокая, склонна к отрыву).
  * время печати ~ 12-15 часов.
"""
import math
from pathlib import Path

import trimesh

# --- Внутренние размеры ---
INSIDE_X = 290.0
INSIDE_Y = 290.0
WALL_T = 6.0
FLOOR_T = 8.0
HEIGHT = 130.0

OUTER_X = INSIDE_X + 2 * WALL_T
OUTER_Y = INSIDE_Y + 2 * WALL_T

# --- Шпильки высотной регулировки M8 ---
# Положения на радиусе SHAFT_R = 132мм от центра коробки,
# углы 30°/150°/270° — соответствуют ушам Y-плиты оправы.
SHAFT_R = 132.0
SHAFT_ANGLES = [30.0, 150.0, 270.0]
SHAFT_CLEAR_R = 4.6   # Ø9.2 clearance под M8 (с запасом на печать)

# Усиление вокруг отверстия снизу — бобышка для M8 шайбы/гайки
SHAFT_BOSS_R = 12.0   # Ø24 бобышка
SHAFT_BOSS_H = 4.0    # высота бобышки над верхней гранью пола

# --- Угловые крепёжные отверстия под сокеты стоек ---
# В каждом углу — 2 сквозных M5 отверстия, по одному на каждой из двух
# стенок, образующих угол. Это даёт симметричное крепление сокета
# (L-образный фланец захватывает угол с двух сторон).
CORNER_M5_HOLE_R = 2.75    # Ø5.5 clearance под M5
CORNER_M5_Z = 100.0        # высота отверстий (верхняя треть стенки)
CORNER_M5_INSET = 25.0     # отступ от угла внутрь по стенке

# --- Окна в стенках (вентиляция/облегчение) ---
WINDOW_W = 80.0
WINDOW_H = 60.0
WINDOW_CENTER_Z = HEIGHT / 2.0  # по высоте — посередине

# --- Скругление внешних углов ---
CORNER_CHAMFER = 5.0

SEG = 64
OUT_DIR = Path(__file__).parent
OUT_FILE = OUT_DIR / "Mirror_box.stl"


def xy(angle_deg, r):
    a = math.radians(angle_deg)
    return r * math.cos(a), r * math.sin(a)


def main():
    # Внешний короб
    outer = trimesh.creation.box(extents=(OUTER_X, OUTER_Y, HEIGHT))
    outer.apply_translation([0, 0, HEIGHT / 2.0])

    # Внутренняя полость — вычитаем сверху, оставляя пол толщиной FLOOR_T
    cavity = trimesh.creation.box(
        extents=(INSIDE_X, INSIDE_Y, HEIGHT - FLOOR_T + 0.1)
    )
    cavity.apply_translation(
        [0, 0, FLOOR_T + (HEIGHT - FLOOR_T) / 2.0 + 0.05]
    )
    body = outer.difference(cavity)

    # 3 отверстия под шпильки M8 в полу (clearance)
    for ang in SHAFT_ANGLES:
        x, y = xy(ang, SHAFT_R)
        shaft_hole = trimesh.creation.cylinder(
            radius=SHAFT_CLEAR_R,
            height=FLOOR_T * 4,
            sections=SEG,
        )
        shaft_hole.apply_translation([x, y, FLOOR_T / 2.0])
        body = body.difference(shaft_hole)

    # Усиление вокруг каждого отверстия — кольцевая бобышка СВЕРХУ
    # (не снизу — снизу важна ровная плоскость для опоры коробки)
    for ang in SHAFT_ANGLES:
        x, y = xy(ang, SHAFT_R)
        boss = trimesh.creation.cylinder(
            radius=SHAFT_BOSS_R,
            height=SHAFT_BOSS_H,
            sections=SEG,
        )
        boss.apply_translation([x, y, FLOOR_T + SHAFT_BOSS_H / 2.0])
        # сверлим в бобышке clearance hole
        boss_hole = trimesh.creation.cylinder(
            radius=SHAFT_CLEAR_R,
            height=SHAFT_BOSS_H * 4,
            sections=SEG,
        )
        boss_hole.apply_translation([x, y, FLOOR_T + SHAFT_BOSS_H / 2.0])
        boss = boss.difference(boss_hole)
        body = body.union(boss)

    # 4 угла × 2 M5 отверстия (по одному на каждой из двух стенок угла).
    # Всего 8 отверстий. Сокет с L-фланцем будет захватывать угол
    # одним болтом через каждую стенку.
    corners = [
        (+OUTER_X / 2.0, +OUTER_Y / 2.0),
        (-OUTER_X / 2.0, +OUTER_Y / 2.0),
        (-OUTER_X / 2.0, -OUTER_Y / 2.0),
        (+OUTER_X / 2.0, -OUTER_Y / 2.0),
    ]
    rot_y = trimesh.transformations.rotation_matrix(math.radians(90), [0, 1, 0])
    rot_x = trimesh.transformations.rotation_matrix(math.radians(90), [1, 0, 0])
    for cx, cy in corners:
        sign_x = 1 if cx > 0 else -1
        sign_y = 1 if cy > 0 else -1

        # Отверстие #1 — на X-перпендикулярной стенке (ось болта = X).
        # Y-координата: отступ CORNER_M5_INSET от угла внутрь стенки.
        bolt_x_axis = trimesh.creation.cylinder(
            radius=CORNER_M5_HOLE_R, height=WALL_T * 4, sections=32
        )
        bolt_x_axis.apply_transform(rot_y)
        bolt_x_axis.apply_translation(
            [cx - sign_x * WALL_T / 2.0,
             cy - sign_y * CORNER_M5_INSET,
             CORNER_M5_Z]
        )
        body = body.difference(bolt_x_axis)

        # Отверстие #2 — на Y-перпендикулярной стенке (ось болта = Y).
        # X-координата: отступ CORNER_M5_INSET от угла внутрь стенки.
        bolt_y_axis = trimesh.creation.cylinder(
            radius=CORNER_M5_HOLE_R, height=WALL_T * 4, sections=32
        )
        bolt_y_axis.apply_transform(rot_x)
        bolt_y_axis.apply_translation(
            [cx - sign_x * CORNER_M5_INSET,
             cy - sign_y * WALL_T / 2.0,
             CORNER_M5_Z]
        )
        body = body.difference(bolt_y_axis)

    # 4 окна в стенках (по одному в каждой стенке) — облегчение и
    # вентиляция. Делаем закруглённые прямоугольные.
    # Окна в стенках, перпендикулярных X (левая и правая):
    for sign in (+1, -1):
        wnd = trimesh.creation.box(
            extents=(WALL_T * 4, WINDOW_W, WINDOW_H)
        )
        wnd.apply_translation([sign * (INSIDE_X / 2.0 + WALL_T / 2.0),
                                0, WINDOW_CENTER_Z])
        body = body.difference(wnd)
    # Окна в стенках, перпендикулярных Y (передняя и задняя):
    for sign in (+1, -1):
        wnd = trimesh.creation.box(
            extents=(WINDOW_W, WALL_T * 4, WINDOW_H)
        )
        wnd.apply_translation([0, sign * (INSIDE_Y / 2.0 + WALL_T / 2.0),
                                WINDOW_CENTER_Z])
        body = body.difference(wnd)

    body.export(OUT_FILE)
    e = body.extents
    print(f"  -> {OUT_FILE.name}  {len(body.faces)} faces, "
          f"{e[0]:.1f}x{e[1]:.1f}x{e[2]:.1f}mm")
    print()
    print(f"  Внутри: {INSIDE_X:.0f}×{INSIDE_Y:.0f}×{HEIGHT - FLOOR_T:.0f}мм")
    print(f"  Снаружи: {OUTER_X:.0f}×{OUTER_Y:.0f}×{HEIGHT:.0f}мм")
    print()
    print("  Шпильки M8 — на радиусе r=132мм, углы 30°/150°/270°")
    print("  Сокеты под стойки — печатать отдельно (4 шт),")
    print(f"  крепятся 2 M5 болтами на угол (по одному на каждой стенке угла), z={CORNER_M5_Z}")


if __name__ == "__main__":
    main()
