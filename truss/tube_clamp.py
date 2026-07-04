#!/usr/bin/env python3
"""
tube_clamp — ПЕРЕИСПОЛЬЗУЕМЫЙ модуль (НЕ самостоятельный генератор STL).

Оборачивает ПРОВЕРЕННЫЙ хомут сына (incoming/son_tube_clamp.stl) — раздвижной
разрезной хомут (split-collar) под трубу Ø22 алюминий:
  • бор Ø22 (ручки-защёлки труб зажимаются в нём),
  • прорезь (пропил) к проушине, поперечный прижимной болт стягивает щёки,
  • призматический профиль ВДОЛЬ оси бора (постоянное сечение).
Другие генераторы узлов (пауки, гнёзда, лапы) ИМПОРТИРУЮТ этот модуль и
приваривают (union) хомут к своим телам через place_clamp(). Новый хомут НЕ
изобретаем — берём ровно этот профиль сына.

Геометрия определяется ПО МЕШУ (не хардкод):
  1) ось бора  — призматическая ось (мин. дисперсия площади сечения) +
     подгонка окружности Ø22 по вертикальным внутренним граням (Каса + отсев);
  2) направление прорези/проушины — от центра бора к центру прижимного болта;
  3) самопроверка: печатаем измеренные Ø бора и Ø болта.
Затем меш переориентируется в КАНОН: ось бора через (0,0,z) вдоль +Z, бор в
центре XY, прорезь смотрит на +X, низ на z=0. Профиль призматичен (проверка
CV сечения на плато < 2%). Обрезается до CLAMP_H (по умолч. 46) Z-боксом,
центрированным на прижимном болте (сохраняем бор+прорезь+проушину+болт).

ОРИЕНТАЦИЯ ПЕЧАТИ канонического хомута: ось бора вертикальна (+Z) → бор
печатается вертикальным отверстием без поддержек; поперечный прижимной болт
мостится (bridging) — это ПРОВЕРЕННАЯ печать сына, профиль не трогаем.

ЗАМЕР (см. self-check при импорте): бор ≈ Ø21.9 (номинал Ø22, ручки труб
входят), прижимной болт — сквозняк ≈ Ø6.2 + зенковка ≈ Ø8.8 под головку, т.е.
это M5/M6 винт с цил. головкой, а НЕ M4/Ø4.4 из брифа. Мы переиспользуем
профиль как есть (отверстие уже в меше, заново НЕ сверлим), поэтому посадка
болта уже задана сыном.

API:
  clamp_mesh(height=CLAMP_H)                      -> trimesh (канон)
  place_clamp(height, origin, tube_dir, slit_dir) -> trimesh (размещённый)
  BORE_D, BOLT_D, CLAMP_OD, CLAMP_H               -> константы (мм)
"""
import math
from pathlib import Path

import numpy as np
import trimesh

# ============================ ПАРАМЕТРЫ ============================
SRC = Path(__file__).parent / "incoming" / "son_tube_clamp.stl"
OUTDIR = Path(__file__).parent / "stl"

CLAMP_H = 46.0          # высота канонического хомута по умолчанию, мм (85→46)
BORE_NOM = 22.0         # номинальный Ø бора под трубу, мм (для сверки)
FIT_TOL = 1.5           # допуск отсева при подгонке окружности бора, мм
PRISM_CV_MAX = 2.0      # макс. CV площади сечения на плато, % (условие призмы)

SEC_N = 24              # точек по Z при поиске профиля/болта
CIRC_SEG = 96           # фасеты цилиндров демо-пластины


# ============================ ХЕЛПЕРЫ ============================
def _circle_fit_kasa(pts):
    """Алгебраическая подгонка окружности (Каса) по точкам Nx2 → (cx,cy,R)."""
    x, y = pts[:, 0], pts[:, 1]
    A = np.c_[2 * x, 2 * y, np.ones(len(x))]
    b = x ** 2 + y ** 2
    c, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = c[0], c[1]
    return cx, cy, math.sqrt(max(c[2] + cx ** 2 + cy ** 2, 0.0))


def _prismatic_axis(mesh):
    """Ось с минимальным CV площади поперечного сечения → индекс оси (0/1/2)."""
    best, best_cv = 2, 1e9
    for ax in range(3):
        lo, hi = mesh.bounds[0, ax], mesh.bounds[1, ax]
        n = [0, 0, 0]; n[ax] = 1
        areas = []
        for t in np.linspace(lo + 2, hi - 2, SEC_N):
            o = [0, 0, 0]; o[ax] = t
            sec = mesh.section(plane_origin=o, plane_normal=n)
            if sec is None:
                continue
            areas.append(sec.to_2D()[0].area)
        areas = np.array(areas)
        if len(areas) < 3:
            continue
        cv = areas.std() / areas.mean() * 100
        if cv < best_cv:
            best, best_cv = ax, cv
    return best, best_cv


def _fit_bore(mesh, axis):
    """Подгонка окружности бора по вертикальным внутренним граням (⟂ оси)."""
    a, b = [i for i in range(3) if i != axis]   # плоскостные оси
    fn, fc = mesh.face_normals, mesh.triangles_center
    wall = np.abs(fn[:, axis]) < 0.2            # стенки, параллельные оси
    P, N = fc[wall][:, [a, b]], fn[wall][:, [a, b]]
    ctr = P.mean(0)
    to = ctr - P
    to /= np.linalg.norm(to, axis=1, keepdims=True) + 1e-9
    inward = (N * to).sum(1) > 0.5              # нормаль смотрит внутрь → бор
    Q = P[inward]
    for _ in range(6):                          # робастный отсев наружной стенки
        cx, cy, R = _circle_fit_kasa(Q)
        d = np.hypot(Q[:, 0] - cx, Q[:, 1] - cy)
        keep = np.abs(d - R) < FIT_TOL
        if keep.sum() < 10:
            break
        Q = Q[keep]
    return cx, cy, R, a, b


def _area_profile(mesh, axis):
    """(z, area) вдоль оси; для поиска болта (провал) и плато (константа)."""
    lo, hi = mesh.bounds[0, axis], mesh.bounds[1, axis]
    zs = np.linspace(lo + 1, hi - 1, 40)
    out = []
    for t in zs:
        o = [0, 0, 0]; o[axis] = t
        sec = mesh.section(plane_origin=o, plane_normal=[int(i == axis) for i in range(3)])
        out.append((t, sec.to_2D()[0].area if sec is not None else 0.0))
    return np.array(out)


# ============================ АНАЛИЗ ИСХОДНИКА ============================
def _analyze():
    """Разобрать хомут сына → канонический меш + замеры. Возвращает dict."""
    raw = trimesh.load(SRC, process=False)

    axis, axis_cv = _prismatic_axis(raw)
    cx, cy, R, pa, pb = _fit_bore(raw, axis)

    prof = _area_profile(raw, axis)
    z = prof[:, 0]; area = prof[:, 1]
    plateau = np.median(area)
    # плато = сечения близко к медиане (без торцевых фасок и провала болта)
    on_plateau = area > 0.95 * plateau
    plat_cv = area[on_plateau].std() / area[on_plateau].mean() * 100
    # прижимной болт = минимум площади во внутренней трети (не на торцах)
    inner = (z > raw.bounds[0, axis] + 0.25 * (raw.bounds[1, axis] - raw.bounds[0, axis])) & \
            (z < raw.bounds[1, axis] - 0.25 * (raw.bounds[1, axis] - raw.bounds[0, axis]))
    bolt_z = z[inner][np.argmin(area[inner])]

    # направление прорези: от центра бора к центру провала болта в плоскости XY
    o = [0, 0, 0]; o[axis] = bolt_z
    sec = raw.section(plane_origin=o, plane_normal=[int(i == axis) for i in range(3)])
    p2, T2 = sec.to_2D()
    R2, t2 = T2[:3, :3], T2[:3, 3]
    # центроид самых удалённых от бора кусков (щёки проушины) — задаёт прорезь
    pts3 = []
    for poly in p2.polygons_full:
        c = poly.centroid
        pts3.append(R2 @ np.array([c.x, c.y, 0]) + t2)
    pts3 = np.array(pts3)
    bore_ctr3 = np.zeros(3); bore_ctr3[pa] = cx; bore_ctr3[pb] = cy
    far = pts3[np.argmax(np.linalg.norm(pts3 - bore_ctr3, axis=1))]
    slit_vec = np.array([far[pa] - cx, far[pb] - cy])
    slit_vec /= np.linalg.norm(slit_vec)

    # диаметр сквозного отверстия болта: сечение вдоль оси прорези сквозь щёку
    bolt_d = _measure_bolt(raw, axis, pa, pb, cx, cy, slit_vec, bolt_z, R)

    # ---- переориентация в КАНОН ----
    m = raw.copy()
    # 1) ось бора → +Z: переставить оси так, чтобы 'axis'→Z, (pa,pb)→(X,Y)
    perm = [pa, pb, axis]
    M = np.eye(4); M[:3, :3] = np.eye(3)[perm]      # строки-перестановка
    m.apply_transform(M)
    # правая тройка (если перестановка дала отражение — зеркалим Y назад)
    if np.linalg.det(M[:3, :3]) < 0:
        F = np.eye(4); F[1, 1] = -1; m.apply_transform(F)
    # 2) центр бора → (0,0), низ → z=0
    m.apply_translation([-cx, -cy, -m.bounds[0, 2]])
    # 3) прорезь → +X (поворот вокруг Z)
    ang = -math.atan2(slit_vec[1], slit_vec[0])
    m.apply_transform(trimesh.transformations.rotation_matrix(ang, [0, 0, 1]))
    # довести до чистого объёма (исходник грузили process=False)
    m.merge_vertices()
    m.process(validate=True)
    m.fix_normals()

    return dict(mesh=m, bore_d=2 * R, bolt_d=bolt_d, bolt_z=bolt_z - raw.bounds[0, axis],
                plateau_cv=plat_cv, axis_cv=axis_cv, plateau_area=plateau,
                total_h=raw.bounds[1, axis] - raw.bounds[0, axis])


def _measure_bolt(mesh, axis, pa, pb, cx, cy, slit_vec, bolt_z, bore_R):
    """Ø сквозного отверстия прижимного болта: сечения ⟂ ОСИ БОЛТА в щеке.
    Ось болта = bore_dir × slit_dir (болт стягивает щёки поперёк прорези)."""
    from shapely.geometry import Polygon
    sd = np.zeros(3); sd[pa], sd[pb] = slit_vec        # направление прорези
    ez = np.zeros(3); ez[axis] = 1.0                   # ось бора
    baxis = np.cross(ez, sd)                            # ось болта
    baxis /= np.linalg.norm(baxis) + 1e-9
    zc = np.zeros(3); zc[axis] = bolt_z
    bc = np.zeros(3); bc[pa], bc[pb] = cx, cy
    best = None
    offs = np.r_[np.arange(-9.0, -2.0, 0.5), np.arange(2.0, 9.5, 0.5)]  # обе щеки
    for off in offs:                                   # шаг вдоль оси болта
        p0 = bc + zc + baxis * off
        sec = mesh.section(plane_origin=p0, plane_normal=baxis)
        if sec is None:
            continue
        p2, _ = sec.to_2D()
        for poly in p2.polygons_full:
            for ring in poly.interiors:
                pr = Polygon(ring)
                if pr.area < 2:
                    continue
                d = 2 * math.sqrt(pr.area / math.pi)
                if best is None or d < best:           # сквозняк = наименьший Ø
                    best = d
    return best if best else float('nan')


# ============================ КОНСТАНТЫ + САМОПРОВЕРКА ============================
_A = _analyze()
_CANON = _A["mesh"]                              # канонический меш (0..total_h)
_BOLT_Z = _A["bolt_z"]                           # высота оси болта от низа, мм

BORE_D = round(_A["bore_d"], 2)                  # измеренный Ø бора, мм
BOLT_D = round(_A["bolt_d"], 2)                  # измеренный Ø сквозняка болта, мм
_bb = _CANON.bounds
# CLAMP_OD = диаметр воротника ⟂ прорези (по Y канона); по X добавляет проушину
CLAMP_OD = round(float(_bb[1, 1] - _bb[0, 1]), 1)   # габарит воротника ⟂ прорези, мм
_SLIT_SPAN = round(float(_bb[1, 0] - _bb[0, 0]), 1)  # габарит вдоль прорези (с проушиной), мм


def _selfcheck():
    print("tube_clamp self-check (замер по мешу сына):")
    print(f"  бор Ø{BORE_D} мм (номинал Ø{BORE_NOM}) — {'OK' if abs(BORE_D-BORE_NOM)<1 else 'ОТКЛОНЕНИЕ'}")
    print(f"  прижимной болт: сквозняк Ø{BOLT_D} мм  (это M5/M6, НЕ M4/Ø4.4)")
    print(f"  ось болта z={_BOLT_Z:.1f} мм от низа; профиль призмат.: CV плато={_A['plateau_cv']:.2f}% "
          f"({'OK <'+str(PRISM_CV_MAX)+'%' if _A['plateau_cv']<PRISM_CV_MAX else 'НЕ призма'})")
    print(f"  воротник CLAMP_OD={CLAMP_OD} мм ⟂ прорези; вдоль прорези (с проушиной) "
          f"{_SLIT_SPAN} мм; полная высота исходника {_A['total_h']:.0f} мм")


# ============================ ПУБЛИЧНОЕ API ============================
def clamp_mesh(height=CLAMP_H):
    """Канонический хомут: бор вдоль +Z в (0,0), прорезь на +X, низ z=0.
    Обрезан Z-боксом высотой `height`, центрированным на прижимном болте
    (сохраняем бор+прорезь+проушину+болт). Возвращает watertight trimesh."""
    m = _CANON.copy()
    total = m.bounds[1, 2] - m.bounds[0, 2]
    if height >= total:
        return m
    z0 = _BOLT_Z - height / 2.0                  # окно вокруг болта
    z0 = min(max(z0, 0.0), total - height)       # не вылезать за исходник
    span = max(_SLIT_SPAN, CLAMP_OD) * 2 + 20    # заведомо шире профиля в XY
    box = trimesh.creation.box(extents=(span, span, height))
    box.apply_translation([0, 0, z0 + height / 2.0])
    out = m.intersection(box)
    out.apply_translation([0, 0, -out.bounds[0, 2]])   # низ → z=0
    return out


def place_clamp(height, origin, tube_dir, slit_dir):
    """Разместить хомут так, чтобы ось бора шла через `origin` вдоль `tube_dir`,
    прорезь смотрела на `slit_dir`. `origin` = точка на оси бора у нижнего торца
    хомута. tube_dir/slit_dir — векторы (нормируются, slit ортогонализуется).
    Возвращает трансформированный trimesh (для union с телом узла)."""
    origin = np.asarray(origin, float)
    z_ax = np.asarray(tube_dir, float); z_ax /= np.linalg.norm(z_ax)
    x_ax = np.asarray(slit_dir, float)
    x_ax = x_ax - np.dot(x_ax, z_ax) * z_ax      # ортогонализация к оси бора
    x_ax /= np.linalg.norm(x_ax)
    y_ax = np.cross(z_ax, x_ax)                  # правая тройка
    T = np.eye(4)
    T[:3, 0] = x_ax                              # +X_локал (прорезь) → slit_dir
    T[:3, 1] = y_ax
    T[:3, 2] = z_ax                              # +Z_локал (бор) → tube_dir
    T[:3, 3] = origin
    m = clamp_mesh(height)
    m.apply_transform(T)
    return m


# ============================ ДЕМО ============================
def _finish(mesh, name):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    mesh.process(validate=True)
    out = OUTDIR / f"{name}.stl"
    mesh.export(out)
    bb = mesh.bounds
    print(f"  {name}.stl  watertight={mesh.is_watertight}  vol={mesh.volume/1000:.2f}cm³  "
          f"bbox={bb[1,0]-bb[0,0]:.0f}×{bb[1,1]-bb[0,1]:.0f}×{bb[1,2]-bb[0,2]:.0f}mm")
    return mesh


def _demo():
    """Три хомута сына на болванке-пластине под 0/120/240° радиально —
    доказательство, что place_clamp() приваривает профиль в любой позе."""
    Rc = 60.0                                    # радиус расстановки хомутов
    plate = trimesh.creation.cylinder(radius=Rc + CLAMP_OD / 2 + 6, height=8, sections=CIRC_SEG)
    plate.apply_translation([0, 0, 4])           # верх пластины z=8
    part = plate
    for deg in (0.0, 120.0, 240.0):
        a = math.radians(deg)
        radial = np.array([math.cos(a), math.sin(a), 0.0])
        origin = np.array([Rc * math.cos(a), Rc * math.sin(a), 8.0])
        # трубы стоят вертикально (+Z), прорезь смотрит радиально наружу
        c = place_clamp(CLAMP_H, origin, tube_dir=[0, 0, 1], slit_dir=radial)
        part = part.union(c)
    return _finish(part, "_clamp_demo")


if __name__ == "__main__":
    _selfcheck()
    print("Демо: 3 хомута на пластине (0/120/240°)…")
    _demo()
    print(f"\nГотово → {OUTDIR}")
else:
    _selfcheck()
