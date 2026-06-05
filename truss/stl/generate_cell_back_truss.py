#!/usr/bin/env python3
"""
Задняя плита оправы С ИНТЕГРИРОВАННЫМИ НОЖКАМИ для truss-варианта 8" Newton.
(Mirror_cell_back_truss.stl)

Одна печатная деталь = задняя плита push-pull оправы + 3 ножки, которыми
она сразу притягивается к дну существующей mirror box. Заменяет связку
"старая Mirror_cell_back + 3 отдельных кронштейна + горизонтальные болты".

  * Геометрия плиты — как в generate_mirror_cell.make_back():
    Ø250, 6 отверстий коллимации (3 push r=70 @ 0/120/240,
    3 pull r=89 @ 60/180/300), центральный вент Ø30, 3 фестона.
    Радиальные отверстия в ушах НЕ нужны (ножки встроены).
  * 3 ножки на углах 30/150/270 спускаются от плиты к дну коробки.
    Каждая садится на существующую бобышку дна (Ø24×4мм) своим
    углублением (самоцентрирование) и притягивается болтом M5 СНИЗУ
    (из-под дна, сквозь Ø9 + шайба) в гайку M5 в боковом пазу ножки.

Регулировка зеркала — штатными push-pull барашками между этой плитой и
передней плитой (Mirror_cell_front.stl, без изменений). Фокус — фокусёром.

Привязка к существующей коробке (generate_mirror_box.py):
  SHAFT_R=132, углы 30/150/270, отверстие Ø9.2, бобышка Ø24 высотой 4мм.

Печать: плитой на стол, ножки вверх? Нет — ножками вниз, плита сверху,
поддержки под нависание плиты над ножками не нужны (ножки шире снизу).
Либо печатать плитой на стол и ножки вверх — тогда пазы гаек печатаются
мостами. Рекомендую: ножками ВНИЗ на стол, 5 периметров, 30% gyroid,
PETG-HF/ASA.
"""
import math
from pathlib import Path

import trimesh

# --- Плита (из generate_mirror_cell.py) ---
TUBE_R = 125.0
PLATE_T = 8.0
PUSH_R = 70.0
PULL_R = 89.0
PUSH_ANGLES = [0, 120, 240]
PULL_ANGLES = [60, 180, 300]
BOLT_HOLE_R = 3.0          # Ø6 clearance под M5 (коллимация)
VENT_R = 15.0
SCALLOP_ANGLES = [90, 210, 330]
SCALLOP_D = 195.0
SCALLOP_R = 110.0

# --- Ножки ---
LEG_ANGLES = [30, 150, 270]
PLATE_BOTTOM_Z = 20.0      # низ плиты над верхом дна коробки
                           # (зазор под push-pull гайки)
PLATE_TOP_Z = PLATE_BOTTOM_Z + PLATE_T
LEG_RADIAL = 34.0          # радиальный размер ножки
LEG_CENTER_R = 127.0       # центр ножки по радиусу (r 110..144)
LEG_TANG = 28.0            # тангенциальная ширина ножки

# --- Привязка к дну коробки ---
SHAFT_R = 132.0            # где отверстие/бобышка в дне
BOSS_RECESS_R = 12.3       # Ø24.6 углубление под бобышку Ø24
BOSS_RECESS_H = 4.5        # глубина (бобышка 4мм)

# --- Крепёж ножки к дну ---
M5_CLR_R = 2.75            # Ø5.5
NUT_AF = 8.0
NUT_CIRC_R = NUT_AF / math.cos(math.radians(30)) / 2.0
NUT_TH = 4.6
FLOOR_NUT_Z = 8.0          # высота центра гайки над низом ножки

SEG = 96
SEG_DISK = 256

OUT_DIR = Path(__file__).parent
OUT_FILE = OUT_DIR / "Mirror_cell_back_truss.stl"


def xy(angle_deg, r):
    a = math.radians(angle_deg)
    return r * math.cos(a), r * math.sin(a)


def tall_cyl(radius, sections=64):
    return trimesh.creation.cylinder(radius=radius, height=PLATE_T * 6, sections=sections)


def main():
    rot_z = lambda a: trimesh.transformations.rotation_matrix(math.radians(a), [0, 0, 1])

    # --- Плита ---
    body = trimesh.creation.cylinder(radius=TUBE_R, height=PLATE_T, sections=SEG_DISK)
    body.apply_translation([0, 0, (PLATE_BOTTOM_Z + PLATE_TOP_Z) / 2.0])

    # фестоны
    for ang in SCALLOP_ANGLES:
        x, y = xy(ang, SCALLOP_D)
        sc = trimesh.creation.cylinder(radius=SCALLOP_R, height=PLATE_T * 6, sections=SEG)
        sc.apply_translation([x, y, (PLATE_BOTTOM_Z + PLATE_TOP_Z) / 2.0])
        body = body.difference(sc)

    # вент + коллимация (вертикальные сквозные)
    drills = [(0, 0, VENT_R)]
    for ang in PUSH_ANGLES:
        x, y = xy(ang, PUSH_R); drills.append((x, y, BOLT_HOLE_R))
    for ang in PULL_ANGLES:
        x, y = xy(ang, PULL_R); drills.append((x, y, BOLT_HOLE_R))
    for x, y, r in drills:
        h = tall_cyl(r)
        h.apply_translation([x, y, (PLATE_BOTTOM_Z + PLATE_TOP_Z) / 2.0])
        body = body.difference(h)

    # --- Ножки ---
    for ang in LEG_ANGLES:
        leg = trimesh.creation.box(extents=(LEG_RADIAL, LEG_TANG, PLATE_TOP_Z))
        leg.apply_translation([LEG_CENTER_R, 0, PLATE_TOP_Z / 2.0])
        leg.apply_transform(rot_z(ang))
        body = body.union(leg)

    # --- Отверстия/карманы в ножках ---
    for ang in LEG_ANGLES:
        # вертикальное Ø5.5 (только основание, не дотягиваясь до плиты)
        m5v_top = FLOOR_NUT_Z + NUT_TH / 2.0 + 5.0
        m5v = trimesh.creation.cylinder(radius=M5_CLR_R, height=m5v_top + 8, sections=64)
        m5v.apply_translation([SHAFT_R, 0, (m5v_top - 8) / 2.0])
        m5v.apply_transform(rot_z(ang))
        body = body.difference(m5v)

        # шестигранный карман гайки
        hexp = trimesh.creation.cylinder(radius=NUT_CIRC_R, height=NUT_TH, sections=6)
        hexp.apply_translation([SHAFT_R, 0, FLOOR_NUT_Z])
        hexp.apply_transform(rot_z(ang))
        body = body.difference(hexp)

        # боковой сквозной паз под гайку (тангенциальный)
        slot = trimesh.creation.box(extents=(NUT_AF, LEG_TANG + 4, NUT_TH))
        slot.apply_translation([SHAFT_R, 0, FLOOR_NUT_Z])
        slot.apply_transform(rot_z(ang))
        body = body.difference(slot)

        # углубление под бобышку дна (самоцентрирование), снизу
        boss = trimesh.creation.cylinder(radius=BOSS_RECESS_R, height=BOSS_RECESS_H + 1, sections=SEG)
        boss.apply_translation([SHAFT_R, 0, (BOSS_RECESS_H - 1) / 2.0])
        boss.apply_transform(rot_z(ang))
        body = body.difference(boss)

    body.export(OUT_FILE)
    e = body.extents
    maxr = max(math.hypot(*xy(a, LEG_CENTER_R + LEG_RADIAL / 2)) for a in LEG_ANGLES)
    print(f"  -> {OUT_FILE.name}  {len(body.faces)} faces, "
          f"{e[0]:.1f}x{e[1]:.1f}x{e[2]:.1f}mm")
    print(f"  watertight: {body.is_watertight}")
    print(f"  макс. радиус ножки ≈ {LEG_CENTER_R + LEG_RADIAL/2:.0f}мм "
          f"(стенка коробки внутри r=145)")
    print(f"  низ плиты над дном: {PLATE_BOTTOM_Z:.0f}мм")
    print()
    print("Сборка:")
    print("  1. В боковой паз каждой ножки задвинуть гайку M5 (+ клей).")
    print("  2. Деталь поставить в коробку: ножки сядут углублениями на")
    print("     3 бобышки дна (самоцентрируется).")
    print("  3. Снизу 3 болта M5×20 + шайба сквозь дно → в гайки ножек.")
    print("  4. Сверху штатная push-pull сборка с Mirror_cell_front.stl —")
    print("     ею же коллимация и осевая подстройка зеркала.")


if __name__ == "__main__":
    main()
