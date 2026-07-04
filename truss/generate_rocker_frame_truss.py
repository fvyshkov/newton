#!/usr/bin/env python3
"""
Нижнее кольцо ВРАЩАЮЩЕЙСЯ рамы рокера как ферма «трубы + узлы».

Генерит 4 бинарных STL в truss/stl/ через CSG (trimesh + manifold3d), приваривая
к литым узлам ПРОВЕРЕННЫЙ хомут сына (incoming/son_tube_clamp.stl) через
tube_clamp.place_clamp(). Хомут НЕ изобретаем — это раздвижной разрезной
split-collar под трубу Ø22 (ручки-защёлки труб зажимаются в боре), поперечный
прижимной болт стягивает щёки через прорезь. Профиль призматичен вдоль оси бора.

Общий мир (мм, z=0 = верх грунт-доски) ИМПОРТИРУЕТСЯ из gen_rocker_comic
(НЕ хардкодим): CORNER_ANGLES=(30,150,270), R_CORNER=210, FRAME_Z=75 (ось труб
вращающейся рамы), WHEEL_X=170, APEX_Z=530 (вершины башен = ±170,0,530),
PINION_R=240, RING_Z=50 (зубья кольца z=50..60, верх дорожки скольжения z=60).
Направления всех труб СЧИТАЮТСЯ из координат концов (угол→угол хорды,
угол→центр радиали, угол→вершина ноги башни). КАЖДЫЙ хомут сидит на КОРОТКОЙ
ШЕЕ, торчащей из маленькой ступицы, а прорезь смотрит в СВОБОДНОЕ пространство
(горизонтальные трубы — строго ВВЕРХ; крутые ноги башни — по горизонтали
НАРУЖУ). Так щёки split-collar сжимаются свободно, а болт доступен сбоку.
ГЛАВНОЕ ИСПРАВЛЕНИЕ: прорези больше НЕ смотрят в соседние хомуты/ступицу и
ничего НЕ приварено над прорезью (проверено verify — щель прорези свободна).

  1. Rocker_corner_node.stl ×2 — рядовые углы 30° и 150°. Узел в
     polar(R_CORNER, ang, FRAME_Z) сводит до 5 хомутов на шеях:
       • 2 хорды к двум другим углам (горизонт, прорезь вверх),
       • 1 радиаль к центру рамы (горизонт, прорезь вверх),
       • 2 ноги башни ВВЕРХ-НАРУЖУ к ОБЕИМ вершинам (±170,0,530), прорезь
         наружу — каждая вершина раскосится всеми тремя углами → жёсткая башня.
     ВАЖНО: три горизонтальные трубы копланарны и лежат в 30° (аз 180/210/240),
     поэтому вынос воротника STANDOFF_H=44, чтобы соседний Ø46.6 воротник НЕ
     нависал над прорезью-вверх (строгое НЕкасание всех трёх при 30° требовало бы
     ~90-мм рычагов и столкновения с центральным узлом — невозможно; выбрана
     свобода ЩЕЛИ прорези как функциональный критерий).
     Снизу — небольшой ПЛОСКИЙ пад-скользяк z≈61 (не curved-обрезка) с карманом
     под PTFE: узел едет по дорожке кольца z=60. Центральная бобышка кармана
     держит мост потолка и несёт M3-саморез PTFE-подушки.
  2. Rocker_corner_drive.stl ×1 — задний угол 270°: ТОТ ЖЕ узел (те же 5
     гнёзд) ПЛЮС посадочная бобышка азимутального привода — плоский пад с
     4×M4 (сквозняк 4.4 + карман под гайку hex 7.0 A/F гл.3.2) под
     Rocker_swing_base и радиальный проём Ø40 к кольцу, чтобы шестерня на
     PINION_R=240 дотянулась до венца. Сам привод НЕ переделываем.
  3. Rocker_center_node.stl ×1 — центр вращающейся рамы: втулка по оси M10
     (бор 10.6, едет по гладкому хвостовику), 3 радиальных хомута к трём
     углам на FRAME_Z, и полка под плату AS5048A над колпачком магнита
     (идея полки — из Rocker_pivot_flange: холдер board_holder ложится ВВЕРХ
     НОГАМИ, чип на оси ~1мм над магнитом, свес полки на 45°-клине без
     поддержек). Плата и колпачок — отдельные детали, тут только полка+пилоты.

ОРИЕНТАЦИЯ ПЕЧАТИ (без поддержек, где можно): узлы печатаются ПЛОСКИМ ДНОМ
z≈61 (у центра — низом втулки) на стол → бор втулки/карман PTFE вертикальны,
свес полки на 45°-клине. Хорды/радиали горизонтальны → их боры Ø22
горизонтальны и печатаются мостом по верху (как штатный мост болта у хомута
сына); при желании — символические поддержки. Ноги башни смотрят вверх-наружу
(> 45° от горизонта) → печатаются чисто.
"""
import math
from pathlib import Path

import numpy as np
import trimesh

import gen_rocker_comic as W            # общий мир (координаты, polar) — НЕ хардкод
import tube_clamp as TC                 # проверенный хомут сына + place_clamp

# ============================ ПАРАМЕТРЫ ============================
# --- Мир (из gen_rocker_comic) ---
CORNER_ANGLES = W.CORNER_ANGLES         # (30, 150, 270)
R_CORNER = W.R_CORNER                   # 210
FRAME_Z = W.FRAME_Z                     # 75  (ось труб вращающейся рамы)
WHEEL_X = W.WHEEL_X                     # 170
APEX_Z = W.APEX_Z                       # 530
PINION_R = W.PINION_R                   # 240
RING_TRACK_TOP = 60.0                   # верх дорожки скольжения кольца (z=50..60)
APEXES = [(WHEEL_X, 0.0, APEX_Z), (-WHEEL_X, 0.0, APEX_Z)]   # правая/левая вершины

# --- Хомут (из tube_clamp, замер по мешу сына) ---
CLAMP_H_SOCK = 44.0     # высота гнезда-хомута вдоль трубы, мм
BORE_D = TC.BORE_D      # Ø бора ≈ 21.94 (труба Ø22)
CLAMP_OD = TC.CLAMP_OD  # воротник ≈ 46.6 ⟂ прорези
SLIT_UP = (0.0, 0.0, 1.0)   # прорезь ВВЕРХ (+Z): щёки раскрываются в открытое небо

# --- Шея (стойка хомута) ---
# Каждый хомут сидит на КОРОТКОЙ ШЕЕ, торчащей из маленькой ступицы, чтобы
# воротник (со щеками+прорезью) стоял В СВОБОДНОМ пространстве и щёки могли
# сжиматься. Ступица соединяет ТОЛЬКО шеи, не воротники.
NECK_R = 13.0           # радиус шеи-стойки, мм (>Ø бора/2=11 → сваривается с
                        #   торцом воротника кольцом 11..13, глухой упор трубы)
NECK_OVER = 6.0         # заход шеи ВНУТРЬ воротника для водонепроницаемой сварки
# STANDOFF_H=44: у КАЖДОГО углового узла три горизонтальные трубы (2 хорды +
# радиаль) лежат В ОДНОЙ плоскости всего в 30° друг от друга (аз 180/210/240).
# При коротком выносе соседний Ø46.6 воротник нависает над прорезью-вверх и
# ЗАЖИМАЕТ щёки. Замер по мешу (verify): щель прорези (ядро ±25° вверх)
# освобождается только при выносе ≈44 (blocked 15→2=своя шея). 44 ещё не
# сталкивает воротник радиали с воротником центрального узла на той же 210-мм
# трубе (углов. 122..166 от центра, центр. 44..88 → зазор 34). Крайние «крылья»
# ±70° у копланарной тройки неизбежно касаются соседей (геометрия 30°), но щель
# раскрывается в открытое небо — хомут затягивается.
STANDOFF_H = 44.0       # вынос воротника горизонтальной трубы от центра, мм
STANDOFF_T = 18.0       # вынос воротника ноги башни (круче, слит наружу), мм

# --- Литой узел ---
HUB_R = 14.0            # радиус центральной сферы-ступицы (низ = дно пада z=61)
NODE_BOT_Z = 61.0       # плоское дно пада-скользяка — 1мм над дорожкой (60)
ICO_SUB = 3             # подразбиение икосферы ступицы

# --- Карман PTFE-скользяка (снизу углового узла) ---
PAD_D = 28.0            # Ø кармана под PTFE-подушку
PAD_DEEP = 2.0          # глубина кармана (подушка ~3мм, выступает 1мм на дорожку)
PAD_POST_D = 6.0        # центральная бобышка (держит мост потолка кармана)
M3_SELFTAP = 2.7        # пилот M3-самореза PTFE-подушки

# --- Привод (задний узел 270°): пад + 4×M4 + проём под шестерню ---
PAD_X = 56.0            # пад под Rocker_swing_base, X
PAD_Y = 62.0            # пад, Y (тянется наружу к PINION_R)
PAD_T = 8.0             # толщина пада
PAD_TOP_Z = 83.0        # верх пада (низ плиты swing_base здесь)
M4_CLR = 4.4            # сквозной M4
M4_NUT_AF = 7.0         # гайка M4 «под ключ» (hex)
M4_NUT_DEEP = 3.2       # глубина hex-кармана гайки
M4_DX = 44.0            # 4×M4: размах по X (болты ±22)
M4_DY = 20.0            # 4×M4: размах по Y (±10, оба ВНУТРИ от проёма шестерни)
PAD_CTR_Y = -206.0      # центр пада по Y (у узла, болты не задевают шестерню)
PINION_CLR_D = 40.0     # проём под шестерню Ø36 на PINION_R

# --- Втулка центра (по болту M10) ---
BUSH_OD = 22.0          # Ø втулки
M10_BORE = 10.6         # бор по гладкому хвостовику M10
BUSH_Z0 = NODE_BOT_Z    # низ втулки = дно узла
BUSH_Z1 = 100.0         # верх втулки

# --- Полка энкодера AS5048A (идея Rocker_pivot_flange) ---
MAG_TOP_Z = 130.0       # верх колпачка магнита на болте (мир, из gen_rocker_comic)
AIR_GAP = 1.0           # зазор магнит↔чип
CHIP_T = 1.1            # корпус чипа AS5048A над платой
BRD_T = 1.6             # толщина платы
HLD_BOSS_H = 3.0        # бобышки board_holder
SHELF_TOP_Z = MAG_TOP_Z + AIR_GAP + CHIP_T + BRD_T + HLD_BOSS_H   # 136.7
SHELF_T = 6.0           # толщина полки
SHELF_W = 28.0          # ширина полки/стойки по X (= ширина лапки холдера)
SHELF_Y_FRONT = 12.0    # передний край полки (к центру; +Y, чтобы не мешать
                        #   радиали к углу 270° — она смотрит на −Y)
POST_Y_FRONT = 17.0     # стойка у заднего края
POST_Y_BACK = 25.0
POST_Z0 = 80.0          # низ стойки (тонет в ступицу/втулку)
PILOT_XY = (10.0, 15.5)     # 2 пилота M3 холдера: ±x, +y (чип оказывается на оси)
PILOT_DEPTH = 8.0

SEG = 96                # фасеты полных окружностей
OUTDIR = Path(__file__).parent / "stl"


# ============================ ХЕЛПЕРЫ ============================
def cyl(r, h, seg=SEG, T=None):
    c = trimesh.creation.cylinder(radius=r, height=h, sections=seg)
    if T is not None:
        c.apply_transform(T)
    return c


def box(x, y, z, T=None):
    b = trimesh.creation.box(extents=(x, y, z))
    if T is not None:
        b.apply_transform(T)
    return b


def tr(x, y, z):
    M = np.eye(4)
    M[:3, 3] = (x, y, z)
    return M


def hexprism(af, h, T=None):
    """Шестигранная призма «под ключ» af (across flats), ось Z."""
    r = af / math.cos(math.radians(30)) / 2.0        # радиус по вершинам
    angs = np.radians(np.arange(6) * 60 + 30)
    pts = np.c_[r * np.cos(angs), r * np.sin(angs)]
    from shapely.geometry import Polygon
    m = trimesh.creation.extrude_polygon(Polygon(pts), height=h)
    if T is not None:
        m.apply_transform(T)
    return m


def rod(p0, p1, r, seg=32):
    """Сплошной цилиндр-стержень между точками p0..p1 (для шеи-стойки)."""
    return trimesh.creation.cylinder(radius=r, segment=np.array([p0, p1], float),
                                     sections=seg)


def slit_dir_for(node, d):
    """Направление прорези В СВОБОДНОЕ пространство:
      • горизонтальная-ish труба (|dz|<0.5) → прорезь строго ВВЕРХ (+Z):
        щёки раскрываются в открытое небо над узлом, болт доступен сбоку;
      • крутая труба (нога башни) → прорезь по ГОРИЗОНТАЛИ НАРУЖУ (от центра
        рамы) — щёки открываются на внешнюю (пустую) сторону фермы.
    place_clamp сам ортогонализует slit к оси бора, так что можно давать
    мировой +Z или радиаль-наружу свободно."""
    if abs(d[2]) < 0.5:
        return SLIT_UP
    out = np.array([node[0], node[1], 0.0])
    n = np.linalg.norm(out)
    return tuple(out / n) if n > 1e-6 else SLIT_UP


def necked_socket(node, endpoint):
    """Хомут-гнездо на КОРОТКОЙ ШЕЕ: ось бора вдоль трубы node→endpoint, воротник
    вынесен на STANDOFF в свободное пространство, прорезь смотрит в пустоту
    (slit_dir_for). Шея = стержень NECK_R от ступицы до торца воротника (заходит
    внутрь на NECK_OVER для сварки; глухой упор трубы). Возвращает union(воротник,
    шея) — воротник НЕ приваривается к соседям, только шея к ступице."""
    node = np.asarray(node, float)
    d = np.asarray(endpoint, float) - node
    d /= np.linalg.norm(d)
    standoff = STANDOFF_H if abs(d[2]) < 0.5 else STANDOFF_T
    origin = node + d * standoff
    slit = slit_dir_for(node, d)
    clamp = TC.place_clamp(CLAMP_H_SOCK, origin, tube_dir=d, slit_dir=slit)
    neck = rod(node - d * 4.0, origin + d * NECK_OVER, NECK_R)
    return clamp.union(neck)


def glide_pad(part, cx, cy):
    """Небольшой ПЛОСКИЙ пад-скользяк под ступицей: плоское дно z=NODE_BOT_Z (61),
    верх тонет в ступицу. Заменяет прежнюю curved-обрезку низа. Карман PTFE
    режется отдельно (ptfe_pocket). НЕ трогает воротники (они висят по бокам)."""
    Rp = PAD_D / 2 + 5.0                 # радиус пада (охватывает карман PTFE)
    h = FRAME_Z + 2.0 - NODE_BOT_Z       # 61..77
    pad = cyl(Rp, h, T=tr(cx, cy, (NODE_BOT_Z + FRAME_Z + 2.0) / 2))
    return part.union(pad)


def ptfe_pocket(cx, cy):
    """Резак кармана PTFE снизу + центральная бобышка-опора моста с пилотом M3.
    Возвращает (add_boss, cut_pocket, cut_pilot)."""
    z_floor = NODE_BOT_Z + PAD_DEEP
    pocket = cyl(PAD_D / 2, PAD_DEEP + 1.0, seg=64,
                 T=tr(cx, cy, NODE_BOT_Z + PAD_DEEP / 2 - 0.5))
    boss = cyl(PAD_POST_D / 2, PAD_DEEP, seg=32,
               T=tr(cx, cy, NODE_BOT_Z + PAD_DEEP / 2))
    pilot = cyl(M3_SELFTAP / 2, PILOT_DEPTH + 1, seg=24,
                T=tr(cx, cy, NODE_BOT_Z + (PILOT_DEPTH + 1) / 2 - 0.5))
    return boss, pocket, pilot


def finish(mesh, name):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    # Грубая сварка вершин ДО валидации (тела вращения хомута дают sliver-пары
    # ~5e-7 — validate их дырявит); схлопываем в честное ребро (урок azbench).
    mesh.merge_vertices(digits_vertex=5)
    mesh.process(validate=True)
    # выкинуть плавающие boolean-стружки (corner_drive давал 0.19см³ обломок) —
    # оставляем только крупнейшее тело
    parts = mesh.split(only_watertight=False)
    if len(parts) > 1:
        mesh = max(parts, key=lambda m: m.volume)
    if not mesh.is_watertight:                 # добить редкие sliver-дырки от validate
        trimesh.repair.fill_holes(mesh)
        mesh.fix_normals()
    out = OUTDIR / f"{name}.stl"
    mesh.export(out)
    bb = mesh.bounds
    print(f"  {name}.stl  watertight={mesh.is_watertight}  vol={mesh.volume/1000:.2f}cm³  "
          f"bbox={bb[1,0]-bb[0,0]:.0f}×{bb[1,1]-bb[0,1]:.0f}×{bb[1,2]-bb[0,2]:.0f}mm")
    return mesh


# ============================ ГЕОМЕТРИЯ ТРУБ ============================
def corner_xyz(ang):
    return np.array(W.polar(R_CORNER, ang, FRAME_Z), float)


def endpoints_for_corner(ang):
    """Список (метка, точка-конец) всех труб, сходящихся в угловом узле."""
    node = corner_xyz(ang)
    others = [a for a in CORNER_ANGLES if a != ang]
    eps = []
    for a in others:                                   # 2 хорды
        eps.append((f"chord→{a}°", corner_xyz(a)))
    eps.append(("radial→center", np.array([0, 0, FRAME_Z], float)))   # радиаль
    # Ноги башни: передний угол (x≠0) — ТОЛЬКО к ближнему апексу (совпадающий
    # знак X); задний угол 270° (x≈0) — к обеим вершинам. Иначе у передних
    # углов повисали пустые гнёзда к дальнему апексу (нет ответной трубы).
    for apex in APEXES:
        near = abs(node[0]) < 1.0 or (apex[0] * node[0] > 0)
        if near:
            tag = "tower→apexR" if apex[0] > 0 else "tower→apexL"
            eps.append((tag, np.array(apex, float)))
    return node, eps


# ============================ 1/2. УГЛОВОЙ УЗЕЛ ============================
def corner_node(ang, drive=False):
    """Литой угловой узел: МАЛЕНЬКАЯ ступица + до 5 хомутов НА ШЕЯХ (2 хорды,
    1 радиаль — прорезь ВВЕРХ; 2 ноги башни — прорезь наружу). Ступица соединяет
    только ШЕИ, не воротники → щёки каждого хомута сжимаются в открытом
    пространстве (см. verify: щель прорези свободна). Curved-дно убрано; снизу —
    небольшой ПЛОСКИЙ пад-скользяк z=61 с карманом PTFE.
    drive=True → задний узел 270°: добавляет ПЛОСКИЙ пад 4×M4 под Rocker_swing_base
    и радиальный проём под шестерню к венцу."""
    node, eps = endpoints_for_corner(ang)
    cx, cy = node[0], node[1]

    part = trimesh.creation.icosphere(subdivisions=ICO_SUB, radius=HUB_R)
    part.apply_translation(node)

    for _tag, ep in eps:                               # хомут на шее в каждую трубу
        part = part.union(necked_socket(node, ep))

    part = glide_pad(part, cx, cy)                      # плоский пад-скользяк снизу

    # Посадочная бобышка привода (только задний узел 270°)
    pad_cuts = []
    if drive:
        pad = box(PAD_X, PAD_Y, PAD_T, T=tr(0, PAD_CTR_Y, PAD_TOP_Z - PAD_T / 2))
        # ножка пада вниз к ступице (чтобы приварилось монолитно)
        leg = box(PAD_X, 30.0, PAD_TOP_Z - FRAME_Z + 5,
                  T=tr(0, -R_CORNER + 2, (PAD_TOP_Z + FRAME_Z - 5) / 2))
        part = part.union(pad).union(leg)
        for sx in (-1, 1):
            for sy in (-1, 1):
                hx, hy = sx * M4_DX / 2, PAD_CTR_Y + sy * M4_DY / 2
                pad_cuts.append(cyl(M4_CLR / 2, PAD_T + 2, seg=24,
                                    T=tr(hx, hy, PAD_TOP_Z - PAD_T / 2)))
                pad_cuts.append(hexprism(M4_NUT_AF, M4_NUT_DEEP + 0.5,
                                         T=tr(hx, hy, PAD_TOP_Z - PAD_T
                                              + M4_NUT_DEEP / 2 - 0.25)))
        # проём под шестерню на PINION_R (Ø36) — сквозь пад/ножку вертикально
        pad_cuts.append(cyl(PINION_CLR_D / 2, 200, seg=48,
                            T=tr(0, -PINION_R, 60)))

    boss, pocket, pilot = ptfe_pocket(cx, cy)
    part = part.union(boss)
    part = part.difference([pocket, pilot] + pad_cuts)

    part.apply_translation([-cx, -cy, -part.bounds[0, 2]])   # на стол, центр XY
    name = "Rocker_corner_drive" if drive else f"Rocker_corner_node_{int(ang)}"
    return finish(part, name)


# ============================ 3. ЦЕНТРАЛЬНЫЙ УЗЕЛ ============================
def center_node():
    """Центр вращающейся рамы: втулка Ø22 по болту M10 (бор Ø10.6), 3 радиальных
    хомута к трём углам на FRAME_Z, полка под board_holder над магнитом (чип на
    оси ~1мм над магнитом; свес на 45°-клине — печать без поддержек)."""
    from shapely.geometry import Polygon

    node = np.array([0, 0, FRAME_Z], float)

    # Ступица + втулка
    part = trimesh.creation.icosphere(subdivisions=ICO_SUB, radius=HUB_R)
    part.apply_translation(node)
    part = part.union(cyl(BUSH_OD / 2, BUSH_Z1 - BUSH_Z0,
                          T=tr(0, 0, (BUSH_Z0 + BUSH_Z1) / 2)))

    # 3 радиальных гнезда к углам (хомут на шее, прорезь ВВЕРХ в открытое небо)
    for ang in CORNER_ANGLES:
        part = part.union(necked_socket(node, corner_xyz(ang)))

    # Стойка + 45°-клин + полка под board_holder (профиль в (Y,Z), экструзия X)
    wedge_z0 = (SHELF_TOP_Z - SHELF_T) - (POST_Y_FRONT - SHELF_Y_FRONT)   # 45°
    prof = Polygon([(POST_Y_BACK, POST_Z0), (POST_Y_FRONT, POST_Z0),
                    (POST_Y_FRONT, wedge_z0),
                    (SHELF_Y_FRONT, SHELF_TOP_Z - SHELF_T),
                    (SHELF_Y_FRONT, SHELF_TOP_Z),
                    (POST_Y_BACK, SHELF_TOP_Z)])
    post = trimesh.creation.extrude_polygon(prof, height=SHELF_W)
    # локальные оси профиля (x=Y, y=Z, z=X) → мировые
    M = np.array([[0, 0, 1, -SHELF_W / 2],
                  [1, 0, 0, 0],
                  [0, 1, 0, 0],
                  [0, 0, 0, 1.0]])
    post.apply_transform(M)
    part = part.union(post)

    # Резаки: бор M10 сквозь втулку, 2 пилота M3 в полке
    cuts = [cyl(M10_BORE / 2, BUSH_Z1 - BUSH_Z0 + 40, seg=48,
                T=tr(0, 0, (BUSH_Z0 + BUSH_Z1) / 2))]
    for sx in (-1, 1):
        cuts.append(cyl(M3_SELFTAP / 2, PILOT_DEPTH + 1, seg=24,
                        T=tr(sx * PILOT_XY[0], PILOT_XY[1],
                             SHELF_TOP_Z + 1 - (PILOT_DEPTH + 1) / 2)))
    part = part.difference(cuts)

    part.apply_translation([0, 0, -part.bounds[0, 2]])       # на стол
    return finish(part, "Rocker_center_node")


# ============================ ОТЧЁТ ПО ТРУБАМ ============================
def report_tubes():
    def L(a, b):
        return float(np.linalg.norm(np.asarray(a, float) - np.asarray(b, float)))
    print("\nДлины труб (из координат концов, мм):")
    # хорды угол-угол (равносторонний треугольник R=210)
    cc = L(corner_xyz(30), corner_xyz(150))
    print(f"  хорда угол↔угол (все 3 равны): {cc:.1f}")
    print(f"  радиаль центр↔угол (все 3 равны): {L([0,0,FRAME_Z], corner_xyz(30)):.1f}")
    for ang in CORNER_ANGLES:
        node = corner_xyz(ang)
        for apex in APEXES:
            tag = "apexR(+170)" if apex[0] > 0 else "apexL(−170)"
            print(f"  нога башни {int(ang):>3}°→{tag}: {L(node, apex):.1f}")


def main():
    print("Генерация фермы нижнего кольца вращающейся рамы…")
    print(f"  углы {CORNER_ANGLES} на R{R_CORNER}, ось труб z={FRAME_Z}; "
          f"вершины башен ±{WHEEL_X},0,{APEX_Z}; бор хомута Ø{BORE_D} (труба Ø22)")
    corner_node(30)
    corner_node(150)
    corner_node(270, drive=True)
    center_node()
    report_tubes()
    print(f"\nГотово → {OUTDIR}")
    print("Количества: угловой узел ×2 (30°,150°), приводной узел ×1 (270°), "
          "центральный узел ×1.")


if __name__ == "__main__":
    main()
