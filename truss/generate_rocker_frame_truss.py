#!/usr/bin/env python3
"""
Нижнее кольцо ВРАЩАЮЩЕЙСЯ рамы рокера как ферма «трубы + узлы» — МИНИМАЛЬНЫЙ
стиль, ТОПОЛОГИЯ v3 (эталон truss/_proto_reference.py, одобрен пользователем,
показаны и приняты все 3 типа узлов).

ИЗМЕНЕНИЕ ТОПОЛОГИИ (v3): вращающаяся рама больше НЕ «углы с радиалями к центру».
Теперь:
  • 3 УГЛОВЫХ узла (30/150/270°): ТОЛЬКО 2 хорды к соседним углам (под 60°) +
    нога(и) башни к ближней(им) вершине(ам). НИКАКОЙ радиали к центру.
  • 3 узла СЕРЕДИНЫ ХОРДЫ (середины AB, BC, CA): хорда проходит как 2 полухорды
    (коллинеарно, 180°) + 1 радиаль к центру (90°).
  • 1 ЦЕНТРАЛЬНЫЙ узел: 3 радиали к 3 СЕРЕДИНАМ хорд (120°) + втулка M10 +
    полка энкодера.
→ в каждом узле трубы разнесены ≥60°, разрезные хомуты не сливаются в кашу.

Каждый узел = union ЧИСТЫХ разрезных цилиндров-хомутов (tube_clamp.place_clamp,
бор Ø22.4 + стенка 4 → воротник Ø≈30.4, щель на +X, проушины M5, БОЛТ у НАРУЖНОГО
(входного) торца воротника, где труба точно внутри) + МАЛЕНЬКОЕ ядро (сфера /
втулка), ровно чтобы сварить их водонепроницаемо, + ТОЛЬКО функциональные детали.
Хомуты выходят прямо из ядра (origin = узел): труба вставляется в воротник до
упора в ядро (глухой упор).

Щель хомута смотрит в СВОБОДНОЕ пространство: горизонтальные трубы (хорды,
полухорды, радиали) — щель строго ВВЕРХ (+Z); крутые ноги башни — щель по
ГОРИЗОНТАЛИ НАРУЖУ (от центра рамы).

Мир (мм, z=0 = верх грунт-доски) ИМПОРТИРУЕТСЯ из gen_rocker_comic (НЕ хардкод):
CORNER_ANGLES=(30,150,270), R_CORNER=210, FRAME_Z=75 (ось труб рамы),
WHEEL_X=170, APEX_Z=530 (вершины башен ±170,0,530), PINION_R=240. Все направления
труб СЧИТАЮТСЯ из координат концов.

Детали:
  1. Rocker_corner_node_30.stl / _150.stl (зеркальная пара) — ядро-сфера + 2
     хорды (к двум соседним углам, щель ВВЕРХ) + 1 нога башни к ближней вершине
     (30→apexR, 150→apexL; щель НАРУЖУ). НИКАКОЙ радиали. Больше ничего.
  2. Rocker_corner_drive.stl (270°) — 2 хорды + 2 ноги башни (270° кормит обе
     вершины) + МИНИМАЛЬНЫЙ плоский пад 4×M4 под Rocker_swing_base и вертикальный
     проём Ø40 под шестерню к венцу на PINION_R. НИКАКОЙ радиали.
  3. Rocker_midchord_node.stl (×3 идентичных — одна деталь, печатается 3×) —
     в середине хорды: 2 полухорды коллинеарно (180°) + 1 радиаль к центру (90°),
     щель ВВЕРХ. Малое ядро. Три середины симметричны поворотом на 120° вокруг Z
     (радиаль ⟂ хорде — перпендикуляр к хорде из равноудалённого центра), поэтому
     ОДНА деталь обслуживает все три.
  4. Rocker_center_node.stl — втулка по оси M10 (бор Ø10.6) + 3 радиальных хомута
     к 3 СЕРЕДИНАМ хорд (120°) + МИНИМАЛЬНАЯ полка энкодера (стойка+таб в свободном
     секторе 270°, 2×M3 холдера AS5048A, чип на оси над магнитом), в стороне от щелей.

ОРИЕНТАЦИЯ ПЕЧАТИ (проектируем в мировых координатах, чтобы оси труб стыковались,
затем разворачиваем каждую деталь в естественную позу печати, z_min=0):
  • Rocker_corner_node/drive: разворот вокруг Z (наружу-радиаль угла → +X). Стол =
    низ горизонтальных воротников хорд (боры Ø22 горизонтальны, мостятся по верху,
    щель вверх); воротники ног башни и приводной пад/проём смотрят вверх.
  • Rocker_midchord_node: все три трубы горизонтальны и копланарны (z=75) → деталь
    плоская. Разворот вокруг Z (радиаль → −X). Плоский низ на стол, боры мостятся,
    щели вверх.
  • Rocker_center_node: без разворота — втулка стоит вертикально, её плоский НИЗ
    на столе (бор M10 вертикален), радиальные хомуты горизонтальны (мост),
    стойка+таб полки уходят вверх (лёгкий свес) в секторе −Y (270°).
"""
import math
from pathlib import Path

import numpy as np
import trimesh

import gen_rocker_comic as W            # общий мир (координаты, polar) — НЕ хардкод
import tube_clamp as TC                 # чистый параметрический хомут + place_clamp

# ============================ ПАРАМЕТРЫ ============================
# --- Мир (из gen_rocker_comic) ---
CORNER_ANGLES = W.CORNER_ANGLES         # (30, 150, 270)
R_CORNER = W.R_CORNER                   # 210
FRAME_Z = W.FRAME_Z                     # 75  (ось труб вращающейся рамы)
WHEEL_X = W.WHEEL_X                     # 170
APEX_Z = W.APEX_Z                       # 530
PINION_R = W.PINION_R                   # 240
APEX_R = np.array([WHEEL_X, 0.0, APEX_Z], float)     # правая вершина (+X)
APEX_L = np.array([-WHEEL_X, 0.0, APEX_Z], float)    # левая вершина (−X)
CENTER = np.array([0.0, 0.0, FRAME_Z], float)

# Ноги башни по углам (из gen_rocker_comic::towers): 30→apexR, 150→apexL,
# 270→обе вершины.
TOWER_LEGS = {30: [APEX_R], 150: [APEX_L], 270: [APEX_R, APEX_L]}

# --- Хомут (чистый разрезной цилиндр из tube_clamp) ---
CLAMP_H = 40.0          # высота воротника вдоль оси трубы, мм
BORE_D = TC.BORE_D      # Ø бора ≈ 22.4 (труба Ø22 + зазор)
CLAMP_OD = TC.CLAMP_OD  # наружный Ø воротника ≈ 30.4
SLIT_UP = (0.0, 0.0, 1.0)   # щель ВВЕРХ для горизонтальных труб

# --- Минимальное ядро узла ---
HUB_R = 15.0            # радиус ядра-сферы: хомуты выходят из него, труба
                        #   упирается в ядро (глухой упор)
ICO_SUB = 3             # подразбиение икосферы ядра

# --- Привод (узел 270°): минимальный пад 4×M4 + проём под шестерню ---
PAD_X = 56.0            # пад под Rocker_swing_base, X
PAD_Y = 62.0            # пад, Y (тянется наружу к PINION_R)
PAD_T = 8.0             # толщина пада
PAD_TOP_Z = 83.0        # верх пада (низ плиты swing_base здесь)
PAD_CTR_Y = -206.0      # центр пада по Y (у узла 270°, C=(0,−210))
M4_CLR = 4.4            # сквозной M4
M4_NUT_AF = 7.0         # гайка M4 «под ключ» (hex)
M4_NUT_DEEP = 3.2       # глубина hex-кармана гайки
M4_DX = 44.0            # 4×M4: размах по X (болты ±22)
M4_DY = 20.0            # 4×M4: размах по Y (±10)
PINION_CLR_D = 40.0     # вертикальный проём под шестерню на PINION_R

# --- Центр: втулка по оси M10 ---
BUSH_OD = 22.0          # Ø втулки
M10_BORE = 10.6         # бор по гладкому хвостовику M10
BUSH_Z0 = 50.0          # низ втулки (плоский стол)
BUSH_Z1 = 110.0         # верх втулки

# --- Полка энкодера AS5048A (минимальная: стойка + таб), сектор −Y (270°) ---
MAG_TOP_Z = 130.0       # верх колпачка магнита на болте (мир)
AIR_GAP = 1.0           # зазор магнит↔чип
CHIP_T = 1.1            # корпус чипа AS5048A над платой
BRD_T = 1.6             # толщина платы
HLD_BOSS_H = 3.0        # бобышки board_holder
SHELF_TOP_Z = MAG_TOP_Z + AIR_GAP + CHIP_T + BRD_T + HLD_BOSS_H   # ≈136.7
SHELF_T = 6.0           # толщина таба полки
SHELF_W = 28.0          # ширина стойки/таба по X (= лапка холдера)
TAB_CY = -12.0          # центр таба по Y (кроет ось и пилоты), сектор −Y
TAB_DY = 36.0           # глубина таба по Y (−30..+6, кроет ось)
POST_CY = -14.0         # центр стойки по Y (−Y сторона, свободный сектор 270°)
POST_DY = 32.0          # глубина стойки по Y (−30..+2 → варится с втулкой)
POST_Z0 = 90.0          # низ стойки (над воротниками, тонет во втулку z≤110)
M3_SELFTAP = 2.7        # пилот M3 холдера
PILOT_XY = (10.0, -15.5)    # 2 пилота M3 холдера: ±x, −y (чип оказывается на оси)
PILOT_DEPTH = 8.0

SEG = 96
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
    from shapely.geometry import Polygon
    r = af / math.cos(math.radians(30)) / 2.0
    angs = np.radians(np.arange(6) * 60 + 30)
    pts = np.c_[r * np.cos(angs), r * np.sin(angs)]
    m = trimesh.creation.extrude_polygon(Polygon(pts), height=h)
    if T is not None:
        m.apply_transform(T)
    return m


def slit_for(node, d):
    """Щель В СВОБОДНОЕ пространство: горизонтальная труба (|dz|<0.5) → ВВЕРХ;
    крутая труба (нога башни) → по ГОРИЗОНТАЛИ НАРУЖУ от центра рамы."""
    if abs(d[2]) < 0.5:
        return SLIT_UP
    out = np.array([node[0], node[1], 0.0])
    n = np.linalg.norm(out)
    return tuple(out / n) if n > 1e-6 else SLIT_UP


def clamp_toward(node, endpoint, height=CLAMP_H):
    """Разместить чистый хомут: ось бора node→endpoint, нижний торец в узле
    (труба входит в воротник до упора в ядро), щель — в пустоту (slit_for).
    (эталон: _proto_reference.py::place)"""
    node = np.asarray(node, float)
    d = np.asarray(endpoint, float) - node
    d /= np.linalg.norm(d)
    return TC.place_clamp(height, node, tube_dir=d, slit_dir=slit_for(node, d))


def to_bed(part, T=None):
    """Развернуть в позу печати (опц. T), затем центрировать по XY и опустить
    z_min=0 на стол."""
    if T is not None:
        part.apply_transform(T)
    b = part.bounds
    part.apply_translation([-(b[0, 0] + b[1, 0]) / 2,
                            -(b[0, 1] + b[1, 1]) / 2,
                            -b[0, 2]])
    return part


def finish(mesh, name):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    # Грубая сварка вершин ДО валидации (тела вращения дают sliver-пары ~5e-7 —
    # validate их дырявит); схлопываем в честное ребро.
    mesh.merge_vertices(digits_vertex=5)
    mesh.process(validate=True)
    # выкинуть плавающие boolean-стружки — оставляем только крупнейшее тело
    parts = mesh.split(only_watertight=False)
    if len(parts) > 1:
        mesh = max(parts, key=lambda m: m.volume)
    if not mesh.is_watertight:
        trimesh.repair.fill_holes(mesh)
        mesh.fix_normals()
    out = OUTDIR / f"{name}.stl"
    mesh.export(out)
    bb = mesh.bounds
    print(f"  {name}.stl  watertight={mesh.is_watertight}  bodies={len(parts)}  "
          f"vol={mesh.volume/1000:.2f}cm³  "
          f"bbox={bb[1,0]-bb[0,0]:.0f}×{bb[1,1]-bb[0,1]:.0f}×{bb[1,2]-bb[0,2]:.0f}mm")
    return mesh


# ============================ ГЕОМЕТРИЯ ТРУБ ============================
def corner_xyz(ang):
    return np.array(W.polar(R_CORNER, ang, FRAME_Z), float)


def chord_mid(ang_a, ang_b):
    return (corner_xyz(ang_a) + corner_xyz(ang_b)) / 2.0


def endpoints_for_corner(ang):
    """(v3) Трубы углового узла: 2 хорды к соседним углам + нога(и) башни.
    НИКАКОЙ радиали к центру."""
    node = corner_xyz(ang)
    others = [a for a in CORNER_ANGLES if a != ang]
    eps = [(f"chord→{a}°", corner_xyz(a)) for a in others]        # 2 хорды (60°)
    for apex in TOWER_LEGS[ang]:                                  # нога(и) башни
        tag = "tower→apexR" if apex[0] > 0 else "tower→apexL"
        eps.append((tag, apex))
    return node, eps


# ============================ 1/2. УГЛОВОЙ УЗЕЛ ============================
def corner_node(ang, drive=False):
    """(v3) Минимальный угловой узел: ядро-сфера + 2 хорды (щель вверх) +
    нога(и) башни (щель наружу). БЕЗ радиали. drive=True → узел 270°:
    + минимальный пад 4×M4 под Rocker_swing_base и вертикальный проём Ø40 под
    шестерню. Ничего лишнего."""
    node, eps = endpoints_for_corner(ang)

    part = trimesh.creation.icosphere(subdivisions=ICO_SUB, radius=HUB_R)
    part.apply_translation(node)
    for _tag, ep in eps:
        part = part.union(clamp_toward(node, ep))

    cuts = []
    if drive:
        pad = box(PAD_X, PAD_Y, PAD_T, tr(0, PAD_CTR_Y, PAD_TOP_Z - PAD_T / 2))
        leg = box(PAD_X, 30.0, PAD_TOP_Z - FRAME_Z + 5,
                  tr(0, -R_CORNER + 2, (PAD_TOP_Z + FRAME_Z - 5) / 2))
        part = part.union(pad).union(leg)
        for sx in (-1, 1):
            for sy in (-1, 1):
                hx, hy = sx * M4_DX / 2, PAD_CTR_Y + sy * M4_DY / 2
                cuts.append(cyl(M4_CLR / 2, PAD_T + 2, seg=24,
                                T=tr(hx, hy, PAD_TOP_Z - PAD_T / 2)))
                cuts.append(hexprism(M4_NUT_AF, M4_NUT_DEEP + 0.5,
                                     T=tr(hx, hy, PAD_TOP_Z - PAD_T
                                          + M4_NUT_DEEP / 2 - 0.25)))
        cuts.append(cyl(PINION_CLR_D / 2, 200, seg=48, T=tr(0, -PINION_R, 60)))

    if cuts:
        part = part.difference(cuts)

    # поза печати: развернуть вокруг Z (наружу-радиаль угла → +X)
    yaw = trimesh.transformations.rotation_matrix(math.radians(-ang), [0, 0, 1])
    part = to_bed(part, yaw)
    name = "Rocker_corner_drive" if drive else f"Rocker_corner_node_{int(ang)}"
    return finish(part, name)


# ============================ 3. СЕРЕДИНА ХОРДЫ ============================
def midchord_node():
    """(v3) Узел середины хорды (эталон — середина хорды 30–150 = AB): 2 полухорды
    коллинеарно к A и к B (180°) + 1 радиаль к центру (90°), все щели ВВЕРХ.
    Три середины хорд симметричны поворотом на 120° вокруг Z (радиаль — перпендикуляр
    к хорде из равноудалённого центра) → одна деталь печатается 3×."""
    m = chord_mid(30, 150)
    eps = [("half→30°", corner_xyz(30)),
           ("half→150°", corner_xyz(150)),
           ("radial→center", CENTER)]

    part = trimesh.creation.icosphere(subdivisions=ICO_SUB, radius=HUB_R)
    part.apply_translation(m)
    for _tag, ep in eps:
        part = part.union(clamp_toward(m, ep))

    # поза печати: развернуть вокруг Z так, что радиаль-к-центру → −X.
    # радиаль mAB→центр = (0,−1,0); yaw −90° переводит −Y → −X.
    yaw = trimesh.transformations.rotation_matrix(math.radians(-90), [0, 0, 1])
    part = to_bed(part, yaw)
    return finish(part, "Rocker_midchord_node")


# ============================ 4. ЦЕНТРАЛЬНЫЙ УЗЕЛ ============================
def center_node():
    """(v3) Минимальный центр: ядро-втулка по оси M10 (бор Ø10.6) + 3 радиальных
    хомута к 3 СЕРЕДИНАМ хорд (120°, щель вверх) + минимальная полка энкодера
    (стойка+таб в свободном секторе −Y, 2×M3, чип на оси над магнитом). Без арок."""
    node = CENTER
    mids = [chord_mid(30, 150), chord_mid(150, 270), chord_mid(270, 30)]

    part = trimesh.creation.icosphere(subdivisions=ICO_SUB, radius=HUB_R)
    part.apply_translation(node)
    part = part.union(cyl(BUSH_OD / 2, BUSH_Z1 - BUSH_Z0,
                          T=tr(0, 0, (BUSH_Z0 + BUSH_Z1) / 2)))

    for m in mids:                                    # 3 радиали к серединам хорд
        part = part.union(clamp_toward(node, m))

    # полка энкодера: стойка (−Y, вне щелей/радиалей) + горизонтальный таб над осью
    post = box(SHELF_W, POST_DY, SHELF_TOP_Z - POST_Z0,
               tr(0, POST_CY, (POST_Z0 + SHELF_TOP_Z) / 2))
    tab = box(SHELF_W, TAB_DY, SHELF_T, tr(0, TAB_CY, SHELF_TOP_Z - SHELF_T / 2))
    part = part.union(post).union(tab)

    cuts = [cyl(M10_BORE / 2, BUSH_Z1 - BUSH_Z0 + 40, seg=48,
                T=tr(0, 0, (BUSH_Z0 + BUSH_Z1) / 2))]
    for sx in (-1, 1):
        cuts.append(cyl(M3_SELFTAP / 2, PILOT_DEPTH + 1, seg=24,
                        T=tr(sx * PILOT_XY[0], PILOT_XY[1],
                             SHELF_TOP_Z + 1 - (PILOT_DEPTH + 1) / 2)))
    part = part.difference(cuts)

    part = to_bed(part)        # втулка вертикальна, плоский низ на стол
    return finish(part, "Rocker_center_node")


# ============================ ОТЧЁТ ПО ТРУБАМ ============================
def report_tubes():
    def L(a, b):
        return float(np.linalg.norm(np.asarray(a, float) - np.asarray(b, float)))
    print("\nСегменты труб этой топологии (из координат концов, мм):")
    print(f"  полухорда угол→середина (все 6 равны): "
          f"{L(corner_xyz(30), chord_mid(30, 150)):.1f}")
    print(f"  радиаль центр→середина хорды (все 3 равны): "
          f"{L(CENTER, chord_mid(30, 150)):.1f}")
    print(f"  (полная хорда угол↔угол = 2×полухорды: "
          f"{L(corner_xyz(30), corner_xyz(150)):.1f})")
    for ang in CORNER_ANGLES:
        node = corner_xyz(ang)
        for apex in TOWER_LEGS[ang]:
            tag = "apexR(+170)" if apex[0] > 0 else "apexL(−170)"
            print(f"  нога башни {int(ang):>3}°→{tag}: {L(node, apex):.1f}")


def main():
    print("Генерация фермы нижнего кольца вращающейся рамы (v3, минимальный стиль)…")
    print(f"  углы {CORNER_ANGLES} на R{R_CORNER}, ось труб z={FRAME_Z}; "
          f"вершины башен ±{WHEEL_X},0,{APEX_Z}; бор хомута Ø{BORE_D} воротник Ø{CLAMP_OD}")
    corner_node(30)
    corner_node(150)
    corner_node(270, drive=True)
    midchord_node()
    center_node()
    report_tubes()
    print(f"\nГотово → {OUTDIR}")
    print("Количества: угловой узел ×2 (30°,150°), приводной узел ×1 (270°), "
          "середина хорды ×3 (одна деталь), центральный узел ×1.")


if __name__ == "__main__":
    main()
