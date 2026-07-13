#!/usr/bin/env python3
"""БАШМАКИ ног башен — замена сломанных наклонных гнёзд на венце (az2).

Гнёзда ног печатались заодно с сегментами венца наклонными (15.6°/35.6°) и без
точечных поддержек не напечатались (сорвались, пустоты). Перепечатывать сегменты
не нужно: зубья/стыки/карманы целы. Вместо этого — отдельные БАШМАКИ: тот же
наклонный хомут Ø30/бор Ø22.6, но на плоском фланце-подошве, прикручивается
шурупами к верху венца на месте зачищенного «шрама» ноги.

Геометрия ноги 1:1 из generate_az2 (_leg_dir_local, R_LEG=201, те же апексы
±170,0,460) → верх (башни/седло) встаёт без изменений; посадка трубы стартует
на 8 мм выше (толщина фланца) → апексы равномерно +8 мм, ноги короче на ~8-10 мм
(резать по месту).

ПЕЧАТЬ: фланцем вниз, БЕЗ поддержек (наклон хомута ≤36° < 45°), PETG,
4 стенки, инфилл ≥40% (это силовые детали — не 15%!).

УСТАНОВКА (см. README print_queue/azimuth2):
  1. Остатки сломанных гнёзд срезать/зачистить ЗАПОДЛИЦО с верхом венца.
  2. Башмак прижать наружным краем фланца к зубчатому ободу (упор по радиусу),
     хомут по центру шрама старой ноги (упор по углу).
  3. Сквозь отверстия фланца предсверлить Ø2.5, шурупы 3.5×12 (НЕ длиннее:
     снизу скользящая грань и тефлон-карманы!).
Позиции шурупов разведены от тефлон-карманов (R201, азимуты (k+0.5)·15°):
ряды R211.5 и R190.5 радиально вне карманов (R193.5..208.5).

+ az2_magnet_spider3 — спайдер с ТРЕМЯ лучами (120/210/300): бобышка спайдера
сегмента A (R196, азимут 30°) лежит ВНУТРИ пятна ноги 30° (ось хомута в 4-5 мм) —
4-й луч на 30° прикрутить нельзя ни с родной ногой, ни с башмаком. Трёх хватает.
"""
import math
from pathlib import Path

import numpy as np
import trimesh

import generate_az2 as A

# ============================ ПАРАМЕТРЫ ============================
FL_Z0 = A.ROT_Z1              # 17 — верх венца (мир az2)
FL_T = 8.0                    # толщина фланца
FL_Z1 = FL_Z0 + FL_T          # 25 — верх фланца = старт посадки трубы
FL_R_IN = 188.0               # фланец: внутренний радиус (тело венца от R185.5)
FL_R_OUT = 217.1              # наружный: упор в стенку обода зубьев (R217.5, зазор 0.4)
SKIRT = ((19.0, 5.0), (17.0, 4.0))   # юбка-усиление корня: (радиус, высота) от верха фланца

SCREW_D = 3.7                 # сквозной под шуруп 3.5
SCREW_HEAD_D = 8.0            # цековка под головку
SCREW_HEAD_T = 3.5            # глубина цековки
R_OUTB = 211.5                # ряд шурупов СНАРУЖИ тефлон-карманов (<208.5)
R_INB = 190.5                 # ряд ВНУТРИ карманов (>193.5)

GRIP = A.LEG_H                # 44 — глубина посадки трубы (как у венца)
PAD_R, PAD_N = A.PAD_R, A.PAD_N          # тефлон-карманы: R201, 24 шт
PAD_HALF = A.PAD_D / 2.0                 # Ø15/2

# (имя, C сегмента, [(bx,by,side)], полуширина фланца °, [шурупы (R, азимут°)])
SHOES = [
    ("az2_shoe_A30", 0.0, [(A.R_LEG * A._c30, A.R_LEG * A._s30, "R")], 7.5,
     [(R_OUTB, 24.0), (R_OUTB, 36.0), (R_INB, 36.0)]),      # хомут валит к −азимуту → внутр. шуруп на +стороне
    ("az2_shoe_C150", 180.0, [(A.R_LEG * A._c30, -A.R_LEG * A._s30, "L")], 7.5,
     [(R_OUTB, 156.0), (R_OUTB, 144.0), (R_INB, 144.0)]),   # зеркало A
    ("az2_shoe_D270", 270.0, [(A.R_LEG, 12.0, "R"), (A.R_LEG, -12.0, "L")], 10.5,
     [(R_OUTB, a) for a in (262.0, 266.0, 270.0, 274.0, 278.0)]),  # оба хомута валят внутрь → все шурупы снаружи
]


def world_leg(C, bx, by, side):
    """(база XY в мире, единичное направление ноги в мире) — 1:1 из венца."""
    dl = A._leg_dir_local(C, (bx, by), side)
    Rz = A._rotz3(C)
    bw = Rz @ np.array([bx, by, 0.0])
    return bw[:2], Rz @ dl


def check_screw_vs_pads(holes):
    """Шуруп не должен попасть в тефлон-карман в дне венца."""
    for (r, az) in holes:
        hx, hy = r * math.cos(math.radians(az)), r * math.sin(math.radians(az))
        for k in range(PAD_N):
            pa = math.radians((k + 0.5) * (360.0 / PAD_N))
            d = math.hypot(hx - PAD_R * math.cos(pa), hy - PAD_R * math.sin(pa))
            assert d > PAD_HALF + SCREW_D / 2 + 0.8, \
                f"шуруп ({r},{az}°) лезет в тефлон-карман #{k} (дист {d:.1f})"


def shoe(name, C, legs, half_ang, holes):
    mean_az = {0.0: 30.0, 180.0: 150.0, 270.0: 270.0}[C]
    check_screw_vs_pads(holes)

    # --- фланец: сектор-кольцо, наружный край под стенку обода зубьев ---
    part = A.extrude(A.sector_annulus(FL_R_IN, FL_R_OUT,
                                      mean_az - half_ang, mean_az + half_ang),
                     FL_T, z0=FL_Z0)
    clip_sect = A.extrude(A.sector_annulus(FL_R_IN + 0.5, FL_R_OUT - 1.0,
                                           mean_az - half_ang + 0.4,
                                           mean_az + half_ang - 0.4),
                          40.0, z0=FL_Z1)          # юбки не свисают с фланца

    cuts = []
    for (bx, by, side) in legs:
        bw, d = world_leg(C, bx, by, side)
        base = np.array([bw[0], bw[1], FL_Z0])
        p0 = base + d * (FL_T / d[2])              # ось на верхе фланца = старт бора
        col_len = FL_T / d[2] + GRIP + 1.0
        # хомут (заглублён на 2 вниз, потом срез плоскостью z=17)
        part = part.union(A.cyl_along(A.LEG_COLLAR_D / 2, col_len + 2, base - d * 2, d))
        # юбка-усиление корня (ступеньками над фланцем), обрезана по сектору фланца
        sk = []
        z = FL_Z1
        for (r, h) in SKIRT:
            sk.append(A.cyl(r, h, T=A.tr(bw[0], bw[1], z + h / 2)))
            z += h
        part = part.union(trimesh.boolean.union(sk).intersection(clip_sect))
        # бор: от верха фланца ВВЕРХ (фланец/подошва целы), открыт сверху
        cuts.append(A.cyl_along(A.LEG_BORE / 2, GRIP + 20, p0, d, seg=48))
        # радиальный M4-стопор трубы (как у венца: LEG_H−8 от начала посадки)
        h = np.array([d[0], d[1], 0.0]); h /= np.linalg.norm(h)
        ss = p0 + d * (GRIP - 8)
        cuts.append(A.cyl_along(A.LEG_SET / 2, A.LEG_COLLAR_D + 8,
                                ss - h * (A.LEG_COLLAR_D / 2 + 4), h, seg=24))

    # --- шурупы: сквозной Ø3.7 + цековка Ø8×3.5 сверху ---
    for (r, az) in holes:
        hx, hy = r * math.cos(math.radians(az)), r * math.sin(math.radians(az))
        cuts.append(A.cyl(SCREW_D / 2, FL_T + 2, seg=24, T=A.tr(hx, hy, FL_Z0 + FL_T / 2)))
        cuts.append(A.cyl(SCREW_HEAD_D / 2, SCREW_HEAD_T + 20, seg=24,
                          T=A.tr(hx, hy, FL_Z1 - SCREW_HEAD_T / 2 + 10)))
    part = part.difference(cuts)
    part = part.intersection(A.box(1000, 1000, 200, T=A.tr(0, 0, 117)))  # низ = z17

    # ---- проверки (в мировой позе) ----
    pts, _ = trimesh.sample.sample_surface(part, 60000)
    pts = np.vstack([pts, part.vertices])
    rr = np.hypot(pts[:, 0], pts[:, 1])
    assert rr.max() < 218.0, f"{name}: R {rr.max():.1f} — лезет к мотору (218.85)"
    low = rr[pts[:, 2] < A.ROT_RIM_Z1 + 0.4]
    assert low.max() < 217.25, f"{name}: {low.max():.2f} — лезет в стенку обода зубьев (R217.5)"
    assert abs(part.bounds[0][2] - FL_Z0) < 0.01, f"{name}: низ не плоский z17"
    for (bx, by, side) in legs:      # труба Ø22 входит на полный грип в ПУСТОЙ бор
        bw, d = world_leg(C, bx, by, side)
        p0 = np.array([bw[0], bw[1], FL_Z0]) + d * (FL_T / d[2])
        tube = A.cyl_along(A.TUBE_D / 2 if hasattr(A, "TUBE_D") else 11.0, GRIP, p0, d, seg=48)
        it = trimesh.boolean.intersection([part, tube])
        frac = (abs(it.volume) if len(it.vertices) else 0.0) / (math.pi * 121 * GRIP) * 100
        print(f"    tube-fit {name} ({side}): {frac:.1f}% {'PASS' if frac < 5 else 'FAIL'}")
        assert frac < 5.0

    # ---- поза печати: фланец на стол, XY в ноль ----
    b = part.bounds
    part.apply_translation([-(b[0][0] + b[1][0]) / 2, -(b[0][1] + b[1][1]) / 2, -FL_Z0])
    return A.finish(part, name)


# ============================ СПАЙДЕР 3 ЛУЧА ============================
def magnet_spider3():
    """Как az2_magnet_spider, но лучи на 120/210/300 (сборочные азимуты бобышек).
    Луч на 30° убран: бобышка сегмента A накрыта ногой 30° (родной или башмаком).
    Ставится БЕЗ вращения: уши точно на бобышки 120/210/300 (вариант «30/120/210»
    не встанет — луч упрётся в хомут ноги)."""
    arm_z0 = A.ROT_Z1
    arm_t, arm_w = 3.0, 10.0
    hub_d, hub_h = 20.0, 5.0
    r_out = A.SPD_MOUNT_R
    solids = [A.cyl(hub_d / 2, hub_h, T=A.tr(0, 0, arm_z0 + hub_h / 2))]
    for ang in (120, 210, 300):
        arm = A.box(r_out - hub_d / 2, arm_w, arm_t)
        arm.apply_translation([(hub_d / 2 + r_out) / 2, 0, arm_z0 + arm_t / 2])
        arm.apply_transform(A.rotz(ang))
        solids.append(arm)
        ear = A.cyl(arm_w / 2, arm_t, T=A.tr(r_out, 0, arm_z0 + arm_t / 2))
        ear.apply_transform(A.rotz(ang))
        solids.append(ear)
    part = trimesh.boolean.union(solids)

    cuts = []
    mag_pocket_bot = A.MAG_FACE_Z - A.MAG_RECESS
    cuts.append(A.cyl((A.MAGNET_D + A.MAG_FIT) / 2, (A.MAGNET_H + A.MAG_RECESS) + 0.5,
                      seg=48, T=A.tr(0, 0, mag_pocket_bot + (A.MAGNET_H + A.MAG_RECESS) / 2)))
    for ang in (120, 210, 300):
        a = math.radians(ang)
        cuts.append(A.cyl(3.4 / 2, arm_t + 2, seg=24,
                          T=A.tr(r_out * math.cos(a), r_out * math.sin(a),
                                 arm_z0 + arm_t / 2)))
    part = part.difference(cuts)
    part.apply_translation([0, 0, -part.bounds[0][2]])
    return A.finish(part, "az2_magnet_spider3")


def main():
    print("Башмаки ног (замена сломанных гнёзд венца) + спайдер 3 луча…")
    for name, C, legs, half_ang, holes in SHOES:
        shoe(name, C, legs, half_ang, holes)
    magnet_spider3()
    print("\nПечать: фланцем вниз, БЕЗ поддержек, PETG, 4 стенки, инфилл ≥40%.")
    print("Крепёж: шурупы 3.5×12 (предсверлить Ø2.5), НЕ длиннее 12!")


if __name__ == "__main__":
    main()
