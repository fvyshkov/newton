#!/usr/bin/env python3
"""
Высотный (ALT) ярус рокера-добсона под колёса Ø200 — вышки, люльки, фрикционный
привод высоты. GoTo, Этап 2. Генерит бинарные STL в truss/stl/ через CSG
(trimesh + manifold3d), ПЕРЕИСПОЛЬЗУЯ проверенный хомут сына (tube_clamp).

Мировая система (мм, z=0 = верх нижней доски) берётся ИМПОРТОМ из
gen_rocker_comic (НЕ хардкодим): CORNER_ANGLES, R_CORNER, FRAME_Z, WHEEL_X,
APEX_Z, ALT_AXIS, polar(). Труба = Ø22 алюминий, хомут = split-collar сына
(бор Ø21.94, поперечный прижимной болт, призматический профиль вдоль бора).
Все сокеты труб — ЭТОТ ЖЕ хомут через tube_clamp.place_clamp()/clamp_mesh().

Детали:
  1. Rocker_tower_apex_R/L.stl (×1+×1) — узел вершины на (±170,0,APEX_Z=530).
     Сводит ДВЕ трубы-вышки от двух нижних углов + поперечную трубу (cross,
     вдоль X к другой вершине). Три хомута радиально от центрального шара-хаба;
     направления считаются ИЗ КООРДИНАТ. R и L — зеркальные (chiral): правый
     сводит углы 30° и 270°, левый — 150° и 270°; печатаются раздельно.
  2. Rocker_cradle_R/L.stl (×1+×1) — люлька высоты, СКОЛЬЗИТ по cross-трубе
     (хомут Ø22 → подвинул на нужный разнос колёс и затянул). Несёт ДВА ролика
     608ZZ (оси вдоль X), обод колеса (R100, ось X, центр z=590) ложится в V на
     ±35° от нижней точки: центры роликов на радиусе 111 от оси колеса →
     локально (y=±63.7, z=498.9). Палец-антиподъём (PTFE-накладка) над верхом
     обода z≈692 с зазором 1мм. Направляющие бортики не дают колесу «уйти» по X.
     Хомут смещён по оси трубы ВНУТРЬ (диск колеса тонкий, 15мм) — труба не
     задевает обод. R/L — зеркальные (хомут на внутренней стороне у каждой).
  3. Rocker_alt_drive.stl (×1) + Rocker_alt_roller.stl — фрикционный привод
     высоты на ОДНОЙ люльке: качающийся кронштейн (ось качания вертикальна,
     M5) держит NEMA17 + GT2 3:1 (20T→60T, CD 58.6) → вал Ø8 в 2×608 →
     фрикц. ролик Ø35 с проточкой под O-ring, прижатый пружиной к ободу снизу-
     по-центру (контакт x=170,y=0,z=490). Болтится к телу люльки (2×M4).

ОРИЕНТАЦИЯ ПЕЧАТИ (заявлено явно):
  • apex — печатать хомутом cross-трубы бором ВВЕРХ (этот бор = скользящая
    посадка, важнее всего кругл./без поддержки); две трубы-ноги уходят вниз
    под ~14° от вертикали → бор мостится/лёгкая поддержка; низ хаба сфаска 45°.
  • cradle и alt_drive — печатать осью cross-трубы ВЕРТИКАЛЬНО (локальная +Z =
    мировая X): ВСЕ боры (хомут + оси роликов + вал + пилот мотора) идут вдоль
    +Z → печатаются вертикальными отверстиями без поддержек. Консоль к колесу
    подпёрта 45° косынками; под пальцем/дальним вылетом — лёгкая поддержка.

Все посадки: M4 clr 4.4 / M4 гайка hex 7.0 глуб 3.2, M3 clr 3.4 / саморез 2.7,
M5 clr 5.4, M10 clr 10.6, 608ZZ прессовое гнездо Ø22.15 глуб 7.3 борт 1мм,
NEMA17 пилот Ø22.6 + M3 на 31×31, потай саморез Ø4.4.
"""
import math
from pathlib import Path

import numpy as np
import trimesh

import tube_clamp as tc
import gen_rocker_comic as W   # общий мир: константы + polar()

# ============================ ПАРАМЕТРЫ ============================
OUTDIR = Path(__file__).parent / "stl"
ENGINE = "manifold"

# --- Мир (импорт, не хардкод) ---
CORNER_ANGLES = W.CORNER_ANGLES      # (30,150,270)
R_CORNER = W.R_CORNER                # 210
FRAME_Z = W.FRAME_Z                  # 75  (ось нижних труб)
WHEEL_X = W.WHEEL_X                  # 170 (плоскости колёс x=±170)
APEX_Z = W.APEX_Z                    # 530 (вершина вышек / ось cross-трубы)
WHEEL_AXIS_Z = W.ALT_AXIS[2]         # 590 (ось качания колёс)
WHEEL_R = 100.0                      # радиус обода колеса, мм
WHEEL_W = 15.0                       # ширина обода (вдоль X), мм

# --- Хомут (замер сына) ---
CLAMP_OD = tc.CLAMP_OD               # 46.6 воротник ⟂ прорези
CLAMP_H = tc.CLAMP_H                 # 46

# --- Посадки ---
M3_CLR, M3_TAP = 3.4, 2.7
M4_CLR = 4.4
M4_NUT_AF, M4_NUT_D = 7.0, 3.2       # гайка M4 «под ключ» / глубина кармана
M5_CLR = 5.4
CSK_D = 4.4
BEAR_OD = 22.0                       # 608 наружный
BEAR_ID = 8.0                        # 608 внутренний
BEAR_W = 7.0                         # 608 ширина
BEAR_SEAT = 22.15                    # прессовое гнездо 608
BEAR_SEAT_H = 7.3
BEAR_LIP = 1.0                       # борт гнезда (диаметрально на сторону)
NEMA_PILOT = 22.6
NEMA_HOLE = 31.0                     # M3 на 31×31
SHAFT_D = 8.0

# --- Вышки / apex ---
HUB_R = 22.0                         # радиус шара-хаба вершины
CLAMP_OFF = 4.0                      # хомут стартует чуть наружу от вершины
APEX_CLAMP_H = 50.0                  # длина хомута вышки (грип ≈ 32мм за хабом)

# --- Ролики люльки ---
ROLL_Y = 63.7                        # ±y центров роликов (±35°, r=111)
ROLL_DZ = 91.1                       # опускание центра ролика под ось колеса
ROLL_Z_LOCAL = 0.0                   # локальная z роликов = плоскость обода
DISC_HALF = WHEEL_W / 2.0 + 1.5      # полузазор от диска колеса, ≈9.0

# --- Фрикц. привод высоты ---
FRIC_R = 17.5                        # фрикц. ролик Ø35
BELT_CD = 58.6                       # межосевое GT2 20T→60T
CONTACT_Z = 490.0                    # контакт с ободом (нижняя точка) z, мировое

ICO = 3                              # подразбиение сферы-хаба
SEG = 64

# ============================ ХЕЛПЕРЫ ============================
def tr(x, y, z):
    M = np.eye(4); M[:3, 3] = (x, y, z); return M


def cyl(r, h, T=None, seg=SEG):
    c = trimesh.creation.cylinder(radius=r, height=h, sections=seg)
    if T is not None:
        c.apply_transform(T)
    return c


def box(x, y, z, T=None):
    b = trimesh.creation.box(extents=(x, y, z))
    if T is not None:
        b.apply_transform(T)
    return b


def rotx(d): return trimesh.transformations.rotation_matrix(math.radians(d), [1, 0, 0])
def roty(d): return trimesh.transformations.rotation_matrix(math.radians(d), [0, 1, 0])
def rotz(d): return trimesh.transformations.rotation_matrix(math.radians(d), [0, 0, 1])


def uni(parts):
    return trimesh.boolean.union(parts, engine=ENGINE)


def dif(a, parts):
    return trimesh.boolean.difference([a] + list(parts), engine=ENGINE)


def mirror_x(mesh):
    m = mesh.copy()
    m.apply_transform(np.diag([-1.0, 1.0, 1.0, 1.0]))
    m.fix_normals()
    return m


def mirror_z(mesh):
    m = mesh.copy()
    m.apply_transform(np.diag([1.0, 1.0, -1.0, 1.0]))
    m.fix_normals()
    return m


def wedge_gusset(dx, dy, h, T):
    """Прямоугольная косынка-клин: прямой угол внизу, гипотенуза 45° сверху.
    Треугольная призма экструзией по Y (толщина dy)."""
    from shapely.geometry import Polygon
    poly = Polygon([(0, 0), (dx, 0), (0, h)])
    m = trimesh.creation.extrude_polygon(poly, height=dy)
    m.apply_transform(rotx(90))          # экструзия по +Y
    m.apply_translation([0, dy / 2.0, 0])
    m.apply_transform(T)
    return m


def finish(mesh, name):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    mesh.merge_vertices()
    mesh.process(validate=True)
    out = OUTDIR / f"{name}.stl"
    mesh.export(out)
    bb = mesh.bounds
    print(f"  {name}.stl  watertight={mesh.is_watertight}  vol={mesh.volume/1000:.2f}cm³  "
          f"bbox={bb[1,0]-bb[0,0]:.0f}×{bb[1,1]-bb[0,1]:.0f}×{bb[1,2]-bb[0,2]:.0f}mm")
    return mesh


# ============================ 1. APEX ВЕРШИНЫ ============================
def _apex_dirs(side):
    """Направления трёх труб от вершины (единичные). side=+1 правый, -1 левый."""
    apex = np.array([side * WHEEL_X, 0.0, APEX_Z])
    a_leg = 30.0 if side > 0 else 150.0          # передний угол этой стороны
    c_leg = np.array(W.polar(R_CORNER, a_leg, FRAME_Z))
    c_rear = np.array(W.polar(R_CORNER, 270.0, FRAME_Z))
    other = np.array([-side * WHEEL_X, 0.0, APEX_Z])
    dirs = {
        "leg": (c_leg - apex),
        "rear": (c_rear - apex),
        "cross": (other - apex),
    }
    lens = {k: float(np.linalg.norm(v)) for k, v in dirs.items()}
    dirs = {k: v / lens[k] for k, v in dirs.items()}
    return apex, dirs, lens


def rocker_tower_apex(side=+1, name="Rocker_tower_apex_R"):
    """Вершина: шар-хаб + 3 хомута сына по направлениям труб (из координат).
    Собирается в системе с вершиной в НАЧАЛЕ координат (apex→0)."""
    apex, dirs, _ = _apex_dirs(side)
    hub = trimesh.creation.icosphere(subdivisions=ICO, radius=HUB_R)

    parts = [hub]
    # slit_dir: мировой +Z (ортогонализуется в place_clamp) — болт доступен сбоку
    for key, d in dirs.items():
        origin = d * CLAMP_OFF               # старт хомута чуть наружу от вершины
        slit = np.array([0.0, 0.0, 1.0])
        if abs(np.dot(slit, d)) > 0.9:       # труба почти вертикальна → прорезь вбок
            slit = np.array([1.0, 0.0, 0.0])
        c = tc.place_clamp(APEX_CLAMP_H, origin, tube_dir=d, slit_dir=slit)
        parts.append(c)

    part = uni(parts)
    # R и L строятся из СВОИХ направлений (dirs(side)) в мировой ориентации,
    # центр — вершина в начале координат; L = зеркало R (проверка объёмом).
    return finish(part, name)


# ============================ 2. ЛЮЛЬКА (CRADLE) ============================
# Локальная система печати: +Z_l = мировая +X (ось cross-трубы, ВЕРТИКАЛЬНО).
#   +X_l = мировая -Z (мировой «низ» = локальный +X → ролики/BDC),
#   +Y_l = мировая +Y.
# Ключевые локальные точки (относительно центра бора хомута на cross-трубе):
#   ось колеса   (-60, 0, 0)   диск: центр(-60,0) R100, толщина z∈[-7.5,7.5]
#   ролики       (+ROLL_DZ.. ) → (ROLL_DZ-60=31.1, ±63.7, 0)   оси по +Z_l
#   обод BDC     (+40, 0, 0)         обод TDC  (-160, 0, 0)
#   палец-накладка над TDC при (-161, 0, z) с зазором 1мм
def rocker_cradle(side=+1, name="Rocker_cradle_R"):
    rx = 60.0                       # смещение оси колеса по -X_l (локально)
    rcx = ROLL_DZ - rx              # 31.1  локальная x центров роликов
    Z_TOP = -8.0                    # верх плиты (внутренняя грань, зазор от диска)
    Z_BOT = -18.0                   # низ плиты
    # --- хомут cross-трубы: бор +Z_l, смещён ВНУТРЬ (z<Z_TOP), прорезь +X_l ---
    ch = 40.0
    clamp = tc.clamp_mesh(ch)
    clamp.apply_translation([0, 0, -(6.0) - ch])   # z∈[-46, -6], верх у диска
    # хаб-блок вокруг хомута (садится на стол, даёт тело под плиту)
    hub = box(CLAMP_OD + 8, CLAMP_OD + 6, 46 - 8, T=tr(0, 0, -(46 - 8) / 2 - 8))

    parts = [clamp, hub]

    # --- несущая плита (внутренняя грань диска), консоль к роликам и пальцу ---
    plate = box(rcx + 40, 2 * ROLL_Y + 24, Z_TOP - Z_BOT,
                T=tr((rcx + 40) / 2 - 24, 0, (Z_TOP + Z_BOT) / 2))
    parts.append(plate)
    finger_beam = box(200, 26, Z_TOP - Z_BOT,
                      T=tr(-160 + 90, 0, (Z_TOP + Z_BOT) / 2))  # балка к пальцу x:-160..30
    parts.append(finger_beam)

    # косынки 45° от хаба под плиту (уменьшают вылет, держат ≥45° свесы)
    parts.append(wedge_gusset(rcx, 12, 30, T=tr(4, -6, -46)))

    # --- ролики 608: вилка (2 уха) + ось Ø8 вдоль +Z_l ---
    roller_bores = []
    for sy in (+1, -1):
        yc = sy * ROLL_Y
        # нижнее ухо = верх плиты до z=-4 (плечо подшипника)
        lower = box(24, 22, (Z_TOP) - (-4) + 0.0 + 8, T=tr(rcx, yc, (-8 + (-4)) / 2))
        # верхнее ухо
        upper = box(24, 22, 6, T=tr(rcx, yc, 7))
        # внешняя стенка-перемычка (радиально наружу от колеса, r>111 → мимо диска)
        web = box(8, 22, 22, T=tr(rcx + 14, yc, 0))
        parts += [lower, upper, web]
        # направляющие бортики: заходят на грань диска (r<100) с обеих сторон
        # обода (z=±(полуширина+борт)) → не дают колесу уйти по оси X
        for sz in (+1, -1):
            parts.append(box(14, 8, 5, T=tr(rcx - 18, yc - sy * 6, sz * (DISC_HALF + 1))))
        # ось Ø8 сквозь оба уха (вычесть)
        roller_bores.append(cyl(SHAFT_D / 2 + 0.1, 30, T=tr(rcx, yc, 0), seg=32))

    # --- палец-антиподъём над TDC ---
    post = box(12, 16, 44, T=tr(-166, 0, (44) / 2 - 18))     # стойка от плиты вверх
    pad = box(9, 26, 2 * DISC_HALF + 6, T=tr(-165.5, 0, 0))  # накладка ~1мм над ободом TDC
    parts += [post, pad]

    body = uni(parts)

    # --- вычесть боры/крепёж ---
    cuts = list(roller_bores)
    # крепёж alt-drive к люльке: 2×M4 clr в плите (совпадают с лапой привода)
    for sy in (+1, -1):
        cuts.append(cyl(M4_CLR / 2, 30, T=tr(rcx, sy * 22, -13), seg=24))
    body = dif(body, cuts)

    # L-люлька = зеркало по оси ТРУБЫ (локальная Z = мировая X): хомут уходит
    # на противоположную сторону диска (внутрь у своего конца cross-трубы)
    if side < 0:
        body = mirror_z(body)
    return finish(body, name)


# ============================ 3. ФРИКЦ. ПРИВОД ВЫСОТЫ ============================
# Та же локальная система (+Z_l = мировая X). Контакт ролика с ободом на BDC
# (мировое (170,0,490)) → локально обод BDC = (+40,0,0); центр фрикц. ролика
# опущен на FRIC_R «вниз» (мировое -Z = локальное +X) → (+40+FRIC_R, 0, 0).
def rocker_alt_drive(name="Rocker_alt_drive"):
    rcx = 40.0 + FRIC_R              # локальная x оси фрикц. вала = 57.5
    shaft_xy = (rcx, 0.0)
    motor_xy = (rcx, BELT_CD)        # мотор на CD 58.6 (+Y), ось +Z_l
    pivot_xy = (rcx + 55.0, -20.0)   # ось качания (вертикаль, M5) поодаль

    parts = []
    # --- корпус вала: колонна с 2×608 (снизу и сверху), высота под стек ---
    col = box(30, 30, 44, T=tr(rcx, 0, 22))
    parts.append(col)
    # --- площадка мотора (верх, z=44) с пилотом ---
    mplate = box(46, 46, 6, T=tr(rcx, BELT_CD / 2, 44 + 3))
    parts.append(mplate)
    # --- ребро/шейка, соединяющее вал и площадку мотора ---
    neck = box(20, BELT_CD, 12, T=tr(rcx, BELT_CD / 2, 44 - 6))
    parts.append(neck)
    # --- качающийся рычаг: плечо от оси качания к валу + проушина пружины ---
    arm = box(70, 20, 16, T=tr((rcx + pivot_xy[0]) / 2, -10, 8))
    piv = cyl(9, 30, T=tr(*pivot_xy, 15), seg=32)
    parts.append(arm)
    parts.append(piv)
    # проушина пружины (крючок) у ролика, тянет к ободу (-X_l)
    hook = box(10, 10, 12, T=tr(rcx - 22, -22, 8))
    parts.append(hook)
    # --- лапа крепления к люльке (2×M4), на -X_l стороне (внутрь) ---
    # ширина по X доведена до колонны (перекрытие ~7мм), иначе лапа висела
    # отдельным телом (зазор 3мм до колонны → union не сваривал).
    foot = box(30, 60, 10, T=tr(rcx - 22.5, 0, 5))
    parts.append(foot)

    body = uni(parts)

    cuts = []
    # 2×608 гнёзда в колонне (сверху и снизу, борт 1мм → сквозной вал Ø8.4)
    cuts.append(cyl(BEAR_SEAT / 2, BEAR_SEAT_H, T=tr(*shaft_xy, 44 - BEAR_SEAT_H / 2), seg=48))
    cuts.append(cyl(BEAR_SEAT / 2, BEAR_SEAT_H, T=tr(*shaft_xy, 0 + BEAR_SEAT_H / 2), seg=48))
    cuts.append(cyl((BEAR_ID + 0.4) / 2, 60, T=tr(*shaft_xy, 22), seg=32))  # сквозной вал
    # NEMA17: пилот Ø22.6 + 4×M3 на 31×31
    cuts.append(cyl(NEMA_PILOT / 2, 14, T=tr(*motor_xy, 44 + 1), seg=48))
    for sx in (+1, -1):
        for sy in (+1, -1):
            cuts.append(cyl(M3_CLR / 2, 16,
                            T=tr(motor_xy[0] + sx * NEMA_HOLE / 2,
                                 motor_xy[1] + sy * NEMA_HOLE / 2, 44), seg=20))
    # ось качания M5
    cuts.append(cyl(M5_CLR / 2, 40, T=tr(*pivot_xy, 15), seg=32))
    # крючок пружины Ø3
    cuts.append(cyl(1.6, 20, T=tr(rcx - 22, -22, 8) @ roty(90), seg=16))
    # лапа: 2×M4 clr (совпадают с отверстиями люльки y=±40... на лапе y=±22)
    for sy in (+1, -1):
        cuts.append(cyl(M4_CLR / 2, 20, T=tr(rcx - 26, sy * 22, 5), seg=20))

    body = dif(body, cuts)
    return finish(body, name)


def rocker_alt_roller(name="Rocker_alt_roller"):
    """Фрикц. ролик Ø35 с проточкой под O-ring, бор Ø8 под вал, M3-фиксатор."""
    r = FRIC_R
    body = cyl(r, 16, T=tr(0, 0, 8))
    groove = trimesh.creation.torus(major_radius=r, minor_radius=2.2,
                                    major_sections=48, minor_sections=16)
    groove.apply_translation([0, 0, 8])
    body = dif(body, [groove,
                      cyl((SHAFT_D + 0.4) / 2, 20, T=tr(0, 0, 8), seg=32),
                      cyl(M3_TAP / 2, r, T=tr(r / 2, 0, 8) @ roty(90), seg=16)])
    return finish(body, name)


# ============================ MAIN ============================
def main():
    print("Генерация ALT-яруса рокера (вышки/люльки/привод высоты)…")
    _, _, lensR = _apex_dirs(+1)
    print(f"  длины труб (из координат): нога(перед)→apex {lensR['leg']:.1f}мм, "
          f"нога(зад,270°)→apex {lensR['rear']:.1f}мм, cross {2*WHEEL_X:.1f}мм")
    print(f"  хомут сына: бор Ø{tc.BORE_D}, воротник {CLAMP_OD}мм — переиспользован во всех сокетах")
    rocker_tower_apex(+1, "Rocker_tower_apex_R")
    rocker_tower_apex(-1, "Rocker_tower_apex_L")
    rocker_cradle(+1, "Rocker_cradle_R")
    rocker_cradle(-1, "Rocker_cradle_L")
    rocker_alt_drive("Rocker_alt_drive")
    rocker_alt_roller("Rocker_alt_roller")
    print(f"\nГотово → {OUTDIR}")


if __name__ == "__main__":
    main()
