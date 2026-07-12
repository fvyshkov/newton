#!/usr/bin/env python3
"""Собирает готовые столы (3MF) под Bambu H2D (350×320) из отдельных STL.
Детали расставлены по печатной зоне, низом на z=0 → открыть в Bambu Studio → слайс.

ГЛАВНОЕ: седло печатается «НА БОКУ» (rotate X90+Y180, H=160) — так весь лес
(поддержка) сидит ниже z=70 в блоке хомута (бор Ø22 + уши роликов), башен к
верхней арке нет. «Лёжа» давало 11.6k мм² леса, «на боку» — 5.6k и весь у дна.
Футпринт седла на боку 257×98 → оба седла + вся мелочь помещаются на ОДИН стол.

→ print_queue/verkhniy_yarus/STOL_ALL.3mf   (всё одним столом)
Разложить обратно на 2 стола — вызвать build_split() (см. низ файла).
"""
import math, numpy as np, trimesh
from pathlib import Path
D = Path("print_queue/verkhniy_yarus")

def load(name): return trimesh.load(D / name, process=False)
def eul(ax, ay, az):
    return trimesh.transformations.euler_matrix(math.radians(ax), math.radians(ay), math.radians(az))

ON_SIDE = eul(90, 180, 0)     # седло на боку: H=160, лес весь у дна
LAY_ARM = eul(0, -90, 0)      # 130-мм энкодер-arm кладём горизонтально
ROT_Z90 = eul(0, 0, 90)       # разворот на столе (не меняет опору, только футпринт)

def place(fname, x0, y0, pre=None):
    """Ориентировать (pre), опустить низом на z=0, левый-нижний угол bbox → (x0,y0)."""
    m = load(fname)
    if pre is not None:
        m.apply_transform(pre)
    b = m.bounds
    m.apply_translation([x0 - b[0, 0], y0 - b[0, 1], -b[0, 2]])
    return m

def make_plate(items, out, bedx=350, bedy=320):
    scene = trimesh.Scene()
    boxes = []   # (name, x0,y0,x1,y1) для проверки пересечений
    for name, fname, x0, y0, pre in items:
        m = place(fname, x0, y0, pre)
        scene.add_geometry(m, node_name=name, geom_name=name)
        b = m.bounds
        boxes.append((name, b[0, 0], b[0, 1], b[1, 0], b[1, 1]))
    # --- проверки: границы стола + попарные пересечения по XY (зазор проектный) ---
    errs = []
    for name, ax0, ay0, ax1, ay1 in boxes:
        if ax0 < 0 or ay0 < 0 or ax1 > bedx or ay1 > bedy:
            errs.append(f"{name}: вне стола ({ax0:.0f},{ay0:.0f})-({ax1:.0f},{ay1:.0f})")
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            n1, a0, b0, a1, b1 = boxes[i]; n2, c0, d0, c1, d1 = boxes[j]
            ox = min(a1, c1) - max(a0, c0); oy = min(b1, d1) - max(b0, d0)
            if ox > 0 and oy > 0:
                errs.append(f"ПЕРЕСЕЧЕНИЕ {n1}∩{n2}: {ox:.0f}×{oy:.0f} мм")
    scene.export(D / out)
    tot = sum(abs(g.volume) for g in scene.geometry.values()) / 1000
    bb = (scene.bounds[1] - scene.bounds[0]).round(0)
    print(f"  {out}: {len(scene.geometry)} дет., ~{tot:.0f} см³  bbox={bb}  H={bb[2]:.0f}")
    for e in errs:
        print("   ⚠", e)
    return len(errs) == 0


# ============================ ОДИН СТОЛ: ВСЁ ============================
# Раскладка на 350×320: 2 седла на боку (257×98) стопкой слева-снизу; справа
# колонка из 2 вышек (развёрнуты Z90 → 77 шир.) + 2 ролика + магнит; сверху
# полоса энкодер-arm + привод. Зазоры ≥5 мм, поля от края ≥3 мм.
def build_all():
    ok = make_plate([
        ("cradle_R",   "03_Rocker_cradle_R_x1.stl",         6,   6, ON_SIDE),   # 257×98  x6..263 y6..104
        ("cradle_L",   "04_Rocker_cradle_L_x1.stl",         6, 112, ON_SIDE),   # 257×98  x6..263 y112..210
        ("apex_R",     "01_Rocker_tower_apex_R_x1.stl",    269,   6, ROT_Z90),  # 77×84   x269..346 y6..90
        ("apex_L",     "02_Rocker_tower_apex_L_x1.stl",    269,  96, ROT_Z90),  # 77×84   x269..346 y96..180
        ("roller_1",   "06_Rocker_alt_roller_x2.stl",      269, 186, None),     # 35×35   x269..304 y186..221
        ("roller_2",   "06_Rocker_alt_roller_x2.stl",      309, 186, None),     # 35×35   x309..344 y186..221
        ("magnet_cap", "08_magnet_cap_altitude_x1.stl",    269, 227, None),     # 18×18
        ("encoder_arm","07_Rocker_alt_encoder_arm_x1.stl",   6, 218, LAY_ARM),  # 130×28  x6..136 y218..246
        ("alt_drive",  "05_Rocker_alt_drive_x1.stl",         6, 252, None),     # 93×46   x6..99  y252..298
    ], "STOL_ALL.3mf")
    print("  →", "OK" if ok else "ЕСТЬ КОНФЛИКТЫ (см. ⚠ выше)")


# ============================ FALLBACK: 2 СТОЛА ============================
# По седлу на стол (изоляция брака) + мелочь рядом. Тоже седло на боку.
def build_split():
    make_plate([
        ("cradle_R",   "03_Rocker_cradle_R_x1.stl",         6,   6, ON_SIDE),
        ("apex_R",     "01_Rocker_tower_apex_R_x1.stl",     6, 112, None),
        ("alt_drive",  "05_Rocker_alt_drive_x1.stl",      100, 112, None),
        ("magnet_cap", "08_magnet_cap_altitude_x1.stl",   205, 112, None),
        ("roller_1",   "06_Rocker_alt_roller_x2.stl",     240, 112, None),
    ], "STOL_1.3mf")
    make_plate([
        ("cradle_L",   "04_Rocker_cradle_L_x1.stl",         6,   6, ON_SIDE),
        ("apex_L",     "02_Rocker_tower_apex_L_x1.stl",      6, 112, None),
        ("encoder_arm","07_Rocker_alt_encoder_arm_x1.stl", 100, 112, LAY_ARM),
        ("roller_2",   "06_Rocker_alt_roller_x2.stl",      245, 112, None),
    ], "STOL_2.3mf")


if __name__ == "__main__":
    print("Собираю ОДИН стол (седла на боку, всё на 350×320)…")
    build_all()
    print("Готово: STOL_ALL.3mf")
