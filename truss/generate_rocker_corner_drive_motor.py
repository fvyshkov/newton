"""
ЦЕЛЬНЫЙ приводной угол + мотор-каретка в ОДНОМ теле (печатать вместо
19_Rocker_corner_drive). Ремень 2GT-200 (CD 58.6).

Мотор НЕ по оси: на оси (0,−181.4) корпус Ø42 упирается в трубные воротники угла
(посчитано: пересечение ~11 см³). Уводим мотор ВБОК по дуге CD 58.6 в позицию
(55,−220) — там чисто (0 пересечения). Ремень идёт по диагонали от шестерни.

Каретка (в мировых координатах, до позы печати):
  • корпус Ø30 под 2×608ZZ на оси шестерни (0,−240);
  • балка-вынос от корпуса к фланцу мотора вбок (55,−220);
  • фланец NEMA17 (31×31 M3 + окно Ø23) с ПРОРЕЗЯМИ вдоль ремня → натяг/зазор ставишь
    сдвигом мотора и затягиваешь;
  • проём Ø40 отключён — шестерня/шкивы висят ниже корпуса в открытом пространстве.

Z: шестерня 50..62 · шкивы+ремень ~62..74 · 608 78..85 и 88..95 · фланец 83..90 ·
мотор вверх. Шестерню/шкивы/подшипники/вал/ремень ставим при сборке (см. README).
"""
import math
from pathlib import Path
import trimesh
import generate_rocker_frame_truss as ft

OUT = Path(__file__).parent / "print_queue" / "motor_kron" / "Rocker_corner_drive_motor.stl"

PINION_XY = (0.0, -240.0)
MOTOR_XY = (55.1, -220.0)                 # вбок по дуге CD 58.6 (ремень 200) — чисто
BELT_ANG = math.degrees(math.atan2(MOTOR_XY[1] - PINION_XY[1],
                                   MOTOR_XY[0] - PINION_XY[0]))   # ось прорезей = линия ремня
SLOT_TRAVEL = 3.5                         # ±ход прорезей вдоль ремня, мм
BOSS_D, BRG_OD, SHAFT_RELIEF = 30.0, 22.15, 16.0
PILOT_D, M3_CLR, NEMA_PITCH = 23.0, 3.4, 15.5


def _obox(L, W, H, cx, cy, cz, ang):
    """Бокс L×W×H, повёрнутый на ang° вокруг Z, в центре (cx,cy,cz)."""
    m = trimesh.creation.box(extents=[L, W, H])
    m.apply_transform(trimesh.transformations.rotation_matrix(math.radians(ang), [0, 0, 1]))
    m.apply_translation([cx, cy, cz])
    return m


def _slot(cx, cy, z0, z1, w, ang, travel=SLOT_TRAVEL):
    """Прорезь-паз шириной w, длиной 2·travel+w вдоль ang°."""
    return _obox(2 * travel + w, w, z1 - z0, cx, cy, (z0 + z1) / 2, ang)


def caddy_world():
    px, py = PINION_XY
    mx, my = MOTOR_XY
    solids = [
        ft.cyl(BOSS_D / 2, 19.0, T=ft.tr(px, py, 86.5)),                 # корпус 608 z77..96
        # БУТТРЕС: массив сваривает корпус ↔ пад ↔ ядро узла (кружок не висит на перемычке).
        # низ z75 — над шкивом 60T (верх z74); сквозная расточка вала его проходит.
        ft.box(34.0, 37.0, 14.0, T=ft.tr(0.0, -228.5, 85.0)),   # буттрес z78..92 (низ поднят с z75 — не задевает шкив 60T, верх z76)
        # балка-вынос к фланцу мотора — ШИРЕ прорези Ø23, чтобы прорезь не перерезала
        # стык. Высота 7 (z83..90) = вровень с верхом фланца, НЕ лезет в тело мотора (z90+).
        _obox(64.0, 40.0, 7.0, (px + mx) / 2, (py + my) / 2, 86.5, BELT_ANG),
        ft.cyl(30.0, 7.0, T=ft.tr(mx, my, 86.5)),                        # фланец Ø60 z83..90
    ]
    cuts = [
        # ГНЁЗДА 608 РАСКРЫТЫ ДО ТОРЦОВ корпуса — иначе поясок Ø16 на входе не пускал
        # подшипник Ø22 (баг). Оба садятся на СРЕДНИЙ бортик Ø16 (z85..88): нижний
        # входит СНИЗУ (гнездо открыто до z74), верхний СВЕРХУ (открыто до z96.5).
        ft.cyl(BRG_OD / 2, 11.0, seg=64, T=ft.tr(px, py, 79.5)),         # нижний 608: z74..85 (открыт вниз)
        ft.cyl(BRG_OD / 2, 8.5, seg=64, T=ft.tr(px, py, 92.25)),         # верхний 608: z88..96.5 (открыт вверх)
        ft.cyl(SHAFT_RELIEF / 2, 24.0, seg=48, T=ft.tr(px, py, 86.0)),   # расточка вала Ø16 z74..98
        ft.cyl(23.0, 16.0, seg=48, T=ft.tr(px, py, 69.0)),               # раскрытие под шкив 60T: Ø46 z61..77 (кромка ядра не лезет)
        _slot(mx, my, 79.0, 97.0, PILOT_D, BELT_ANG),                    # окно мотора СКВОЗЬ балку (доступ + вал)
    ]
    for sx in (-1, 1):                    # 4×M3 (31×31) ПРОРЕЗЯМИ вдоль ремня, СКВОЗЬ балку → доступ отвёрткой
        for sy in (-1, 1):
            cuts.append(_slot(mx + sx * NEMA_PITCH, my + sy * NEMA_PITCH,
                              79.0, 97.0, M3_CLR, BELT_ANG))
    return solids, cuts


if __name__ == "__main__":
    solids, cuts = caddy_world()
    mesh = ft.corner_node(270, drive=True, drive_window=False, drive_pad=False,
                          extra_solids=solids, extra_cuts=cuts,
                          name="Rocker_corner_drive_motor")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(OUT)
    print(f"[OK] BELT_ANG={BELT_ANG:.1f}°  → {OUT}")
