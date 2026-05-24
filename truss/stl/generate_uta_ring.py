#!/usr/bin/env python3
"""
UTA_ring.stl — Upper Tube Assembly для truss-варианта 8" Newton.

Гибридная конструкция:
  * Нижняя часть — квадратная рамка 302×302мм (внешняя), 290×290мм (внутренняя),
    высота 120мм. По крепежу 1-в-1 совпадает с Mirror_box.stl — те же сокеты
    Truss_socket.stl присоединяются теми же M5 болтами, но перевёрнутые на 180°.
  * Переходная горизонтальная плита (z=120 до z=128) с отверстием Ø240мм
    в центре — соединяет квадратную рамку с цилиндром выше.
  * Верхняя часть — цилиндрическое кольцо ID 240мм, OD 260мм, высота 172мм.
    Внутри сидит вторичка на пауке. На +X стенке — сквозное окно Ø55мм под
    световой конус, идущий в фокусер. Вокруг окна — 4 M5 отверстия под
    крепление фокусерного седла (Focuser_saddle.stl из старого проекта).
  * 4 M5 сквозных отверстия в цилиндре под крепление лопастей паука
    (Spider_4vane.stl) на углах 45°/135°/225°/315° (между фокусером и
    стойками), на высоте центра вторички.

Геометрия привязки (UTA local frame, z=0 в основании):
  * UTA bottom (frame): z=0
  * UTA M5 corner holes (под Truss_socket): z=100 (20мм от верха рамки)
  * Cylinder bottom: z=128
  * Secondary center: z=222 (соответствует z=1082 в мире сборки)
  * Cylinder top: z=300

Параметры мира сборки (для справки):
  * UTA нижний край: z_world = 860мм
  * Вторичка: z_world = 1082мм
  * UTA верхний край: z_world = 1160мм
  * Это даёт D1 = 960мм от поверхности зеркала (z_world ≈ 122) до вторички.

Печать:
  * Ориентация: квадратной рамкой вниз на стол, цилиндр строится вверх.
  * Высота 300мм — Bambu H2D берёт (рабочая высота 325мм).
  * 0.4мм сопло · 0.2мм слой · 5+ периметров · 25-30% gyroid · PETG-HF.
  * Поддержки нужны только под переходную плиту в районе перехода
    квадрат→цилиндр (~5мм над аркой). Slicer auto-support справится.
  * brim 5мм для адгезии.
  * ~20-22 часа печати.
"""
import math
from pathlib import Path

import trimesh

# === Размеры (UTA local frame) ===
OUTER_X = 302.0
OUTER_Y = 302.0
INSIDE_X = 290.0
INSIDE_Y = 290.0
WALL_T = 6.0
FRAME_H = 120.0                  # высота квадратной рамки

CYL_ID = 240.0
CYL_OD = 260.0
CYL_BOTTOM = 128.0               # начало цилиндра (после переходной плиты)
CYL_TOP = 300.0
CYL_H = CYL_TOP - CYL_BOTTOM

TRANSITION_T = 8.0               # толщина переходной горизонтальной плиты

# === Угловые M5 отверстия (под Truss_socket, перевёрнутые на 180°) ===
CORNER_M5_HOLE_R = 2.75
CORNER_M5_Z = 100.0              # как у mirror box
CORNER_M5_INSET = 25.0

# === Окно под световой конус к фокусеру ===
LIGHT_WINDOW_R = 27.5            # Ø55мм
LIGHT_WINDOW_Z = 222.0           # высота центра вторички

# === Крепление фокусерного седла ===
SADDLE_M5_R = 2.75
# 4 отверстия в прямоугольном паттерне на +X стенке вокруг светового окна
SADDLE_BOLT_TANG_HALF = 35.0     # тангенциальное полу-расстояние (~ chord)
SADDLE_BOLT_Z_HALF = 30.0        # вертикальное полу-расстояние

# === Крепление лопастей паука ===
SPIDER_M5_R = 2.75
SPIDER_ANGLES = [45.0, 135.0, 225.0, 315.0]

# === Окна облегчения в квадратной рамке ===
WINDOW_W = 80.0
WINDOW_H = 60.0
WINDOW_CENTER_Z = 50.0

SEG = 96
OUT_DIR = Path(__file__).parent
OUT_FILE = OUT_DIR / "UTA_ring.stl"


def main():
    # 1) Квадратная рамка низа
    outer_frame = trimesh.creation.box(extents=(OUTER_X, OUTER_Y, FRAME_H))
    outer_frame.apply_translation([0, 0, FRAME_H / 2.0])

    inner_frame = trimesh.creation.box(
        extents=(INSIDE_X, INSIDE_Y, FRAME_H + 0.2)
    )
    inner_frame.apply_translation([0, 0, FRAME_H / 2.0])

    body = outer_frame.difference(inner_frame)

    # 2) Переходная горизонтальная плита (квадрат снаружи, круг внутри)
    transition_outer = trimesh.creation.box(
        extents=(OUTER_X, OUTER_Y, TRANSITION_T)
    )
    transition_outer.apply_translation([0, 0, FRAME_H + TRANSITION_T / 2.0])

    transition_hole = trimesh.creation.cylinder(
        radius=CYL_ID / 2.0, height=TRANSITION_T * 2, sections=SEG
    )
    transition_hole.apply_translation([0, 0, FRAME_H + TRANSITION_T / 2.0])

    transition = transition_outer.difference(transition_hole)
    body = body.union(transition)

    # 3) Цилиндрическое кольцо
    cyl_outer = trimesh.creation.cylinder(
        radius=CYL_OD / 2.0, height=CYL_H, sections=SEG
    )
    cyl_outer.apply_translation([0, 0, CYL_BOTTOM + CYL_H / 2.0])

    cyl_inner = trimesh.creation.cylinder(
        radius=CYL_ID / 2.0, height=CYL_H + 0.2, sections=SEG
    )
    cyl_inner.apply_translation([0, 0, CYL_BOTTOM + CYL_H / 2.0])

    cylinder = cyl_outer.difference(cyl_inner)
    body = body.union(cylinder)

    # 4) Угловые M5 отверстия для крепления Truss_socket
    corners = [
        (+OUTER_X / 2.0, +OUTER_Y / 2.0),
        (-OUTER_X / 2.0, +OUTER_Y / 2.0),
        (-OUTER_X / 2.0, -OUTER_Y / 2.0),
        (+OUTER_X / 2.0, -OUTER_Y / 2.0),
    ]
    rot_y90 = trimesh.transformations.rotation_matrix(math.radians(90), [0, 1, 0])
    rot_x90 = trimesh.transformations.rotation_matrix(math.radians(90), [1, 0, 0])
    for cx, cy in corners:
        sign_x = 1 if cx > 0 else -1
        sign_y = 1 if cy > 0 else -1

        # Отверстие #1 на X-перпендикулярной стенке
        bolt_x = trimesh.creation.cylinder(
            radius=CORNER_M5_HOLE_R, height=WALL_T * 4, sections=32
        )
        bolt_x.apply_transform(rot_y90)
        bolt_x.apply_translation([
            cx - sign_x * WALL_T / 2.0,
            cy - sign_y * CORNER_M5_INSET,
            CORNER_M5_Z
        ])
        body = body.difference(bolt_x)

        # Отверстие #2 на Y-перпендикулярной стенке
        bolt_y = trimesh.creation.cylinder(
            radius=CORNER_M5_HOLE_R, height=WALL_T * 4, sections=32
        )
        bolt_y.apply_transform(rot_x90)
        bolt_y.apply_translation([
            cx - sign_x * CORNER_M5_INSET,
            cy - sign_y * WALL_T / 2.0,
            CORNER_M5_Z
        ])
        body = body.difference(bolt_y)

    # 5) Окна облегчения в квадратной рамке
    for sign in (+1, -1):
        wnd = trimesh.creation.box(
            extents=(WALL_T * 4, WINDOW_W, WINDOW_H)
        )
        wnd.apply_translation(
            [sign * (INSIDE_X / 2.0 + WALL_T / 2.0), 0, WINDOW_CENTER_Z]
        )
        body = body.difference(wnd)
    for sign in (+1, -1):
        wnd = trimesh.creation.box(
            extents=(WINDOW_W, WALL_T * 4, WINDOW_H)
        )
        wnd.apply_translation(
            [0, sign * (INSIDE_Y / 2.0 + WALL_T / 2.0), WINDOW_CENTER_Z]
        )
        body = body.difference(wnd)

    # 6) Световое окно под фокусер — Ø55 сквозь +X стенку цилиндра
    light_wnd = trimesh.creation.cylinder(
        radius=LIGHT_WINDOW_R,
        height=(CYL_OD - CYL_ID) * 4,
        sections=SEG,
    )
    light_wnd.apply_transform(rot_y90)
    light_wnd.apply_translation([CYL_OD / 2.0, 0, LIGHT_WINDOW_Z])
    body = body.difference(light_wnd)

    # 7) 4 M5 отверстия под фокусерное седло (вокруг светового окна)
    for sign_z in (+1, -1):
        for sign_tang in (+1, -1):
            # Тангенциальная координата на цилиндре радиуса CYL_OD/2
            # Положение по углу: chord на радиусе ≈ SADDLE_BOLT_TANG_HALF
            angle = sign_tang * math.degrees(
                math.asin(SADDLE_BOLT_TANG_HALF / (CYL_OD / 2.0))
            )
            rad = math.radians(angle)
            saddle_hole = trimesh.creation.cylinder(
                radius=SADDLE_M5_R,
                height=(CYL_OD - CYL_ID) * 4,
                sections=32,
            )
            # Отверстие идёт радиально — ось вдоль (cos a, sin a, 0)
            saddle_hole.apply_transform(rot_y90)
            # Поворот на нужный угол вокруг Z
            rot_z = trimesh.transformations.rotation_matrix(rad, [0, 0, 1])
            saddle_hole.apply_transform(rot_z)
            x = (CYL_OD / 2.0) * math.cos(rad)
            y = (CYL_OD / 2.0) * math.sin(rad)
            saddle_hole.apply_translation(
                [x, y, LIGHT_WINDOW_Z + sign_z * SADDLE_BOLT_Z_HALF]
            )
            body = body.difference(saddle_hole)

    # 8) 4 M5 отверстия под лопасти паука — на 45°/135°/225°/315°,
    # на высоте центра вторички
    for ang_deg in SPIDER_ANGLES:
        a = math.radians(ang_deg)
        spider_hole = trimesh.creation.cylinder(
            radius=SPIDER_M5_R,
            height=(CYL_OD - CYL_ID) * 4,
            sections=32,
        )
        spider_hole.apply_transform(rot_y90)
        rot_z = trimesh.transformations.rotation_matrix(a, [0, 0, 1])
        spider_hole.apply_transform(rot_z)
        x = (CYL_OD / 2.0) * math.cos(a)
        y = (CYL_OD / 2.0) * math.sin(a)
        spider_hole.apply_translation([x, y, LIGHT_WINDOW_Z])
        body = body.difference(spider_hole)

    body.export(OUT_FILE)
    e = body.extents
    print(f"  -> {OUT_FILE.name}  {len(body.faces)} faces, "
          f"{e[0]:.1f}x{e[1]:.1f}x{e[2]:.1f}mm")
    print()
    print(f"  Квадратная рамка низа: {OUTER_X:.0f}×{OUTER_Y:.0f}×{FRAME_H:.0f}мм")
    print(f"  Цилиндр: ID{CYL_ID:.0f} OD{CYL_OD:.0f} H{CYL_H:.0f}мм")
    print(f"  Окно фокусера: Ø{LIGHT_WINDOW_R*2:.0f}мм, центр z={LIGHT_WINDOW_Z:.0f}мм")
    print(f"  4 крепления паука: углы {SPIDER_ANGLES}°, z={LIGHT_WINDOW_Z:.0f}мм")
    print()
    print("  Печать: рамкой вниз на стол, цилиндр строится вверх.")
    print("  ~20-22ч на H2D, PETG-HF, 5+ периметров, 30% gyroid.")


if __name__ == "__main__":
    main()
