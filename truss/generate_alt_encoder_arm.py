#!/usr/bin/env python3
"""
Rocker_alt_encoder_arm — кронштейн энкодера ВЫСОТНОЙ оси (AS5048A on-axis).
ПЕРВАЯ деталь проекта на build123d (OpenCASCADE B-rep): watertight по построению,
экспорт STEP (точная геометрия, Bambu Studio открывает нативно) + STL для печати.

Запуск:  ./.venv-cad/bin/python truss/generate_alt_encoder_arm.py

Задача. Магнит энкодера вклеен в ЦЕНТР внешней грани колеса Ø200 (мир x=177.5),
лицо магнита ~x=184.4 на оси качания (y=0, z=590). Чип AS5048A должен стоять
НЕПОДВИЖНО на оси, лицом к магниту, зазор ~1–2 мм. Диск колеса (x∈[162.5,177.5],
R100) пробить нельзя → кронштейн идёт СНАРУЖИ диска и растёт из R-вышки:
нога садится на площадку apex (мир z=474, 2×M4, см. generate_rocker_towers
enc_pad=True), стойка поднимается снаружи диска (x≥179, зазор к грани 177.5),
наверху — карман платы на оси. Слоты ноги дают ±3 мм по X — установка зазора.

Мировые константы (источник — gen_rocker_comic; стабильны):
  WHEEL_X=170, APEX_Z=460, ALT_AXIS_Z=590; колесо Ø200×15 (диск x[162.5,177.5]).
Плата AS5048A (проверено, ams-клон): 28×22, чип=ось в ЦЕНТРЕ прямоуг. отв. 18×11.
"""
from pathlib import Path
from build123d import (Box, Cylinder, Pos, Rot, Align, export_step, export_stl)

OUT = Path(__file__).parent / "stl"

# --- мир ---
WHEEL_X, APEX_Z, AXIS_Z = 170.0, 460.0, 590.0
DISC_FACE_X = WHEEL_X + 7.5          # 177.5 внешняя грань диска — за неё нельзя внутрь
MAG_FACE_X = DISC_FACE_X + 6.9       # 184.4 лицо магнита (колпачок native ~6.9)
PAD_TOP_Z = 474.0                    # верх площадки apex (enc_pad)
PAD_CX = WHEEL_X + 11.0              # 181 центр площадки по X
BOLT_DY = 10.0                       # разнос 2×M4 площадки

# --- плата/чип ---
GAP = 1.6                            # воздушный зазор чип↔магнит (слоты дают ±3)
CHIP_X = MAG_FACE_X + GAP            # 186.0 плоскость чипа (−X сторона платы)
BOSS_H = 3.0                         # плата стоит на бобышках чип-стороной к −X
PLATE_T = 3.0
PLATE_IN_X = CHIP_X + BOSS_H         # 189 внутренняя грань плиты
HOLE_DX, HOLE_DY = 18.0, 11.0        # отв. платы: 18 по Z, 11 по Y
BOARD_L, BOARD_W = 28.0, 22.0        # плата (длина по Z, ширина по Y)
SELFTAP = 2.2                        # Ø самонарез M2.5 в бобышку
CHIP_WIN = 9.0                       # окно под чип по центру плиты

# --- стойка/нога ---
SPINE_X0, SPINE_X1 = 179.0, 191.0    # X-створ стойки (179 ≥ грань диска 177.5 +1.5)
SPINE_YHALF = 12.0                   # полуширина стойки по Y (жёсткость на боковой крен)
FOOT_Z0, FOOT_Z1 = PAD_TOP_Z, PAD_TOP_Z + 8.0   # нога 474..482 на площадке
M4_CLR = 4.5
SLOT_TRAVEL = 3.0                    # ±3 мм регулировка зазора (слот вдоль X)


def bx(x0, x1, y0, y1, z0, z1):
    """Осепараллельный бокс по мин/макс углам (мировые координаты)."""
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def cyl_x(x_ctr, y, z, r, length):
    """Цилиндр с осью вдоль X (для боров/окна/самонарезов), центр на x_ctr."""
    return Pos(x_ctr, y, z) * Rot(0, 90, 0) * Cylinder(r, length)


def build():
    # Диск Ø200 = тело x[162.5,177.5], R100 вокруг оси (y,z−590): всё инбордное
    # (x<177.5) должно быть НИЖЕ обода (z<490), а всё что выше — снаружи (x≥179).
    # Магнит-колпачок Ø18 торчит до x≈184.5 у оси → шейка к плате идёт по x≥185.5.

    # 1) НОГА на площадке apex (мир x[174,188], z[474,482]) — целиком ниже обода
    foot = bx(PAD_CX - 7, PAD_CX + 7, -14, 14, FOOT_Z0, FOOT_Z1)

    # 2) СТОЙКА строго СНАРУЖИ диска (x≥179), от ноги до-под магнита (z≤576).
    #    Низ z=481 перекрывается с ногой (x179..188) → сварка без отдельной рампы.
    spine = bx(SPINE_X0, SPINE_X1, -SPINE_YHALF, SPINE_YHALF, FOOT_Z1 - 1, AXIS_Z - 14)
    # ГУССЕТ снаружи (+X грань) — треугольная жёсткость на «завал» по X к магниту
    gusset = bx(SPINE_X1 - 2, SPINE_X1 + 5, -SPINE_YHALF, SPINE_YHALF, FOOT_Z1, AXIS_Z - 45)
    # ШЕЙКА снаружи магнита (x≥185.5) — обходит колпачок Ø18 и держит плиту
    neck = bx(185.5, SPINE_X1, -10, 10, AXIS_Z - 16, AXIS_Z)

    # 3) ПЛИТА платы (нормаль X) на оси: мир x[189,192], y±11, z 590±14
    plate = bx(PLATE_IN_X, PLATE_IN_X + PLATE_T, -BOARD_W / 2, BOARD_W / 2,
               AXIS_Z - BOARD_L / 2, AXIS_Z + BOARD_L / 2)
    # 4) 4 бобышки под плату (протыкают −X до x=CHIP_X=186), плата стоит чип-стороной к магниту
    part = foot + spine + gusset + neck + plate
    for sz in (+1, -1):
        for sy in (+1, -1):
            zc, yc = AXIS_Z + sz * HOLE_DX / 2, sy * HOLE_DY / 2
            part += cyl_x(CHIP_X + BOSS_H / 2, yc, zc, 3.0, BOSS_H)

    # === ВЫРЕЗЫ ===
    cuts = []
    # окно под чип по центру плиты (сквозь плиту, на оси)
    cuts.append(cyl_x(PLATE_IN_X - 1, 0, AXIS_Z, CHIP_WIN / 2, PLATE_T + 4))
    # самонарезы платы сквозь бобышки+плиту
    for sz in (+1, -1):
        for sy in (+1, -1):
            cuts.append(cyl_x(CHIP_X, sy * HOLE_DY / 2, AXIS_Z + sz * HOLE_DX / 2,
                              SELFTAP / 2, BOSS_H + PLATE_T + 2))
    # 2 СЛОТА ноги под M4 (регулировка зазора ±3 вдоль X): прорезь вдоль X сквозь ногу
    for sy in (+1, -1):
        cuts.append(bx(PAD_CX - SLOT_TRAVEL - M4_CLR / 2, PAD_CX + SLOT_TRAVEL + M4_CLR / 2,
                       sy * BOLT_DY - M4_CLR / 2, sy * BOLT_DY + M4_CLR / 2,
                       FOOT_Z0 - 1, FOOT_Z1 + 1))
        # карман головки M4 сверху ноги (Ø8, глубина 3)
        cuts.append(bx(PAD_CX - SLOT_TRAVEL - 4, PAD_CX + SLOT_TRAVEL + 4,
                       sy * BOLT_DY - 4, sy * BOLT_DY + 4, FOOT_Z1 - 3, FOOT_Z1 + 1))

    for c in cuts:
        part -= c
    return part


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    part = build()
    print(f"build123d B-rep: is_valid={part.is_valid}  объём={part.volume/1000:.2f} cm³  "
          f"граней={len(part.faces())}")
    step = OUT / "Rocker_alt_encoder_arm.step"
    stl = OUT / "Rocker_alt_encoder_arm.stl"
    export_step(part, str(step))
    export_stl(part, str(stl))

    import trimesh
    m = trimesh.load(stl)
    print(f"STL из B-rep: watertight={m.is_watertight}  vol={m.volume/1000:.2f} cm³  "
          f"triangles={len(m.faces)}  bbox(мир)={m.bounds[1]-m.bounds[0]}")
    print(f"→ {step.name} + {stl.name}")


if __name__ == "__main__":
    main()
