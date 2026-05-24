#!/usr/bin/env python3
"""
Spider_4vane.stl — паук с 4 лопастями для UTA ID 240мм.

Лопасти на углах 45°/135°/225°/315° (между фокусером в 0° и крепежами
truss-стоек на 90°/180° относительно секции UTA). Это даёт классический
4-spike diffraction pattern на 45° к горизонту.

Архитектура:
  * Центральный hub — плоский диск Ø24мм, толщина 6мм, со сквозным M5
    отверстием посередине под коллимационный болт держателя вторички.
    На нижней стороне hub — hex карман на M5 hex гайку (для болта).
  * 4 лопасти 3мм × 20мм × 98мм радиально от hub к UTA.
  * 4 утолщённых пятки (tip) на наружных концах — 10×20×16мм (radial ×
    tang × vertical). В каждой пятке: сквозное M5 отверстие (ось радиальная)
    + hex карман на M5 hex гайку на внутренней грани (со стороны центра).
    Через это отверстие болт M5×20 идёт от наружной стенки UTA внутрь
    и стягивает пятку к UTA.

Печать:
  * Плашмя на стол (Z = толщина 3мм, плоскость лопастей).
  * Сопло 0.4мм · слой 0.2мм · 5-6 периметров · 25% gyroid · PETG-HF.
  * brim 5мм для лопастей (3мм узкие, склонны к отрыву).
  * Поддержки НЕ нужны (всё лежит плашмя).
  * ~4ч на H2D.
"""
import math
from pathlib import Path

import trimesh

# === Hub (центральная часть) ===
HUB_R = 12.0
HUB_T = 6.0
HUB_M5_HOLE_R = 2.75    # Ø5.5 clearance под M5 коллимационный болт
HUB_NUT_AF = 8.0        # M5 hex AF
HUB_NUT_DEPTH = 5.0     # глубина hex кармана

# === Лопасти ===
VANE_THICK = 3.0        # толщина лопасти (по вертикали при печати плашмя)
VANE_WIDTH = 20.0       # тангенциальная ширина лопасти
VANE_LEN = 98.0         # длина лопасти от hub до tip
# (tip inner face at r=110, hub edge at r=12, length = 110-12 = 98)

# === Пятки на наружных концах ===
TIP_RADIAL = 10.0       # радиальная толщина пятки (от r=110 до r=120)
TIP_WIDTH = 20.0        # тангенциальная ширина пятки
TIP_HEIGHT = 16.0       # вертикальная высота (Z) пятки
TIP_M5_HOLE_R = 2.75    # Ø5.5 clearance под M5
TIP_NUT_AF = 8.0
TIP_NUT_DEPTH = 5.0

# === Углы лопастей ===
VANE_ANGLES = [45.0, 135.0, 225.0, 315.0]

UTA_ID = 240.0          # для справки

SEG = 96
OUT_DIR = Path(__file__).parent
OUT_FILE = OUT_DIR / "Spider_4vane.stl"


def main():
    # Печатаем плашмя, плоскость лопастей = XY, толщина 3мм по Z.

    # 1) Hub в центре
    hub = trimesh.creation.cylinder(radius=HUB_R, height=HUB_T, sections=SEG)
    hub.apply_translation([0, 0, HUB_T / 2.0])
    body = hub

    # Центральное M5 отверстие в hub
    hub_hole = trimesh.creation.cylinder(
        radius=HUB_M5_HOLE_R, height=HUB_T * 4, sections=32
    )
    hub_hole.apply_translation([0, 0, HUB_T / 2.0])
    body = body.difference(hub_hole)

    # Hex карман на НИЖНЕЙ грани hub под M5 гайку коллимационного болта
    hex_pocket = trimesh.creation.cylinder(
        radius=HUB_NUT_AF / math.cos(math.radians(30)) / 2.0,
        height=HUB_NUT_DEPTH,
        sections=6,
    )
    # центр кармана: на нижней грани (z=0), уходит вверх на NUT_DEPTH
    hex_pocket.apply_translation([0, 0, HUB_NUT_DEPTH / 2.0])
    body = body.difference(hex_pocket)

    # 2) Лопасти + пятки на каждом угле
    for ang_deg in VANE_ANGLES:
        # --- Лопасть ---
        vane = trimesh.creation.box(
            extents=(VANE_LEN, VANE_WIDTH, VANE_THICK)
        )
        # Сдвинуть так чтобы внутренний конец у hub_R, внешний у hub_R + VANE_LEN
        vane.apply_translation([HUB_R + VANE_LEN / 2.0, 0, VANE_THICK / 2.0])

        # Поворот на угол лопасти
        rot = trimesh.transformations.rotation_matrix(
            math.radians(ang_deg), [0, 0, 1]
        )
        vane.apply_transform(rot)
        body = body.union(vane)

        # --- Пятка (tip) ---
        tip = trimesh.creation.box(
            extents=(TIP_RADIAL, TIP_WIDTH, TIP_HEIGHT)
        )
        # Сдвинуть так чтобы внутренний край пятки на r = HUB_R + VANE_LEN = 110
        # внешний край — на r = 120 (UTA_ID/2)
        tip.apply_translation(
            [HUB_R + VANE_LEN + TIP_RADIAL / 2.0, 0, TIP_HEIGHT / 2.0]
        )
        tip.apply_transform(rot)
        body = body.union(tip)

        # M5 сквозное отверстие в пятке (ось радиальная)
        tip_hole = trimesh.creation.cylinder(
            radius=TIP_M5_HOLE_R, height=TIP_RADIAL * 3, sections=32
        )
        rot_y90 = trimesh.transformations.rotation_matrix(
            math.radians(90), [0, 1, 0]
        )
        tip_hole.apply_transform(rot_y90)
        tip_hole.apply_translation(
            [HUB_R + VANE_LEN + TIP_RADIAL / 2.0, 0, TIP_HEIGHT / 2.0]
        )
        tip_hole.apply_transform(rot)
        body = body.difference(tip_hole)

        # Hex карман на ВНУТРЕННЕЙ грани пятки под M5 гайку
        # (карман открывается со стороны hub, бортом 5мм)
        tip_nut = trimesh.creation.cylinder(
            radius=TIP_NUT_AF / math.cos(math.radians(30)) / 2.0,
            height=TIP_NUT_DEPTH,
            sections=6,
        )
        tip_nut.apply_transform(rot_y90)
        # карман на радиальной позиции — у внутренней грани пятки
        tip_nut.apply_translation([
            HUB_R + VANE_LEN + TIP_NUT_DEPTH / 2.0,
            0,
            TIP_HEIGHT / 2.0,
        ])
        tip_nut.apply_transform(rot)
        body = body.difference(tip_nut)

    body.export(OUT_FILE)
    e = body.extents
    print(f"  -> {OUT_FILE.name}  {len(body.faces)} faces, "
          f"{e[0]:.1f}x{e[1]:.1f}x{e[2]:.1f}mm")
    print()
    print(f"  Hub: Ø{HUB_R*2:.0f}мм, толщина {HUB_T:.0f}мм")
    print(f"  4 лопасти {VANE_THICK:.0f}×{VANE_WIDTH:.0f}мм, длина {VANE_LEN:.0f}мм")
    print(f"  Пятки: tip {TIP_RADIAL:.0f}×{TIP_WIDTH:.0f}×{TIP_HEIGHT:.0f}мм")
    print(f"  Размер по диагонали: {(HUB_R + VANE_LEN + TIP_RADIAL)*2:.0f}мм")
    print(f"  В UTA: пятки на r=120 (= UTA ID/2 = {UTA_ID/2:.0f}мм) ✓")
    print()
    print("  Сборка:")
    print("    1. Вставить 4 M5 гайки в hex карманы пяток (по 1).")
    print("    2. Вставить 1 M5 гайку в hex карман hub (для коллимац. болта).")
    print("    3. Опустить паука в UTA сверху, совместить пятки с M5 отверстиями")
    print("       в стенках цилиндра (углы 45°/135°/225°/315°).")
    print("    4. M5×20 болты СНАРУЖИ UTA сквозь стенку в пятки, затянуть.")


if __name__ == "__main__":
    main()
