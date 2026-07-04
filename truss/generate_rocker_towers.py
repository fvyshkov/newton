#!/usr/bin/env python3
"""
Высотный (ALT) ярус рокера-добсона под колёса Ø200 — вышки, люльки, фрикционный
привод высоты. GoTo, Этап 2. Генерит бинарные STL в truss/stl/ через CSG
(trimesh + manifold3d).

СТИЛЬ УЗЛА (эталон truss/_proto_reference.py): узел = union разрезных хомутов-
цилиндров (tube_clamp.place_clamp) + МИНИМАЛЬНОЕ ядро, которое ровно сваривает их
в одно watertight-тело, + ТОЛЬКО функциональные фичи (оси роликов, привод).
НИКАКИХ косынок/гуссетов, R200-дуг, толстых «шеек», glide-pad'ов, импорта меша.

Мировая система (мм, z=0 = верх нижней доски) берётся ИМПОРТОМ из
gen_rocker_comic (НЕ хардкодим): CORNER_ANGLES, R_CORNER, FRAME_Z, WHEEL_X,
APEX_Z, ALT_AXIS, polar(). Труба = Ø22 алюминий, хомут = чистый разрезной
цилиндр (бор Ø22.4, поперечный болт M5, прорезь). Все сокеты — ЭТОТ ЖЕ хомут.

ПОЗА ПЕЧАТИ (каждая деталь пере-ориентируется в естественную позу, z_min=0):
  • apex — детали СОБИРАЮТСЯ в мировых координатах (чтобы оси труб сходились),
    затем поворачиваются так, что ось cross-хомута ВЕРТИКАЛЬНА (её круглый торец
    ложится на стол): важнейший скользящий бор печатается вертикально, без
    поддержки; две ноги-хомута расходятся вверх-в-стороны.
  • cradle / alt_drive / roller — собираются сразу в локальной ПЕЧАТНОЙ системе
    (локальная +Z = мировая X = ось cross-трубы, ВЕРТИКАЛЬНО): все боры (хомут,
    оси роликов, вал, пилот мотора) идут вдоль +Z → печатаются вертикальными
    отверстиями без поддержек. finish() лишь сажает деталь на стол (z_min=0).

finish(): merge → process → выкидывает паразитные тела (оставляет самое
крупное) → опц. поворот в позу печати → сажает на стол (z_min=0) → экспорт.

Все посадки: M4 clr 4.4, M3 clr 3.4 / саморез 2.7, M5 clr 5.4, M10 clr 10.6,
608 ось Ø8 (+зазор), NEMA17 пилот Ø22.6 + M3 на 31×31.
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

# --- Хомут (импорт) ---
CLAMP_OD = tc.CLAMP_OD               # ≈30.4 наружный Ø
CLAMP_H = tc.CLAMP_H                 # 46

# --- Посадки ---
M3_CLR, M3_TAP = 3.4, 2.7
M4_CLR = 4.4
M5_CLR = 5.4
BEAR_OD = 22.0                       # 608 наружный
BEAR_ID = 8.0                        # 608 внутренний
BEAR_W = 7.0                         # 608 ширина
BEAR_SEAT = 22.15                    # прессовое гнездо 608
BEAR_SEAT_H = 7.3
NEMA_PILOT = 22.6
NEMA_HOLE = 31.0                     # M3 на 31×31
SHAFT_D = 8.0

# --- Вышки / apex: минимально, как в эталоне (хомуты + ядро-шар) ---
HUB_R = 16.0                         # радиус ядра-шара (ровно сваривает хомуты)
APEX_CLAMP_H = 44.0                  # длина воротника ноги вышки (грип ≥40мм на Ø22)
CROSS_CLAMP_H = 40.0                 # длина воротника cross-хомута
# STAGGER: две ноги apex расходятся всего на ~42° → их боры пересекаются у ядра и
# «палка не влезет» (входной торец одной ноги перекрыт телом другой). Раздвигаем
# ЗАДНЮЮ ногу вдоль её оси на LEG_STAGGER: её воротник (с ушками+болтом) уходит
# наружу, входные торцы двух ног разнесены по оси → каждая труба входит на полный
# грип. Плюс сквозная расточка бора Ø22.4 через ядро (труба садится в ПУСТОЙ бор).
LEG_STAGGER = 22.0                   # вынос заднего воротника вдоль его оси, мм
# --- Тест-посадки трубы (в самом генераторе) ---
TUBE_D = 22.0                        # номинал алюминиевой трубы
GRIP = 40.0                          # требуемая глубина посадки
DRILL_D = 22.4                       # Ø сквозной расточки бора (= бор хомута)
FIT_TOL = 8.0                        # порог теста: <8% объёма трубы = PASS

# --- Ролики люльки ---
ROLL_Y = 63.7                        # ±y центров роликов (±35°, r=111)
ROLL_DZ = 91.1                       # опускание центра ролика под ось колеса
DISC_HALF = WHEEL_W / 2.0 + 1.5      # полузазор от диска колеса, ≈9.0

# --- Фрикц. привод высоты ---
FRIC_R = 17.5                        # фрикц. ролик Ø35
BELT_CD = 58.6                       # межосевое GT2 20T→60T

ICO = 3                              # подразбиение сферы-ядра
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


def axis_cyl(direction, z0, z1, dia, origin=(0.0, 0.0, 0.0), seg=48):
    """Цилиндр Ø`dia` вдоль `direction`, от параметра z0 до z1 (мм по оси),
    отсчитывая от `origin` (точка на оси при z=0). Для расточки бора и теста."""
    d = np.asarray(direction, float); d /= np.linalg.norm(d)
    o = np.asarray(origin, float)
    L = float(z1 - z0)
    c = trimesh.creation.cylinder(radius=dia / 2.0, height=L, sections=seg)
    T = trimesh.geometry.align_vectors([0, 0, 1], d)
    T[:3, 3] = o + d * (z0 + L / 2.0)
    c.apply_transform(T)
    return c


def drill_bores(body, sockets):
    """Сквозная расточка бора Ø DRILL_D по каждому сокету: от z=−3 (сквозь ядро)
    до входного торца воротника (entry). Гарантирует ПУСТОЙ бор на полный грип —
    труба входит до упора, тело соседа на пути расточено (не мешает)."""
    cuts = [axis_cyl(d, -3.0, entry, DRILL_D, origin=o) for _, o, d, entry in sockets]
    return dif(body, cuts)


def tube_fit_test(body, sockets, name):
    """ТЕСТ ПОСАДКИ: для каждого сокета строим Ø22 цилиндр длиной GRIP от входного
    торца бора ВНУТРЬ; пересекаем с телом узла. Труба должна сидеть в ПУСТОМ боре →
    объём пересечения < FIT_TOL% от объёма трубы = PASS."""
    tvol = math.pi * (TUBE_D / 2.0) ** 2 * GRIP
    all_pass = True
    for label, o, d, entry in sockets:
        t = axis_cyl(d, entry - GRIP, entry, TUBE_D, origin=o)
        inter = trimesh.boolean.intersection([body, t], engine=ENGINE)
        vol = abs(inter.volume) if (inter is not None and len(inter.vertices)) else 0.0
        frac = vol / tvol * 100.0
        ok = frac < FIT_TOL
        all_pass = all_pass and ok
        print(f"    tube-fit {name}:{label:<6} {frac:5.1f}%  {'PASS' if ok else 'FAIL'}")
    return all_pass


def tube_fit(body, origin, tube_dir, clamp_h, name, grip=40.0, tube_d=22.0):
    """ТЕСТ ВСТАВКИ ТРУБЫ. Строит цилиндр Ø22 длиной `grip`(40) ВДОЛЬ оси трубы,
    начиная у ВХОДА бора (наружный торец хомута) и уходя ВНУТРЬ на grip. Труба
    должна сидеть в ПОЛОСТИ бора → пересечение с телом узла < 8% объёма трубы.
    Печатает PASS/FAIL. Проверяется на теле ДО finish() (в его собственной
    системе — тест инвариантен к позе)."""
    d = np.asarray(tube_dir, float); d /= np.linalg.norm(d)
    entry = np.asarray(origin, float) + d * clamp_h      # наружный торец = вход трубы
    center = entry - d * (grip / 2.0)                    # центр пробника
    T = trimesh.geometry.align_vectors([0.0, 0.0, 1.0], d)  # ось цилиндра +Z → d
    T[:3, 3] = center
    probe = cyl(tube_d / 2.0, grip, T=T, seg=48)
    inter = trimesh.boolean.intersection([body, probe], engine=ENGINE)
    vi = abs(inter.volume) if (inter is not None and len(inter.vertices) > 0) else 0.0
    vt = math.pi * (tube_d / 2.0) ** 2 * grip
    ratio = vi / vt
    ok = ratio < 0.08
    print(f"    tube-fit {name}: {'PASS' if ok else 'FAIL'}  "
          f"пересечение={ratio*100:5.1f}% от объёма трубы (порог 8%)")
    return ok


def finish(mesh, name, pose=None):
    """Финализация: сшить, выкинуть паразитные тела (оставить самое крупное),
    опц. повернуть в позу печати (`pose` = 4×4), посадить на стол (z_min=0),
    экспортировать. Эталон: _proto_reference.hub_ground()."""
    OUTDIR.mkdir(parents=True, exist_ok=True)
    # Грубая сварка вершин ДО валидации (тела вращения дают sliver-пары ~5e-7 —
    # process(validate=True) их дырявит); схлопываем в честное ребро (эталон —
    # generate_rocker_frame_truss.finish).
    mesh.merge_vertices(digits_vertex=5)
    mesh.process(validate=True)
    # выкинуть паразитные тела — оставить самое крупное (по объёму)
    bodies = mesh.split(only_watertight=False)
    if len(bodies) > 1:
        mesh = max(bodies, key=lambda m: abs(m.volume))
    if pose is not None:
        mesh.apply_transform(pose)
    mesh.apply_translation([0, 0, -mesh.bounds[0, 2]])   # z_min = 0
    mesh.merge_vertices(digits_vertex=5)
    mesh.process(validate=True)
    if not mesh.is_watertight:
        trimesh.repair.fill_holes(mesh)
        mesh.fix_normals()
    out = OUTDIR / f"{name}.stl"
    mesh.export(out)
    bb = mesh.bounds
    print(f"  {name}.stl  watertight={mesh.is_watertight}  vol={mesh.volume/1000:.2f}cm³  "
          f"bbox={bb[1,0]-bb[0,0]:.0f}×{bb[1,1]-bb[0,1]:.0f}×{bb[1,2]-bb[0,2]:.0f}mm")
    return mesh


def seat_enclosure_test(body, seats, wall=3.0):
    """Проверка ОГРАЖДЕНИЯ круглых гнёзд: для каждого гнезда (x,y,z0,z1,r) строим
    кольцо-щуп [r .. r+wall] на его глубине и пересекаем с телом. Если стенка
    ≥wall кругом — щуп целиком в теле → отношение ≈100% (PASS). Клип кромкой →
    отношение <100% (FAIL). Печатает PASS/FAIL и % заполнения стенки."""
    print("  ТЕСТ ОГРАЖДЕНИЯ ГНЁЗД (кольцо-щуп r..r+3мм; PASS ≥98%):")
    allpass = True
    for nm, x, y, z0, z1, r in seats:
        h = z1 - z0
        outer = cyl(r + wall, h, T=tr(x, y, (z0 + z1) / 2), seg=64)
        inner = cyl(r, h + 2, T=tr(x, y, (z0 + z1) / 2), seg=64)
        ring = dif(outer, [inner])
        v_ring = math.pi * ((r + wall) ** 2 - r ** 2) * h
        try:
            it = trimesh.boolean.intersection([body, ring], engine=ENGINE)
            v_it = abs(it.volume) if it is not None and len(it.faces) else 0.0
        except Exception:
            v_it = float("nan")
        frac = v_it / v_ring
        ok = frac >= 0.98
        allpass = allpass and ok
        print(f"    {nm:16s} стенка {frac*100:5.1f}%  {'PASS' if ok else 'FAIL'}")
    return allpass


# ============================ 1. APEX ВЕРШИНЫ ============================
def _apex_dirs(side):
    """Направления трёх труб ОТ вершины (единичные). side=+1 правый, -1 левый."""
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


def _apex_slit(key, d):
    """Прорезь воротника — в СВОБОДНОЕ пространство:
      • cross (труба горизонтальна) → прорезь строго ВВЕРХ (+Z);
      • нога (труба крутая, вниз)   → прорезь по горизонт. радиусу НАРУЖУ.
    """
    if key == "cross":
        return np.array([0.0, 0.0, 1.0])
    h = np.array([d[0], d[1], 0.0])
    return h / np.linalg.norm(h)


def rocker_tower_apex(side=+1, name="Rocker_tower_apex_R"):
    """Вершина: 3 хомута-цилиндра из общего центра + ядро-шар. Прорези: cross
    ВВЕРХ, две ноги — радиально наружу. STAGGER: две ноги всего ~42° апарт → их
    боры пересекались и «палка не влезала». ЗАДНЮЮ ногу выносим вдоль её оси на
    LEG_STAGGER (её воротник+ушки уходят наружу; входные торцы двух ног разнесены
    по оси), а гэп от ядра до вынесенного воротника заполняем струтом-цилиндром.
    Затем СКВОЗНАЯ расточка всех трёх боров Ø22.4 через ядро → каждая труба входит
    в ПУСТОЙ бор на полный грип (tube-fit PASS). Собирается с вершиной в НАЧАЛЕ
    координат; печатная поза — ось cross-хомута вертикально. L = зеркало R по X."""
    _, dirs, _ = _apex_dirs(side)
    # сокеты: (label, origin, dir, entry) — entry = вынос входного торца по оси
    offs = {"cross": 0.0, "leg": 0.0, "rear": LEG_STAGGER}
    hgt = {"cross": CROSS_CLAMP_H, "leg": APEX_CLAMP_H, "rear": APEX_CLAMP_H}
    parts = [trimesh.creation.icosphere(subdivisions=ICO, radius=HUB_R)]
    sockets = []
    for key, d in dirs.items():
        slit = _apex_slit(key, d)
        off, h = offs[key], hgt[key]
        origin = d * off
        parts.append(tc.place_clamp(h, tuple(origin), tube_dir=d, slit_dir=slit))
        if off > 0.5:   # струт ядро→вынесенный воротник (сваривает, потом расточится)
            parts.append(axis_cyl(d, -8.0, off + 8.0, CLAMP_OD, seg=SEG))
        sockets.append((key, np.zeros(3), d, off + h))
    part = uni(parts)
    part = drill_bores(part, sockets)          # сквозной пустой бор на каждый сокет
    ok = tube_fit_test(part, sockets, name)
    assert ok, f"{name}: tube-fit FAIL — палка не влезет"
    # ПОЗА ПЕЧАТИ: ось cross-хомута → вертикаль (её бор печатается без поддержки)
    pose = trimesh.geometry.align_vectors(dirs["cross"], [0.0, 0.0, 1.0])
    return finish(part, name, pose=pose)


# ============================ 2. ЛЮЛЬКА (CRADLE) ============================
# Локальная ПЕЧАТНАЯ система: +Z_l = мировая +X (ось cross-трубы, ВЕРТИКАЛЬНО),
#   +X_l = мировая −Z (мировой «низ» → к роликам/ободу),  +Y_l = мировая +Y.
# Ключевые локальные точки (0 = центр бора хомута на cross-трубе):
#   ось колеса (-60,0,0); диск R100 толщиной z∈[-7.5,7.5];
#   ролики (rcx=31.1, ±63.7, 0), оси по +Z_l;  обод BDC (+40,0,0), TDC (-160,0,0).
def rocker_cradle(side=+1, name="Rocker_cradle_R"):
    """ОДИН хомут вокруг cross-трубы (прорезь ВВЕРХ, скользит+зажимает) +
    ДВЕ вилки роликов 608 (оси Ø8 вдоль +Z_l) + палец-антиподъём над ободом.
    Колесо катится по РОЛИКАМ. ХОМУТ ПРИВАРЕН к раме ЖИРНЫМ СПЛОШНЫМ ВЕБОМ
    (по всей ЗАДНЕЙ образующей воротника, +X_l), а НЕ тонкой шейкой: магистральная
    плита на всю высоту воротника + 2 боковые косынки-рёбра + шапка в плоскость
    роликов → изгибная нагрузка от трубы имеет ЖЁСТКИЙ сплошной путь в балку.
    Бор cross-трубы ПЕРЕ-СВЕРЛИВАется после union → полость чиста, труба входит на
    полный грип. L = зеркало по оси трубы (mirror_z)."""
    rx = 60.0                       # ось колеса по −X_l
    rcx = ROLL_DZ - rx              # 31.1  локальная x центров роликов
    Z_IN = -12.0                    # плоскость тела ВНУТРИ диска (z_l<−7.5)
    ch = 40.0
    UP = np.array([-1.0, 0.0, 0.0])       # прорезь ВВЕРХ (лок. −X_l = мир. +Z)
    ZL = np.array([0.0, 0.0, 1.0])        # ось бора = ось cross-трубы (+Z_l)
    C_ORIG = (0.0, 0.0, -6.0 - ch)        # точка оси бора у ВНУТРЕННЕГО торца хомута
    # воротник: z_l∈[−46,−6]; вход трубы у z_l=−6 (наружный торец, +Z_l)

    # --- хомут: бор вдоль +Z_l, смещён ВНУТРЬ (z_l∈[−46,−6]), прорезь ВВЕРХ ---
    parts = [tc.place_clamp(ch, C_ORIG, tube_dir=ZL, slit_dir=UP)]

    # --- ЖИРНЫЙ СПЛОШНОЙ ВЕБ хомут→балка (заменяет тонкую шейку) ---
    #  магистральная плита: вся ЗАДНЯЯ (+X_l) образующая воротника, полная высота
    parts.append(box(36, 40, 44, T=tr(20, 0, -24)))        # x_l 2..38, y ±20, z_l −46..−2
    for sy in (+1, -1):                                    # 2 боковые косынки-рёбра (fillet)
        parts.append(box(30, 16, 40, T=tr(20, sy * 24, -22)))  # y ±16..32, x_l 5..35
    parts.append(box(30, 40, 20, T=tr(20, 0, -4)))         # шапка веба в плоскость роликов

    # --- балка-спина вдоль Y (несёт вилки роликов) ---
    parts.append(box(18, 2 * ROLL_Y + 22, 8, T=tr(rcx, 0, Z_IN)))   # спина

    # --- вилки роликов 608: 2 уха (внутри/снаружи диска) + перемычка, ось Ø8 +Z_l
    roller_bores = []
    for sy in (+1, -1):
        yc = sy * ROLL_Y
        parts.append(box(24, 22, 12, T=tr(rcx, yc, -4)))   # ухо внутри диска
        parts.append(box(24, 22, 6, T=tr(rcx, yc, 7)))     # ухо снаружи диска
        parts.append(box(8, 22, 22, T=tr(rcx + 14, yc, 0)))  # перемычка r>111 (мимо диска)
        roller_bores.append(cyl(SHAFT_D / 2 + 0.1, 30, T=tr(rcx, yc, 0), seg=32))

    # --- палец-антиподъём над TDC обода: два рельса по бокам (обходят хомут) +
    #     перемычка + накладка над ободом с зазором 1мм ---
    for sy in (+1, -1):
        parts.append(box(191, 14, 8, T=tr((rcx - 160) / 2, sy * 42, Z_IN)))
    parts.append(box(14, 100, 8, T=tr(-160, 0, Z_IN)))              # перемычка у TDC
    parts.append(box(10, 26, 2 * DISC_HALF + 6, T=tr(-166, 0, 0)))  # накладка над ободом

    body = uni(parts)

    # --- боры/крепёж ---
    cuts = list(roller_bores)
    # ПЕРЕ-СВЕРЛИТЬ бор cross-трубы Ø22.4 сквозь веб → полость чиста, труба входит
    cuts.append(cyl(tc.BORE / 2, ch + 20, T=tr(0, 0, -26), seg=48))
    for sy in (+1, -1):   # 2×M4 к лапе привода (совпадают с лапой alt_drive)
        cuts.append(cyl(M4_CLR / 2, 30, T=tr(rcx, sy * 22, Z_IN), seg=24))
    body = dif(body, cuts)

    # --- ТЕСТ ВСТАВКИ cross-трубы (на теле до mirror/finish, инвариантно к позе) ---
    tube_fit(body, C_ORIG, ZL, ch, name)

    if side < 0:          # L = зеркало по оси трубы (прорезь остаётся ВВЕРХ)
        body = mirror_z(body)
    return finish(body, name)


# ============================ 3. ФРИКЦ. ПРИВОД ВЫСОТЫ ============================
# Та же локальная система (+Z_l = мировая X). Обод BDC = локально (+40,0,0);
# центр фрикц. ролика опущен на FRIC_R «вниз» (мир. −Z = лок. +X) → (+40+R,0,0).
def rocker_alt_drive(name="Rocker_alt_drive"):
    """Фрикц. привод: колонна с 2×608 под вал Ø8 + площадка NEMA17 (GT2 3:1) +
    качающийся рычаг (ось M5) с крючком пружины + лапа к люльке (2×M4). Все боры
    вертикальны (лок. +Z). Никаких дуг/косынок — только рабочая геометрия."""
    rcx = 40.0 + FRIC_R              # локальная x оси фрикц. вала = 57.5
    shaft_xy = (rcx, 0.0)
    motor_xy = (rcx, BELT_CD)        # мотор на CD 58.6 (+Y)
    pivot_xy = (rcx + 55.0, -20.0)   # ось качания (вертикаль, M5)

    parts = []
    parts.append(box(30, 30, 44, T=tr(rcx, 0, 22)))              # колонна вала (2×608)
    # ПЛОЩАДКА МОТОРА: центр на оси NEMA (motor_xy), а НЕ на полпути (BELT_CD/2) —
    # иначе пилот Ø22.6 и болты M3 (31×31) свисают за кромку (клип по фидбеку).
    # 46×46 ⇒ ≥11мм стенка вокруг пилота, ≥7мм вокруг крайних болтов M3.
    parts.append(box(46, 46, 6, T=tr(rcx, BELT_CD, 44 + 3)))      # площадка мотора (центр = ось NEMA)
    parts.append(box(20, BELT_CD, 16, T=tr(rcx, BELT_CD / 2, 40)))  # шейка колонна→площадка (overlap +Z)
    parts.append(box(70, 20, 16, T=tr((rcx + pivot_xy[0]) / 2, -10, 8)))  # плечо к оси качания
    parts.append(cyl(9, 30, T=tr(*pivot_xy, 15), seg=32))         # проушина оси качания
    parts.append(box(10, 10, 12, T=tr(rcx - 22, -22, 8)))         # крючок пружины
    parts.append(box(30, 60, 10, T=tr(rcx - 22.5, 0, 5)))         # лапа к люльке (перекрыв. колонну)

    body = uni(parts)

    cuts = []
    cuts.append(cyl(BEAR_SEAT / 2, BEAR_SEAT_H, T=tr(*shaft_xy, 44 - BEAR_SEAT_H / 2), seg=48))
    cuts.append(cyl(BEAR_SEAT / 2, BEAR_SEAT_H, T=tr(*shaft_xy, 0 + BEAR_SEAT_H / 2), seg=48))
    cuts.append(cyl((BEAR_ID + 0.4) / 2, 60, T=tr(*shaft_xy, 22), seg=32))  # сквозной вал Ø8
    cuts.append(cyl(NEMA_PILOT / 2, 14, T=tr(*motor_xy, 44 + 1), seg=48))   # пилот NEMA17
    for sx in (+1, -1):
        for sy in (+1, -1):
            cuts.append(cyl(M3_CLR / 2, 16,
                            T=tr(motor_xy[0] + sx * NEMA_HOLE / 2,
                                 motor_xy[1] + sy * NEMA_HOLE / 2, 44), seg=20))
    cuts.append(cyl(M5_CLR / 2, 40, T=tr(*pivot_xy, 15), seg=32))           # ось качания M5
    cuts.append(cyl(1.6, 20, T=tr(rcx - 22, -22, 8) @ roty(90), seg=16))    # крючок пружины Ø3
    for sy in (+1, -1):                                                     # 2×M4 к люльке
        cuts.append(cyl(M4_CLR / 2, 20, T=tr(rcx - 26, sy * 22, 5), seg=20))

    body = dif(body, cuts)

    # --- проверка: каждое круглое гнездо ограждено стенкой ≥3мм кругом ---
    seats = [
        ("608 верх",  shaft_xy[0], shaft_xy[1], 44 - BEAR_SEAT_H, 44,       BEAR_SEAT / 2),
        ("608 низ",   shaft_xy[0], shaft_xy[1], 0,                BEAR_SEAT_H, BEAR_SEAT / 2),
        ("вал Ø8",    shaft_xy[0], shaft_xy[1], 8,                36,        (BEAR_ID + 0.4) / 2),
        ("NEMA пилот", motor_xy[0], motor_xy[1], 44,              50,        NEMA_PILOT / 2),
        ("ось качания", pivot_xy[0], pivot_xy[1], 2,              28,        M5_CLR / 2),
    ]
    seat_enclosure_test(body, seats)
    return finish(body, name)


def rocker_alt_roller(name="Rocker_alt_roller"):
    """Фрикц. ролик Ø35 с проточкой под O-ring, бор Ø8 под вал, M3-фиксатор.
    Печатается как есть — ось бора вертикальна."""
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
    print(f"  хомут: бор Ø{tc.BORE_D}, воротник Ø{CLAMP_OD}мм — переиспользован во всех сокетах")
    rocker_tower_apex(+1, "Rocker_tower_apex_R")
    rocker_tower_apex(-1, "Rocker_tower_apex_L")
    rocker_cradle(+1, "Rocker_cradle_R")
    rocker_cradle(-1, "Rocker_cradle_L")
    rocker_alt_drive("Rocker_alt_drive")
    rocker_alt_roller("Rocker_alt_roller")
    print(f"\nГотово → {OUTDIR}")


if __name__ == "__main__":
    main()
