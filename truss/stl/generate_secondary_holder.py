#!/usr/bin/env python3
"""
Secondary_holder.stl — держатель вторичного зеркала 50мм с коллимацией.

Архитектура (стандартный амер-ATM дизайн):
  * Цилиндрическое тело OD 58мм со срезом 45° сверху — на нём держится
    вторичка (приклеена силиконом по 3 точкам).
  * Срез 45° даёт эллипс 58×82мм, на нём свободно сидит вторичка 50×71мм
    с запасом ~4мм по краям.
  * Снизу — плоский слэб 5мм толщиной, прилегает к hub паука.
  * Центральное сквозное отверстие Ø5.5мм (clearance под M5) для
    натяжного коллимационного болта M5×40 (идёт от низа спайдер-hub
    вверх насквозь до hex кармана на ВЕРХНЕЙ грани слэба).
  * 3 отверстия Ø2.6мм под self-tap M3 коллимационные винты, равномерно
    на радиусе 20мм через 120°. Винты M3×16 нарезают резьбу в PETG, при
    закручивании выходят из нижней грани слэба, упираясь во вторичку...
    нет — упираясь в hub паука и поднимая угол.
  * 1 центральный M5 болт = pull, 3 M3 винта = push.
  * Между слэбом и hub'ом — мягкая пружинка (резинка/винтажная пружина
    компрессии) на M5 болте, держит натяжение.

Сборка коллимации:
  * Болт M5×40 проходит снизу через hub паука, через слэб держателя,
    в hex карман M5 на верхней грани слэба → стягивает в сборе.
  * 3 M3×16 винтов вкручены сверху держателя (доступ с верхнего среза,
    рядом с зеркалом), нижние концы упираются в hub паука.
  * Регулируя 3 M3 — наклон вторички (наводка зайчика на середину
    фокусера). Центральный M5 — натяжение/положение по высоте.

Печать:
  * Слэбом вниз на стол, угол смотрит вверх. Срез самоподдержится
    (это срез цилиндра под 45°, ровный наклон, можно без поддержек,
    но slicer auto-support не помешает).
  * Сопло 0.4мм · слой 0.2мм · 6+ периметров · 30% gyroid · PETG-HF.
  * brim 5мм.
  * ~2-3ч печати.
  * После печати — М3 hole'ы можно прогнать M3 метчиком (если нет —
    просто закручивать M3 винтом до упора, plastic себя нарезает).

Что докупить дополнительно:
  * M5×40 — 1 шт (стяжной коллимационный)
  * M3×16 — 3 шт (push коллимационные)
  * Пружина сжатия Ø6×15мм — 1 шт (вокруг M5 между hub и слэбом)
    либо силиконовое кольцо вместо пружины
"""
import math
from pathlib import Path

import trimesh

# === Размеры держателя ===
BODY_R = 29.0           # OD 58мм
BODY_H_RAW = 70.0       # высота сырого цилиндра (до среза 45°)
SLAB_T = 5.0            # толщина нижнего слэба

ANGLE_DEG = 45.0
TILT_AXIS = "y"         # ось наклона — вокруг Y; срез смотрит на +X (к фокусеру)

# === Центральный M5 (стяжной) ===
M5_CLEAR_R = 2.75       # Ø5.5 clearance
M5_NUT_AF = 8.0         # M5 hex гайка
M5_NUT_DEPTH = 5.0      # глубина hex кармана на ВЕРХНЕЙ грани слэба

# === 3 M3 коллимационных винта (push) ===
M3_TAP_R = 1.3          # Ø2.6 self-tap hole для M3 в PETG (нарезает сам винт)
M3_RADIUS = 20.0        # от центра держателя
M3_ANGLES = [30.0, 150.0, 270.0]  # 120° apart

# === Вторичное зеркало для справки ===
SECONDARY_MINOR = 50.0
SECONDARY_MAJOR = SECONDARY_MINOR * math.sqrt(2)  # ≈ 70.7мм

SEG = 96
OUT_DIR = Path(__file__).parent
OUT_FILE = OUT_DIR / "Secondary_holder.stl"


def main():
    # 1) Слэб снизу
    slab = trimesh.creation.cylinder(radius=BODY_R, height=SLAB_T, sections=SEG)
    slab.apply_translation([0, 0, SLAB_T / 2.0])

    # 2) Цилиндрическое тело над слэбом (до среза)
    cyl = trimesh.creation.cylinder(radius=BODY_R, height=BODY_H_RAW, sections=SEG)
    cyl.apply_translation([0, 0, SLAB_T + BODY_H_RAW / 2.0])

    body = slab.union(cyl)

    # 3) Срез под 45° сверху
    # Cut plane: проходит через точку (0,0,Z_cut_center) и наклонена на 45° вокруг Y.
    # Normal направлен в (sin45°, 0, cos45°) = (1/√2, 0, 1/√2).
    # Срез убирает всё, что НАД этой плоскостью.
    # Размещение: низкая точка эллипса на +X стороне находится на z = z_low,
    # высокая точка на -X стороне на z = z_low + 2*BODY_R = z_low + 58.
    # Выбираю z_low такой, чтобы высокая точка не выходила за BODY_H_RAW+SLAB_T.
    # z_low + 2*BODY_R ≤ SLAB_T + BODY_H_RAW
    # → z_low ≤ SLAB_T + BODY_H_RAW - 2*BODY_R = 5 + 70 - 58 = 17
    # Выбираем z_low = 12 (низкая точка на +X стороне на высоте 12мм над низом)
    z_low = 12.0
    z_high = z_low + 2 * BODY_R  # = 70
    z_cut_center = (z_low + z_high) / 2.0  # = 41

    # Большой куб для среза, повернутый 45° вокруг Y
    cutter = trimesh.creation.box(extents=(300, 300, 300))
    rot = trimesh.transformations.rotation_matrix(
        math.radians(-ANGLE_DEG), [0, 1, 0]
    )
    cutter.apply_transform(rot)
    # После поворота: куб лежит так что его "верхняя" грань — наклонная плоскость
    # с нормалью (sin45°, 0, cos45°). Центр куба сейчас в (0,0,0).
    # Мы хотим, чтобы наклонная грань проходила через точку (0,0,z_cut_center).
    # Сдвиг: переместить центр куба в (0+150/√2, 0, z_cut_center + 150/√2).
    offset = 150.0 / math.sqrt(2)
    cutter.apply_translation([offset, 0, z_cut_center + offset])

    body = body.difference(cutter)

    # 4) Центральное сквозное отверстие M5 (clearance)
    m5 = trimesh.creation.cylinder(
        radius=M5_CLEAR_R, height=BODY_H_RAW * 2, sections=32
    )
    m5.apply_translation([0, 0, BODY_H_RAW])
    body = body.difference(m5)

    # 5) Hex карман на ВЕРХНЕЙ грани слэба (центр) — под M5 hex гайку
    # для стяжного болта
    hex_pocket = trimesh.creation.cylinder(
        radius=M5_NUT_AF / math.cos(math.radians(30)) / 2.0,
        height=M5_NUT_DEPTH,
        sections=6,
    )
    # карман открывается сверху слэба, уходит вниз
    hex_pocket.apply_translation([0, 0, SLAB_T - M5_NUT_DEPTH / 2.0])
    body = body.difference(hex_pocket)

    # 6) 3 сквозных M3 self-tap hole'а на радиусе 20мм, 120° apart
    for ang_deg in M3_ANGLES:
        a = math.radians(ang_deg)
        m3 = trimesh.creation.cylinder(
            radius=M3_TAP_R, height=BODY_H_RAW * 2, sections=24
        )
        m3.apply_translation([
            M3_RADIUS * math.cos(a),
            M3_RADIUS * math.sin(a),
            BODY_H_RAW,
        ])
        body = body.difference(m3)

    body.export(OUT_FILE)
    e = body.extents
    print(f"  -> {OUT_FILE.name}  {len(body.faces)} faces, "
          f"{e[0]:.1f}x{e[1]:.1f}x{e[2]:.1f}mm")
    print()
    print(f"  Тело: Ø{BODY_R*2:.0f}мм, общая высота ~{z_high:.0f}мм")
    print(f"  Эллипс 45° среза: ~{BODY_R*2:.0f}×{BODY_R*2*math.sqrt(2):.0f}мм")
    print(f"  Вторичка 50×{SECONDARY_MAJOR:.1f}мм — садится с запасом ~4мм по краям")
    print()
    print("  Сборка коллимации:")
    print("    1. Положить M5 hex гайку в hex карман на верхней грани слэба")
    print("       (доступ изнутри тела сверху, через срез — пинцетом).")
    print("    2. Вкрутить 3 M3×16 коллимационных винта сверху держателя")
    print("       (винты сами нарезают резьбу в PETG).")
    print("    3. M5×40 болт снизу через hub паука, через пружинку,")
    print("       через слэб, в M5 гайку — стянуть.")
    print("    4. Зеркало приклеить силиконом (3 точки) к эллипсу 45°.")
    print("    5. Коллимация: 3 M3 винта = наклон, 1 M5 = высота/натяжение.")


if __name__ == "__main__":
    main()
