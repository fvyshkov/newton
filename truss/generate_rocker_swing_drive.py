#!/usr/bin/env python3
"""
Качающийся (подпружиненный) азимутальный привод рокера — «боевой» узел
вместо стенда, ремень GT2 3:1 (20T→60T) + шестерня 16T в венец 224T.

Генерит 2 бинарных STL в truss/stl/ через CSG (trimesh + manifold3d):

  1. Rocker_swing_arm.stl — качающаяся каретка: плита 8мм с осью-бобышкой,
     корпусом вала (2×608ZZ + полость под шкив 60T) и площадкой NEMA17.
     ЭКСПОРТИРОВАНА ВВЕРХ НОГАМИ (верх плиты = стол): посадки подшипников,
     полость шкива и пазы мотора печатаются начисто, БЕЗ поддержек.
  2. Rocker_swing_base.stl — основание на вращающемся фанерном диске:
     стойка оси Ø16 с конической юбкой-косынкой, упор глубины зацепления,
     проушина пружины, 6 потайных саморезов. Печать плашмя, без поддержек.

Локальная система: ось шестерни вертикальна в начале координат, центр
венца в (−240, 0), точка зацепления P = (−16, 0), касательная в P — ось Y.
Ось качания (−16, +65) ЛЕЖИТ НА КАСАТЕЛЬНОЙ через P ⇒ момент силы
зацепления вокруг оси качания ≈ 0 в обе стороны вращения.

Z-СТЕК (мир стенда, z=0 = верх нижней фанеры):
   4..12   ступица шестерни (Rocker_pinion_16T СТУПИЦЕЙ ВНИЗ — ступицей
           вверх она (24..32) упёрлась бы в нижний 608 (28..35))
  12..24   зубья шестерни (венец: зубья 12..22 — перекрытие 10мм)
  25..37   вращающийся фанерный диск (в кромке — вырез R≥33 под корпус)
  27.7     низ трубы корпуса (Ø30) — над зубьями венца (22) везде
  28..35   нижний 608ZZ (посадка Ø22.15 глубиной 7.3 снизу, буртик 35..36)
  36..36.6 жертвенный мостовой пояс (паз 21мм — 2-слойный мост, см. ниже)
  37..43   плита основания (на диске)
  37..49   шкив 60T в полости Ø47 (открыта на +X под выход ремня);
           шкив зажат между буртиками ⇒ осевой замок всего вала
  43..56   стойка оси Ø16 (пилот M5 Ø4.2), юбка-косынка 45° до z=47.5
  50..57   верхний 608ZZ (посадка сверху 50..57.3, заходная Ø22.6 до 66)
  58..66   плита рычага (бобышка оси 56..58 — рычаг трётся ТОЛЬКО о стойку)
  66       фланец NEMA17 (мотор СВЕРХУ, вал вниз до z=42; шкив 20T ставится
           ступицей ВВЕРХ — зубчатый низ нависает ниже конца вала, это норм)

Жертвенный мост: «потолок» полости над нижней посадкой нельзя снять
фаской 45° — фланец шкива Ø44 стоит в 1мм над буртиком Ø20.15. Классика:
слой 0.6мм с прямоугольным пазом 21мм — периметры мостятся хордами,
следующий слой замыкает круг. Печатается без поддержек.

Сборка: основание — 6 саморезов к диску (ДО установки рычага!); нижний
608 запрессовать снизу до буртика, верхний — сверху; шкив 60T вставить
боком через окно +X; вал Ø8×~52 сверху сквозь всё, снизу — шестерня
ступицей вниз; рычаг на стойку, M5×25 с шайбой сверху (не затягивать —
рычаг должен качаться); пружина между проушинами (тянет шестерню к
венцу, −X); винт M3×20 в упорную лапку — регулировка глубины зацепления.
"""
import math
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import LineString, Point, Polygon
from shapely.geometry import box as shbox
from shapely.ops import unary_union

# ============================ ПАРАМЕТРЫ ============================
# --- Мир стенда (z=0 = верх нижней фанеры) ---
PITCH_X = -16.0         # точка зацепления P=(−16,0); центр венца (−240,0)
TEETH_Z1 = 22.0         # верх зубчатого пояса венца (12..22)
DISC_Z1 = 37.0          # верх вращающегося фанерного диска (низ 25)

# --- Ремень GT2 3:1 ---
MOTOR_X = 58.6          # межосевое 20T/60T под ремень 2GT-200, мм
CAV_R = 47.0 / 2        # полость под шкив 60T (фланцы ~Ø44), радиус
PULLEY_Z0, PULLEY_Z1 = 37.0, 49.0   # шкив 60T на валу

# --- Подшипники 608ZZ (22×8×7) ---
SEAT_D = 22.15          # прессовая посадка (проверено на этом принтере)
SEAT_DEPTH = 7.3        # глубина посадки от входного торца
LIP_BORE = SEAT_D - 2.0     # буртик 1мм на сторону → Ø20.15
LEADIN_D = 22.6         # заходная над верхней посадкой (сквозь плиту)

# --- Z-стек корпуса вала (см. докстринг) ---
TUBE_Z0 = 27.7          # низ трубы (= 35.0 − SEAT_DEPTH)
SEAT_LO_Z1 = 35.0       # верх нижней посадки (подшипник 28..35)
LIP_LO_Z1 = 36.0        # верх нижнего буртика
BAND_Z1 = 36.6          # верх жертвенного мостового пояса
CAV_Z1 = 49.0           # верх полости шкива
LIP_HI_Z1 = 50.0        # верх верхнего буртика (подшипник 50..57)
SEAT_HI_Z1 = 57.3       # верх верхней посадки, дальше заходная до 66
PLATE_Z0, PLATE_Z1 = 58.0, 66.0     # плита рычага
TUBE_R = 15.0           # труба нижней посадки, наружный радиус
HOUS_R = 28.0           # корпус вокруг полости, наружный радиус
SLOT_W = 21.0           # ширина паза жертвенного моста (по X, > Ø20.15)
OPEN_X0 = 16.0          # окно выхода ремня: x 16..33, y ±22.5, z 36..49

# --- Ось качания ---
PIVOT = (-16.0, 65.0)   # на касательной x=PITCH_X через P
POST_Z0, POST_Z1 = 43.0, 56.0       # стойка Ø16 на плите основания
BOSS_Z0 = 56.0          # бобышка рычага 56..58: трётся только о стойку
M5_CLR = 5.4            # сквозной M5 в бобышке
M5_PILOT = 4.2          # пилот M5-самонарезайки в стойке

# --- NEMA17 (мотор сверху плиты, фланец на z=66, вал вниз) ---
NEMA_PITCH = 31.0 / 2   # крепёж M3 на квадрате 31×31
SLOT_TRAVEL = 4.0       # пазы натяжения ±4 по X
M3_HOLE = 3.4           # M3 сквозной
PILOT_HOLE = 23.0       # окно под пилотный буртик Ø22×2 (тоже паз ±4)

# --- Упор глубины зацепления ---
TAB_X0, TAB_X1 = -42.0, -34.0       # лапка на рычаге (висит под плитой)
TAB_Y0, TAB_Y1 = 5.0, 15.0
TAB_Z0 = 48.0
STOP_PILOT = 2.7        # пилот M3-самонарезайки, горизонтально вдоль X
STOP_Z = 53.0           # ось упорного винта
WALL_X0, WALL_X1 = -55.0, -49.0     # упорная стенка основания (лицо −49)
WALL_Y0, WALL_Y1 = 4.0, 16.0
WALL_Z1 = 63.0          # стенка 43..63 (~10×20 по спеке)

# --- Пружина (тянет шестерню к венцу, −X) ---
HOOK_Y = -13.0          # обе проушины на y=−13, отверстия Ø4 вдоль Y
HOOK_Z = 52.0           # ось пружины
ARM_HOOK_X = -32.0      # проушина рычага (лапка 3мм у корпуса, −X)
BASE_HOOK_X = -69.0     # проушина основания

# --- Основание ---
BASE_T = 6.0            # плита 37..43 на диске
BASE_X0, BASE_X1 = -115.0, 35.0     # ~150×95
BASE_Y0, BASE_Y1 = -15.0, 80.0
NOTCH_R = 33.0          # вырез под корпус (качается: Ø56 + ход ±3)
SCREW_D, SCREW_CSK = 4.4, 9.0       # потайной саморез 3.5×16
SCREW_XY = ((-105, -5), (-105, 40), (-105, 72),
            (-45, 72), (-45, 35), (-40, -8))   # все ≤ R215 от центра диска

SEG_CIRC = 96           # фасеты полных окружностей
OUTDIR = Path(__file__).parent / "stl"


# ============================ ХЕЛПЕРЫ ============================
def extrude(poly2d, h, z0=0.0):
    m = trimesh.creation.extrude_polygon(poly2d, height=h)
    if z0:
        m.apply_translation([0, 0, z0])
    return m


def tr(x, y, z):
    M = np.eye(4)
    M[:3, 3] = (x, y, z)
    return M


def cyl(r, h, seg=SEG_CIRC, T=None):
    c = trimesh.creation.cylinder(radius=r, height=h, sections=seg)
    if T is not None:
        c.apply_transform(T)
    return c


def czyl(r, z0, z1, x=0.0, y=0.0, seg=SEG_CIRC):
    """Вертикальный цилиндр от z0 до z1 с осью в (x, y)."""
    return cyl(r, z1 - z0, seg=seg, T=tr(x, y, (z0 + z1) / 2))


def cbox(x0, x1, y0, y1, z0, z1):
    """Бокс по двум углам."""
    b = trimesh.creation.box(extents=(x1 - x0, y1 - y0, z1 - z0))
    b.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    return b


def xcyl(r, x0, x1, y, z, seg=32):
    """Горизонтальный цилиндр вдоль X (пилоты упора)."""
    c = cyl(r, x1 - x0, seg=seg)
    c.apply_transform(trimesh.transformations.rotation_matrix(
        math.pi / 2, [0, 1, 0]))
    c.apply_translation([(x0 + x1) / 2, y, z])
    return c


def ycyl(r, y0, y1, x, z, seg=32):
    """Горизонтальный цилиндр вдоль Y (отверстия пружины)."""
    c = cyl(r, y1 - y0, seg=seg)
    c.apply_transform(trimesh.transformations.rotation_matrix(
        math.pi / 2, [1, 0, 0]))
    c.apply_translation([x, (y0 + y1) / 2, z])
    return c


def prism_xz(pts_xz, y0, y1):
    """Призма-косынка: треугольник в плоскости XZ, вытянутый по Y."""
    m = trimesh.creation.extrude_polygon(Polygon(pts_xz), height=y1 - y0)
    m.apply_transform(trimesh.transformations.rotation_matrix(
        math.pi / 2, [1, 0, 0]))
    m.apply_translation([0, y1, 0])
    return m


def csk_cutter(x, y, z_top, d_shaft=SCREW_D, d_head=SCREW_CSK):
    """Резак потайного самореза — ОДНО тело вращения «стержень + конус 90°»
    (коаксиальные цилиндр+конус по отдельности дают sliver-грани —
    опыт generate_rocker_azdrive.py)."""
    rs, rc = d_shaft / 2, d_head / 2
    profile = np.array([[0.0, -20.0], [rs, -20.0], [rs, -(rc - rs)],
                        [rc + 1.0, 1.0], [0.0, 1.0]])
    c = trimesh.creation.revolve(profile, sections=48)
    c.apply_translation([x, y, z_top])
    return c


def capsule2d(x0, x1, y, r):
    """2D-стадион (паз натяжения): отрезок, раздутый на r."""
    return LineString([(x0, y), (x1, y)]).buffer(r, resolution=24)


def finish(mesh, name):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    mesh.process(validate=True)
    out = OUTDIR / f"{name}.stl"
    mesh.export(out)
    bb = mesh.bounds
    print(f"  {name}.stl  watertight={mesh.is_watertight}  vol={mesh.volume/1000:.2f}cm³  "
          f"bbox={bb[1,0]-bb[0,0]:.0f}×{bb[1,1]-bb[0,1]:.0f}×{bb[1,2]-bb[0,2]:.0f}mm")
    return mesh


# ============================ 1. РЫЧАГ ============================
def rocker_swing_arm():
    """Качающаяся каретка. Плита 8мм (z=58..66) = выпуклая оболочка вокруг
    оси качания, корпуса вала и площадки мотора; корпус висит под плитой.
    Печать ВВЕРХ НОГАМИ (уже так экспортировано): всё растёт от плиты
    вертикально, посадки/полость — глухие расточки вверх, единственный
    навес (потолок полости над нижней посадкой) закрыт жертвенным мостом."""
    # --- Плита: convex hull опорных пятен (жёстко и без острых углов)
    hull = unary_union([
        Point(PIVOT).buffer(13),                 # зона оси качания
        Point(0, 0).buffer(HOUS_R),              # корпус вала
        shbox(MOTOR_X - 27, -26, MOTOR_X + 27, 26),   # площадка NEMA17
        Point(-40, 10).buffer(6),                # корень упорной лапки
        Point(ARM_HOOK_X, HOOK_Y).buffer(6),     # корень проушины пружины
    ]).convex_hull
    plate = extrude(hull, PLATE_Z1 - PLATE_Z0, z0=PLATE_Z0)

    # --- Тело: корпус Ø56 (36..66), труба Ø30 (27.7..37), бобышка оси,
    #     упорная лапка и проушина пружины (перекрытия 0.5-1мм → чистый union)
    housing = czyl(HOUS_R, LIP_LO_Z1, PLATE_Z1)
    tube = czyl(TUBE_R, TUBE_Z0, LIP_LO_Z1 + 1.0)
    boss = czyl(8.0, BOSS_Z0, PLATE_Z0 + 0.5, x=PIVOT[0], y=PIVOT[1])
    stop_tab = cbox(TAB_X0, TAB_X1, TAB_Y0, TAB_Y1, TAB_Z0, PLATE_Z0 + 1.0)
    hook_tab = cbox(ARM_HOOK_X - 4, ARM_HOOK_X + 4, HOOK_Y - 1.5, HOOK_Y + 1.5,
                    TAB_Z0, PLATE_Z0 + 1.0)      # проушина 3мм шириной
    part = plate.union(housing).union(tube).union(boss)
    part = part.union(stop_tab).union(hook_tab)

    # --- Расточки вала (все соосны, вертикальны)
    cuts = [
        czyl(LIP_BORE / 2, TUBE_Z0 - 2, PLATE_Z1 + 1),      # буртики Ø20.15
        czyl(SEAT_D / 2, TUBE_Z0 - 2, SEAT_LO_Z1),          # нижняя посадка
        czyl(SEAT_D / 2, LIP_HI_Z1, PLATE_Z1 + 1),          # верхняя посадка
        czyl(LEADIN_D / 2, SEAT_HI_Z1, PLATE_Z1 + 1),       # заходная
        czyl(CAV_R, BAND_Z1, CAV_Z1),                       # полость шкива Ø47
        # Жертвенный мостовой пояс 0.6мм: паз 21мм вдоль Y — «потолок»
        # полости печатается 2-слойным мостом вместо невозможной фаски 45°
        # (фланец шкива Ø44 стоит в 1мм над буртиком Ø20.15).
        cbox(-SLOT_W / 2, SLOT_W / 2, -24, 24, LIP_LO_Z1, BAND_Z1 + 0.02),
        # Окно выхода ремня на +X (через него же заводится шкив 60T боком)
        cbox(OPEN_X0, HOUS_R + 5, -22.5, 22.5, LIP_LO_Z1, CAV_Z1),
        # Ось качания: M5 сквозь бобышку и плиту
        czyl(M5_CLR / 2, BOSS_Z0 - 1, PLATE_Z1 + 1, x=PIVOT[0], y=PIVOT[1],
             seg=32),
        # Пилот упорного винта M3 — горизонтально вдоль X, сквозь лапку
        xcyl(STOP_PILOT / 2, TAB_X0 - 2, TAB_X1 + 2, 10.0, STOP_Z, seg=24),
        # Отверстие пружины Ø4 вдоль Y сквозь проушину
        ycyl(2.0, HOOK_Y - 5, HOOK_Y + 5, ARM_HOOK_X, HOOK_Z, seg=24),
    ]
    # Крепёж NEMA17: центральный паз под буртик Ø22×2 + 4 паза M3, все ±4 по X
    cuts.append(extrude(capsule2d(MOTOR_X - SLOT_TRAVEL, MOTOR_X + SLOT_TRAVEL,
                                  0.0, PILOT_HOLE / 2), 10, z0=PLATE_Z0 - 1))
    for sx in (-NEMA_PITCH, NEMA_PITCH):
        for sy in (-NEMA_PITCH, NEMA_PITCH):
            cuts.append(extrude(
                capsule2d(MOTOR_X + sx - SLOT_TRAVEL, MOTOR_X + sx + SLOT_TRAVEL,
                          sy, M3_HOLE / 2), 10, z0=PLATE_Z0 - 1))
    part = part.difference(cuts)

    # --- Перевернуть под печать: верх плиты (z=66) на стол
    part.apply_transform(trimesh.transformations.rotation_matrix(
        math.pi, [1, 0, 0]))
    part.apply_translation([0, 0, PLATE_Z1])
    return finish(part, "Rocker_swing_arm")


# ============================ 2. ОСНОВАНИЕ ============================
def rocker_swing_base():
    """Основание на вращающемся диске (плита 37..43, печать плашмя).
    Стойка Ø16 (43..56) с конической юбкой 45° — рычаг сидит бобышкой на
    её торце и качается на M5. Упорная стенка (лицо x=−49) — в неё смотрит
    регулировочный винт лапки рычага. Проушина пружины соосна с рычажной
    (y=−13, z=52). Вырез R33 + канал на +X — корпус вала и ремень проходят
    сквозь уровень плиты (диск в этом месте выпилен пользователем)."""
    outline = shbox(BASE_X0, BASE_Y0, BASE_X1, BASE_Y1).difference(unary_union([
        Point(0, 0).buffer(NOTCH_R),                      # под корпус вала
        shbox(0, -NOTCH_R, BASE_X1 + 1, NOTCH_R),         # канал ремня на +X
    ]))
    plate = extrude(outline, BASE_T, z0=DISC_Z1)

    # ВАЖНО (урок этой детали): у сливаемых тел НЕ ДОЛЖНО БЫТЬ общих
    # плоскостей с перекрытием (дно стойки = дно юбки и т.п.) — иначе
    # булев union оставляет sliver-грани и после process(validate=True)
    # деталь дырявая. Поэтому все «заглубления» в плиту РАЗНЫЕ (0.5..1.0),
    # а косынки на 0.1мм уже своих тел.

    # Стойка оси с юбкой-косынкой — ОДНО тело вращения «конус + цилиндр»
    # (коаксиальные cone+cylinder с одинаковыми фасетами дают совпадающие
    # вершины на линии пересечения → sliver → не watertight; тот же урок,
    # что с зенковкой M4 в generate_rocker_azdrive.py). Юбка Ø26→Ø16,
    # наклон 45° от вертикали до z=48, дальше цилиндр Ø16 до 56.
    profile = np.array([[0.0, POST_Z0 - 0.5], [13.0, POST_Z0 - 0.5],
                        [8.0, POST_Z0 + 4.5], [8.0, POST_Z1], [0.0, POST_Z1]])
    post = trimesh.creation.revolve(profile, sections=SEG_CIRC)
    post.apply_translation([PIVOT[0], PIVOT[1], 0.0])

    # Упорная стенка + косынка 45° сзади (−X, внахлёст 1мм в стенку)
    wall = cbox(WALL_X0, WALL_X1, WALL_Y0, WALL_Y1, POST_Z0 - 0.8, WALL_Z1)
    wall_g = prism_xz([(-69, POST_Z0 - 0.5), (WALL_X0 + 1, POST_Z0 - 0.5),
                       (WALL_X0 + 1, 57.0)], 7.0, 13.0)

    # Проушина пружины (стойка 3мм с Ø4 вдоль Y) + косынки 45° по ±X
    hook = cbox(BASE_HOOK_X - 4, BASE_HOOK_X + 4, HOOK_Y - 1.5, HOOK_Y + 1.5,
                POST_Z0 - 0.8, 57.0)
    hook_g1 = prism_xz([(BASE_HOOK_X - 12, POST_Z0 - 0.5),
                        (BASE_HOOK_X - 3, POST_Z0 - 0.5),
                        (BASE_HOOK_X - 3, 51.0)], HOOK_Y - 1.4, HOOK_Y + 1.4)
    hook_g2 = prism_xz([(BASE_HOOK_X + 3, POST_Z0 - 0.5),
                        (BASE_HOOK_X + 12, POST_Z0 - 0.5),
                        (BASE_HOOK_X + 3, 51.0)], HOOK_Y - 1.4, HOOK_Y + 1.4)

    part = plate.union(post).union(wall).union(wall_g)
    part = part.union(hook).union(hook_g1).union(hook_g2)

    cuts = [
        # Пилот M5 по центру стойки (M5×25: 15мм зацепления)
        czyl(M5_PILOT / 2, POST_Z1 - 16, POST_Z1 + 1, x=PIVOT[0], y=PIVOT[1],
             seg=32),
        # Отверстие пружины Ø4 вдоль Y
        ycyl(2.0, HOOK_Y - 5, HOOK_Y + 5, BASE_HOOK_X, HOOK_Z, seg=24),
    ]
    # 6 потайных саморезов к диску (все в радиусе ≤215 от центра диска)
    cuts += [csk_cutter(x, y, DISC_Z1 + BASE_T) for x, y in SCREW_XY]
    part = part.difference(cuts)

    part.apply_translation([0, 0, -DISC_Z1])   # низ плиты на стол
    return finish(part, "Rocker_swing_base")


def main():
    print("Генерация качающегося азимутального привода…")
    print(f"  ось качания {PIVOT} на касательной x={PITCH_X} через P=({PITCH_X},0)")
    print(f"  ремень: межосевое {MOTOR_X}мм (пазы ±{SLOT_TRAVEL}), "
          f"шкив 60T в полости Ø{2*CAV_R:.0f} z={PULLEY_Z0:.0f}..{PULLEY_Z1:.0f}")
    print(f"  608ZZ: нижний 28..35, верхний 50..57 (посадки Ø{SEAT_D}, "
          f"буртики Ø{LIP_BORE}); шкив между буртиками = осевой замок вала")
    rocker_swing_arm()
    rocker_swing_base()
    print(f"\nГотово → {OUTDIR}")
    print("Шестерня Rocker_pinion_16T ставится СТУПИЦЕЙ ВНИЗ (ступица 4..12).")
    print("Вал Ø8×~52; рычаг печатать как экспортирован (вверх ногами).")


if __name__ == "__main__":
    main()
