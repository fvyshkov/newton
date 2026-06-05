#!/usr/bin/env python3
"""
Жёсткий кронштейн оправы (Cell_leg_bracket.stl) для truss-варианта 8" Newton.

Печатается 3 шт. НЕТ регулировки высоты на этом стыке — оправа крепится
к коробке жёстко, а всю настройку (наклон-коллимация И осевой сдвиг)
делают штатные push-pull барашки между задней и передней плитой оправы
(generate_mirror_cell.py). Точный фокус добирается фокусёром.

Это упрощение относительно прежней версии (шпилька M8 + два барашка):
шпильки/барашки M8 больше не нужны, и исчез баг пересечения болта M5 со
шпилькой.

Два крепёжных стыка кронштейна (разнесены по высоте, не пересекаются):

  1) ГОРИЗОНТАЛЬНО — к уху задней плиты:
     болт M5 ИЗНУТРИ ячейки сквозь радиальное Ø5.5 отверстие в ухе
     (r=125) → в сквозное Ø5.5 кронштейна → в гайку M5, сидящую в
     шестигранном кармане на внешней грани. (как и было)

  2) ВЕРТИКАЛЬНО — к дну коробки:
     болт M5 СНИЗУ (из-под дна) сквозь существующее Ø9 отверстие дна
     (r=132) + шайба под дном → вверх в кронштейн → в гайку M5,
     задвинутую в боковой паз-карман у основания кронштейна.

Высота STANDOFF задаёт грубое осевое положение зеркала. Если зеркало
встанет не на месте — перепечатать кронштейн с другим STANDOFF (деталь
маленькая, печать быстрая). Тонкая подстройка — push-pull + фокусёр.

Печать: стоя (Z вертикально), 4-5 периметров, 30% gyroid, PETG-HF/ASA.
Горизонтальное отверстие M5 печатается как мост — допустимо на 5.5мм.
"""
import math
from pathlib import Path

import trimesh

# --- Привязка к существующей геометрии ---
EAR_R = 125.0          # радиус наружной поверхности уха задней плиты
FLOOR_HOLE_R = 132.0   # радиус отверстия в дне коробки (под верт. болт)
X_FLOOR = FLOOR_HOLE_R - EAR_R   # = 7мм: положение верт. болта в локале

# --- Габариты кронштейна ---
STANDOFF_H = 30.0      # высота оси отверстия уха над верхом дна коробки
                       # = на этой высоте сядет середина задней плиты
TOP_MARGIN = 8.0       # материал над отверстием уха
BR_T = 16.0            # радиальная толщина (x: 0..16), покрывает X_FLOOR=7
BR_W = 26.0            # тангенциальная ширина (y: -13..13)
H_TOP = STANDOFF_H + TOP_MARGIN  # полная высота кронштейна

# --- Отверстия ---
M5_CLR_R = 2.75        # Ø5.5 clearance под M5
NUT_AF = 8.0           # M5 hex гайка под ключ
NUT_CIRC_R = NUT_AF / math.cos(math.radians(30)) / 2.0  # описанный радиус
NUT_TH = 4.6           # толщина гайки + запас

# Карман гайки уха (горизонтальный, ось X, на внешней грани)
EAR_NUT_DEPTH = 5.0

# Вертикальный болт к дну + боковой паз под гайку
FLOOR_NUT_Z = 8.0      # высота центра гайки над низом кронштейна

# Вогнутая внутренняя грань под цилиндр уха
INNER_CONCAVE = True

OUT_DIR = Path(__file__).parent
OUT_FILE = OUT_DIR / "Cell_leg_bracket.stl"


def main():
    # Локальные координаты:
    #   x — радиально наружу (x=0 = внутренняя грань, садится на ухо r=125)
    #   y — тангенциально
    #   z — вертикально (z=0 = низ кронштейна, стоит на дне коробки)

    body = trimesh.creation.box(extents=(BR_T, BR_W, H_TOP))
    body.apply_translation([BR_T / 2.0, 0.0, H_TOP / 2.0])

    # Вогнутая внутренняя грань (вырез цилиндра r=EAR_R)
    if INNER_CONCAVE:
        ear_cyl = trimesh.creation.cylinder(
            radius=EAR_R, height=H_TOP * 3, sections=256
        )
        ear_cyl.apply_translation([-EAR_R, 0.0, H_TOP / 2.0])
        body = body.difference(ear_cyl)

    rot_y = trimesh.transformations.rotation_matrix(math.radians(90), [0, 1, 0])

    # 1) Горизонтальное сквозное Ø5.5 к уху (ось X), на высоте STANDOFF_H
    m5h = trimesh.creation.cylinder(radius=M5_CLR_R, height=BR_T * 3, sections=64)
    m5h.apply_transform(rot_y)
    m5h.apply_translation([BR_T / 2.0, 0.0, STANDOFF_H])
    body = body.difference(m5h)

    # 1a) Шестигранный карман под гайку M5 уха — на внешней грани (x=BR_T)
    ear_hex = trimesh.creation.cylinder(
        radius=NUT_CIRC_R, height=EAR_NUT_DEPTH, sections=6
    )
    ear_hex.apply_transform(rot_y)
    ear_hex.apply_translation(
        [BR_T - EAR_NUT_DEPTH / 2.0, 0.0, STANDOFF_H]
    )
    body = body.difference(ear_hex)

    # 2) Вертикальное Ø5.5 к дну (ось Z), при x=X_FLOOR.
    # ТОЛЬКО в основании: от низа до чуть выше гайки, чтобы не дойти до
    # горизонтального отверстия уха (z=STANDOFF_H) — иначе они пересекутся.
    m5v_h = FLOOR_NUT_Z + NUT_TH / 2.0 + 5.0   # верх отверстия ~15мм
    m5v = trimesh.creation.cylinder(radius=M5_CLR_R, height=m5v_h + 8, sections=64)
    m5v.apply_translation([X_FLOOR, 0.0, (m5v_h - 8) / 2.0])
    body = body.difference(m5v)

    # 2a) Вертикальный шестигранный карман под гайку M5 дна
    floor_hex = trimesh.creation.cylinder(
        radius=NUT_CIRC_R, height=NUT_TH, sections=6
    )
    floor_hex.apply_translation([X_FLOOR, 0.0, FLOOR_NUT_Z])
    body = body.difference(floor_hex)

    # 2b) Боковой паз от внешней грани к карману — вставить гайку сбоку
    slot = trimesh.creation.box(extents=(BR_T, NUT_AF, NUT_TH))
    slot.apply_translation([X_FLOOR + BR_T / 2.0, 0.0, FLOOR_NUT_Z])
    body = body.difference(slot)

    body.export(OUT_FILE)
    e = body.extents
    print(f"  -> {OUT_FILE.name}  {len(body.faces)} faces, "
          f"{e[0]:.1f}x{e[1]:.1f}x{e[2]:.1f}mm")
    print()
    print(f"  STANDOFF_H = {STANDOFF_H:.0f}мм  (середина задней плиты над дном)")
    print(f"  Низ задней плиты над дном ≈ {STANDOFF_H - 4:.0f}мм "
          f"(зазор под push-pull гайки)")
    print()
    print("Сборка:")
    print("  1. Гайку M5 задвинуть в боковой паз у основания (над верт.")
    print("     отверстием). Каплей клея зафиксировать.")
    print("  2. Гайку M5 вдавить в шестигранный карман на внешней грани")
    print("     (под болт уха).")
    print("  3. Кронштейн поставить на дно коробки над Ø9 отверстием,")
    print("     болт M5 СНИЗУ (из-под дна) + шайба → в нижнюю гайку.")
    print("  4. Ухо задней плиты прижать к вогнутой грани, болт M5")
    print("     ИЗНУТРИ ячейки сквозь ухо → в кронштейн → в гайку.")
    print("  5. Коллимация и фокус — штатными push-pull барашками оправы.")


if __name__ == "__main__":
    main()
