#!/usr/bin/env python3
"""
Truss_socket.stl — клипса под алюминиевую стойку Ø21.2-21.5мм.

Печатается 8 шт (4 для mirror box, 4 для UTA — одинаковые).

Конструкция:
  * Вертикальный цилиндр-зажим OD 32мм, ID 22мм (с зазором под Ø21.5
    стойку, после затяжки зажима внутренний диаметр сжимается до ~21мм
    и прочно гриппит стойку).
  * Вертикальная радиальная прорезь (2мм) на стороне ОБРАТНОЙ от угла
    коробки — для зажима. Два уха-проушины с внешней стороны прорези
    с поперечным сквозным M5 отверстием под зажимной болт + барашек.
  * L-образный фланец на стороне КОРПУСА коробки: 2 перпендикулярных
    крыла, каждое прижимается к одной стенке угла и крепится одним
    M5×?? болтом сквозь стенку коробки в гайку с внутренней стороны.

Геометрия привязана к Mirror_box.stl (углы):
  Для +X,+Y угла коробки (outer corner at (+151, +151)):
    - Болт на +X стенке коробки: (148, 126, 100), ось X
    - Болт на +Y стенке коробки: (126, 148, 100), ось Y
  Центр зажимного цилиндра располагаем при (167, 167) — диагональ
  +X+Y от угла наружу на 16мм. Прорезь смотрит в +X+Y направлении,
  крылья фланца — в -X и -Y от центра.

Для других углов коробки клипса вращается на 90°/180°/270° вокруг Z
(в слайсере или клонированием).

Печать:
  * Стоит вертикально (Z = ось зажимного цилиндра).
  * 0.4мм сопло · 0.2мм слой · 5+ периметров · 25-30% gyroid · PETG-HF.
  * Без поддержек (всё печатается as-is).
  * ~1.5ч печать каждая, 8 шт = ~12ч на принтере.
"""
import math
from pathlib import Path

import trimesh

# === Привязка к Mirror_box.stl ===
BOX_OUTER_HALF = 302.0 / 2.0     # 151мм (внешний полуразмер коробки)
BOX_WALL_T = 6.0
BOX_M5_INSET = 25.0              # отступ M5 отверстий от угла внутрь
BOX_M5_Z = 100.0                 # высота M5 отверстий в стенке

# === Размеры стойки ===
TUBE_OD_MAX = 21.5
TUBE_OD_MIN = 21.2
BORE_R = (TUBE_OD_MAX + 0.5) / 2.0   # Ø22 — clearance для свободного входа
# при зажиме (прорезь сужается на ~1.5мм) диаметр сожмётся до ~Ø20.7
# что даёт надёжную посадку на 21.2-21.5мм стойку.

# === Зажимной цилиндр (тело клипсы) ===
BODY_OD_R = 17.0                 # Ø34 — толщина стенки 6мм для жёсткости
BODY_Z_BOT = 80.0                # нижний край (z=80 в мире коробки)
BODY_Z_TOP = 200.0               # верхний край
BODY_H = BODY_Z_TOP - BODY_Z_BOT # 120мм высота клипсы

# Положение центра клипсы (для +X,+Y угла коробки)
CORNER_OUT = 16.0                # отступ центра от внешнего угла коробки
                                 # по диагонали наружу
BODY_X = BOX_OUTER_HALF + CORNER_OUT  # 167
BODY_Y = BOX_OUTER_HALF + CORNER_OUT  # 167

# === Прорезь и проушины (для зажимной M5) ===
SLIT_W = 2.0                     # ширина прорези (тангенциальная)
SLIT_ANGLE_DEG = 45.0            # направление прорези в мире коробки

LUG_RADIAL = 12.0                # выступ проушины наружу от BODY_OD_R
LUG_TANG = 9.0                   # тангенциальная толщина каждой проушины
LUG_Z_CENTER = 140.0             # середина проушины по высоте (z в мире)
LUG_H = 22.0                     # высота проушины

CLAMP_BOLT_R = 2.75              # Ø5.5 clearance под M5
# Нут-карман на одной из проушин (M5 hex AF=8)
CLAMP_NUT_AF = 8.0
CLAMP_NUT_DEPTH = 5.0

# === L-фланец (крепление к углу коробки) ===
WING_THICK = 5.0                 # толщина фланца
WING_LEN = 45.0                  # длина крыла вдоль стенки
WING_H = 50.0                    # высота крыла (z=80 до z=130)
WING_Z_BOT = 80.0
WING_Z_TOP = 130.0
WING_BOLT_R = 2.75               # Ø5.5 clearance под M5

# === Corner bridge — заполняет диагональный gap между крыльями и зажимом ===
# Без этого крылья (на (151..156)) и цилиндр зажима (центр 167, r=17) не имеют
# объёмного перекрытия в union — получаются 3 разрозненных тела в STL.
# Bridge — кубик 7×7×50мм в углу (150..157, 150..157, z=80..130),
# который ОБЯЗАТЕЛЬНО перекрывается и с обоими крыльями (≥1мм), и с цилиндром.
BRIDGE_X_MIN = BOX_OUTER_HALF - 1.0        # 150 (на 1мм внутрь от стенки коробки)
BRIDGE_X_MAX = BOX_OUTER_HALF + 6.0        # 157 (внутри цилиндра: r от центра ≈14<17)
BRIDGE_Y_MIN = BOX_OUTER_HALF - 1.0
BRIDGE_Y_MAX = BOX_OUTER_HALF + 6.0
BRIDGE_Z_BOT = WING_Z_BOT
BRIDGE_Z_TOP = WING_Z_TOP

# === Прочее ===
SEG = 96
OUT_DIR = Path(__file__).parent
OUT_FILE = OUT_DIR / "Truss_socket.stl"


def main():
    # 1) Зажимной цилиндр + вычитание бора
    body = trimesh.creation.cylinder(
        radius=BODY_OD_R, height=BODY_H, sections=SEG
    )
    body.apply_translation([BODY_X, BODY_Y, (BODY_Z_TOP + BODY_Z_BOT) / 2.0])

    bore = trimesh.creation.cylinder(
        radius=BORE_R, height=BODY_H * 2, sections=SEG
    )
    bore.apply_translation([BODY_X, BODY_Y, (BODY_Z_TOP + BODY_Z_BOT) / 2.0])
    body = body.difference(bore)

    # 2) Прорезь — тонкий вертикальный паз в стене цилиндра,
    # направлен в +X+Y (наружу от угла коробки).
    # Делаем как тонкий box и вычитаем.
    slit_len_radial = BODY_OD_R + LUG_RADIAL + 5.0  # от bore до за пределы проушин
    slit = trimesh.creation.box(
        extents=(slit_len_radial, SLIT_W, BODY_H + LUG_H + 4)
    )
    # Сдвинуть так чтобы один конец паза был у bore (близко к центру),
    # другой — выступал за пределы проушин.
    slit.apply_translation([slit_len_radial / 2.0, 0, 0])
    # Повернуть на 45° (направление наружу от +X+Y угла) и перенести к BODY_X,Y
    rot = trimesh.transformations.rotation_matrix(
        math.radians(SLIT_ANGLE_DEG), [0, 0, 1]
    )
    slit.apply_transform(rot)
    slit.apply_translation([BODY_X, BODY_Y, (BODY_Z_TOP + BODY_Z_BOT) / 2.0])
    body = body.difference(slit)

    # 3) Проушины — две тангенциальные "уши" по обе стороны прорези,
    # с поперечным сквозным M5 отверстием.
    # В локальной системе клипсы (без поворота): прорезь по +X,
    # проушины по ±Y от прорези, выступающие на LUG_RADIAL наружу.
    # После поворота на 45° они станут на диагонали.
    for sign in (+1, -1):
        # Положение проушины в локальной системе
        lug = trimesh.creation.box(
            extents=(LUG_RADIAL + 2.0, LUG_TANG, LUG_H)
        )
        # Сдвинуть так чтобы внутренний край проушины был у внешней
        # поверхности цилиндра (x=BODY_OD_R), внешний край — на LUG_RADIAL дальше.
        # И тангенциально — отступить на SLIT_W/2 + LUG_TANG/2 от центра прорези.
        lug.apply_translation([
            BODY_OD_R + (LUG_RADIAL + 2.0) / 2.0 - 1.0,
            sign * (SLIT_W / 2.0 + LUG_TANG / 2.0),
            0,
        ])
        # Повернуть на SLIT_ANGLE_DEG
        lug.apply_transform(rot)
        lug.apply_translation([BODY_X, BODY_Y, LUG_Z_CENTER])
        body = body.union(lug)

    # 4) Зажимной болт — отверстие через обе проушины,
    # ось перпендикулярна оси прорези в локальной системе (= перпендикулярно
    # +X в локалке, то есть вдоль Y в локалке; после поворота на 45° — вдоль
    # перпендикулярной диагонали в мире).
    clamp_bolt = trimesh.creation.cylinder(
        radius=CLAMP_BOLT_R,
        height=(LUG_TANG * 2 + SLIT_W) * 1.5,
        sections=32,
    )
    # ось цилиндра по умолчанию Z; повернуть так чтобы стала Y в локалке.
    rot_to_y = trimesh.transformations.rotation_matrix(
        math.radians(90), [1, 0, 0]
    )
    clamp_bolt.apply_transform(rot_to_y)
    # сдвинуть в положение проушин (центр оси на радиальной позиции
    # середины проушин)
    clamp_bolt.apply_translation([
        BODY_OD_R + LUG_RADIAL / 2.0, 0, 0
    ])
    # повернуть на 45° к мировому фрейму
    clamp_bolt.apply_transform(rot)
    clamp_bolt.apply_translation([BODY_X, BODY_Y, LUG_Z_CENTER])
    body = body.difference(clamp_bolt)

    # Hex карман в одной из проушин под гайку M5 (со стороны -Y в локалке)
    hex_pocket = trimesh.creation.cylinder(
        radius=CLAMP_NUT_AF / math.cos(math.radians(30)) / 2.0,
        height=CLAMP_NUT_DEPTH,
        sections=6,
    )
    hex_pocket.apply_transform(rot_to_y)  # ось по Y в локалке
    # положение: радиальная позиция проушины, тангенциально на -Y стороне,
    # внутрь от внешнего края проушины
    hex_pocket.apply_translation([
        BODY_OD_R + LUG_RADIAL / 2.0,
        -(SLIT_W / 2.0 + LUG_TANG - CLAMP_NUT_DEPTH / 2.0),
        0
    ])
    hex_pocket.apply_transform(rot)
    hex_pocket.apply_translation([BODY_X, BODY_Y, LUG_Z_CENTER])
    body = body.difference(hex_pocket)

    # 5a) Corner bridge — заполняет диагональный gap между крыльями и зажимом.
    # Без bridge'а у крыльев нет объёмного перекрытия с цилиндром (есть только
    # потенциальное касание по линии), и union даёт 3 разрозненных тела в STL.
    bridge = trimesh.creation.box(extents=(
        BRIDGE_X_MAX - BRIDGE_X_MIN,
        BRIDGE_Y_MAX - BRIDGE_Y_MIN,
        BRIDGE_Z_TOP - BRIDGE_Z_BOT,
    ))
    bridge.apply_translation([
        (BRIDGE_X_MIN + BRIDGE_X_MAX) / 2.0,
        (BRIDGE_Y_MIN + BRIDGE_Y_MAX) / 2.0,
        (BRIDGE_Z_BOT + BRIDGE_Z_TOP) / 2.0,
    ])
    body = body.union(bridge)

    # 5b) L-фланец — два крыла на -X и -Y стенках клипсы.
    # Крыло #1 — лежит на +X стенке коробки СНАРУЖИ (т.е. при x = BOX_OUTER_HALF + WING_THICK/2)
    # Простирается тангенциально в направлении -Y от угла коробки.
    wing1 = trimesh.creation.box(
        extents=(WING_THICK, WING_LEN, WING_H)
    )
    wing1_x = BOX_OUTER_HALF + WING_THICK / 2.0  # 151+2.5 = 153.5
    wing1_y = BOX_OUTER_HALF - WING_LEN / 2.0    # 151 - 22.5 = 128.5
    wing1_z = (WING_Z_BOT + WING_Z_TOP) / 2.0    # 105
    wing1.apply_translation([wing1_x, wing1_y, wing1_z])
    body = body.union(wing1)

    # M5 отверстие в крыле #1 — на оси X, в координате y=BOX_OUTER_HALF - BOX_M5_INSET = 126
    wing1_bolt = trimesh.creation.cylinder(
        radius=WING_BOLT_R, height=WING_THICK * 4, sections=32
    )
    rot_x_to_y = trimesh.transformations.rotation_matrix(
        math.radians(90), [0, 1, 0]
    )
    wing1_bolt.apply_transform(rot_x_to_y)
    wing1_bolt.apply_translation([wing1_x, BOX_OUTER_HALF - BOX_M5_INSET, BOX_M5_Z])
    body = body.difference(wing1_bolt)

    # Крыло #2 — на +Y стенке коробки СНАРУЖИ, симметрично крылу #1
    wing2 = trimesh.creation.box(
        extents=(WING_LEN, WING_THICK, WING_H)
    )
    wing2_x = BOX_OUTER_HALF - WING_LEN / 2.0
    wing2_y = BOX_OUTER_HALF + WING_THICK / 2.0
    wing2_z = (WING_Z_BOT + WING_Z_TOP) / 2.0
    wing2.apply_translation([wing2_x, wing2_y, wing2_z])
    body = body.union(wing2)

    wing2_bolt = trimesh.creation.cylinder(
        radius=WING_BOLT_R, height=WING_THICK * 4, sections=32
    )
    rot_x_to_x = trimesh.transformations.rotation_matrix(
        math.radians(90), [1, 0, 0]
    )
    wing2_bolt.apply_transform(rot_x_to_x)
    wing2_bolt.apply_translation([BOX_OUTER_HALF - BOX_M5_INSET, wing2_y, BOX_M5_Z])
    body = body.difference(wing2_bolt)

    body.export(OUT_FILE)
    e = body.extents
    print(f"  -> {OUT_FILE.name}  {len(body.faces)} faces, "
          f"{e[0]:.1f}x{e[1]:.1f}x{e[2]:.1f}mm")
    print()
    print(f"  Зажимной бор: Ø{BORE_R*2:.1f}мм (для стойки Ø{TUBE_OD_MIN}-{TUBE_OD_MAX}мм)")
    print(f"  Клипса в мире коробки: центр ({BODY_X:.0f}, {BODY_Y:.0f}),")
    print(f"  z от {BODY_Z_BOT:.0f} до {BODY_Z_TOP:.0f}мм")
    print()
    print("  Печать: 8 шт (4 для mirror box + 4 для UTA), стоит,")
    print("  поворачивать в слайсере на 90°/180°/270° для остальных углов.")


if __name__ == "__main__":
    main()
