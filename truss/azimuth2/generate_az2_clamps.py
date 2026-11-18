#!/usr/bin/env python3
"""ПРИЖИМЫ венца (az2) — 3 Z-скобы, не дают вращающемуся кольцу приподниматься.

Профиль «три плоскости» (вид в радиальном разрезе, центр азимута слева):

              ЯЗЫК ───────┐
       ← R219..234        │ СТЕНКА (R228..234)
   зазор 0.4 над ободом   │
   ~~~зубья/обод z19~~~   │
                          └──── ПОДОШВА (R228..260) → 2 шурупа в фанеру

Куда давит язык: верх ЗУБЧАТОГО ОБОДА (непрерывное кольцо R217.5..221.5 на
z=19) + вершины зубьев. Глубже внутрь нельзя: фланцы башмаков ног метут
z17..25 до R217.1 (весь башмак гарантированно R<218 — assert в generate_az2_shoes),
поэтому внутренний край языка R219. Стенка — снаружи вершин зубьев (R226): R228.

Номинальный зазор язык↔обод 0.4 мм: это ОГРАНИЧИТЕЛЬ, не тормоз — в норме не
трётся, при подъёме кольцо упирается через 0.4 мм. Если реальный стек выше
номинала (тефлон толще) и язык чиркает — подложить под подошву PET/бумагу;
если хочется нулевой зазор — полоска PET-скотча на низ языка.

УСТАНОВКА: 3 шт ~через 120°, НЕ БЛИЖЕ 25° к азимуту мотора (плита подставки
z24..30 доходит до R220, ноги R232..256 — конфликт и по языку, и по подошве).
Шурупы 3.5–4×25 в фанеру, предсверлить Ø2.5.

ПЕЧАТЬ: НА БОКУ (профиль на столе — слои вдоль Z-профиля, консоль языка не
рвётся по слоям), без поддержек, PETG, 4 стенки, инфилл ≥40%. 3 шт.
"""
import numpy as np
import trimesh

import generate_az2 as A

# ============================ ПАРАМЕТРЫ ============================
GAP = 0.4                        # зазор язык ↔ верх обода (z19) в номинале
FINGER_R_IN = 219.0              # язык внутрь: 1.0 запас от гарантии башмаков R<218
FINGER_T = 5.0
FINGER_Z0 = A.ROT_RIM_Z1 + GAP   # 19.4
FINGER_Z1 = FINGER_Z0 + FINGER_T # 24.4

WALL_R_IN = 228.0                # 2.0 запас от вершин зубьев R226
WALL_T = 6.0
WALL_R_OUT = WALL_R_IN + WALL_T  # 234

FOOT_T = 5.0
FOOT_R_OUT = 260.0
WIDTH = 28.0                     # по хорде (мостит вершины зубьев: шаг ~2.8/3.5)

SCREW_D = 4.2                    # шуруп 3.5–4 сквозной
SCREW_HEAD_D = 9.5               # цековка под головку
SCREW_HEAD_T = 2.5
SCREW_R = (241.0, 253.0)         # два шурупа по радиальной оси

CHAMF = 1.0                      # фаска нижних кромок языка (зубья не цепляют кромку)


def clamp_world():
    """Скоба в мировых координатах az2 (радиус вдоль +X, ширина по Y)."""
    finger = A.box(WALL_R_OUT - FINGER_R_IN, WIDTH, FINGER_T,
                   T=A.tr((FINGER_R_IN + WALL_R_OUT) / 2, 0, (FINGER_Z0 + FINGER_Z1) / 2))
    wall = A.box(WALL_T, WIDTH, FINGER_Z1,
                 T=A.tr((WALL_R_IN + WALL_R_OUT) / 2, 0, FINGER_Z1 / 2))
    foot = A.box(FOOT_R_OUT - WALL_R_IN, WIDTH, FOOT_T,
                 T=A.tr((WALL_R_IN + FOOT_R_OUT) / 2, 0, FOOT_T / 2))
    part = trimesh.boolean.union([finger, wall, foot])

    cuts = []
    # фаски 45° нижних кромок языка вдоль X (под ними проносятся вершины зубьев)
    for sy in (-1, 1):
        w = A.box(WALL_R_OUT - FINGER_R_IN + 2, CHAMF * 2 ** 0.5, CHAMF * 2 ** 0.5)
        w.apply_transform(trimesh.transformations.rotation_matrix(
            np.pi / 4, [1, 0, 0]))
        w.apply_translation([(FINGER_R_IN + WALL_R_OUT) / 2, sy * WIDTH / 2, FINGER_Z0])
        cuts.append(w)
    # шурупы: сквозной + цековка сверху
    for r in SCREW_R:
        cuts.append(A.cyl(SCREW_D / 2, FOOT_T + 2, seg=24, T=A.tr(r, 0, FOOT_T / 2)))
        cuts.append(A.cyl(SCREW_HEAD_D / 2, SCREW_HEAD_T + 20, seg=24,
                          T=A.tr(r, 0, FOOT_T - SCREW_HEAD_T / 2 + 10)))
    return part.difference(cuts)


def checks(part):
    """Зазоры к ВСЕМУ вращающемуся (консервативные огибающие) + «подъём блокируется»."""
    # 1. Всё до верха зубьев (z≤19): кольцо+зубья R≤226, неподвижное R≤218 —
    #    цилиндр R227.5 (запас 1.5) до z19.3 (запас 0.3 до языка 19.4).
    env1 = A.cyl(227.5, 19.3, T=A.tr(0, 0, 19.3 / 2))
    it = trimesh.boolean.intersection([part, env1])
    assert not len(it.vertices) or abs(it.volume) < 1e-6, \
        f"скоба лезет в зону кольца/зубьев: {abs(it.volume):.1f}мм³"
    # 2. Всё над кольцом (башмаки z17..25 гарантия R<218; хомуты/трубы/спайдер глубже) —
    #    цилиндр R218.5 от z17 вверх: язык (R≥219) не должен туда попадать.
    env2 = A.cyl(218.5, 60, T=A.tr(0, 0, 17 + 30))
    it = trimesh.boolean.intersection([part, env2])
    assert not len(it.vertices) or abs(it.volume) < 1e-6, \
        f"язык лезет в зону башмаков/стоек: {abs(it.volume):.1f}мм³"
    # 3. Подъём блокируется: обод+зубья (R217.5..226, верх z19), поднятые на GAP+0.2,
    #    должны УПЕРЕТЬСЯ в язык.
    z_mid = A.ROT_Z0 + GAP + 0.2 + A.RIM_H / 2
    rim = A.cyl(A.RING_TIP_R, A.RIM_H, T=A.tr(0, 0, z_mid)).difference(
        A.cyl(A.RIM_R_IN, A.RIM_H + 2, T=A.tr(0, 0, z_mid)))
    it = trimesh.boolean.intersection([part, rim])
    blocked = len(it.vertices) and abs(it.volume) > 1.0
    assert blocked, "поднятый на 0.6 обод НЕ упирается в язык — прижим не работает"
    print(f"    зазоры OK; подъём >{GAP + 0.2:.1f} мм блокируется "
          f"(перекрытие {abs(it.volume):.0f} мм³)")


def main():
    print("Прижимы венца az2 (Z-скоба, 3 шт)…")
    print(f"  язык: низ z{FINGER_Z0} (обод z{A.ROT_RIM_Z1:.0f} + зазор {GAP}), "
          f"R{FINGER_R_IN:.0f}..{WALL_R_OUT:.0f}; стенка R{WALL_R_IN:.0f}; "
          f"подошва до R{FOOT_R_OUT:.0f}")
    part = clamp_world()
    checks(part)
    # поза печати: НА БОКУ (профиль XZ на стол), низ в z0
    part.apply_transform(trimesh.transformations.rotation_matrix(
        np.pi / 2, [1, 0, 0], [0, 0, 0]))
    b = part.bounds
    part.apply_translation([-(b[0][0] + b[1][0]) / 2, -(b[0][1] + b[1][1]) / 2, -b[0][2]])
    A.finish(part, "az2_hold_clamp")
    print("\nПечать: на боку (как экспортировано), PETG, 4 стенки, ≥40%, БЕЗ поддержек, ×3.")
    print("Ставить: ~через 120°, не ближе 25° к мотору; шурупы 3.5–4×25, предсверлить 2.5.")


if __name__ == "__main__":
    main()
