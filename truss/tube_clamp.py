#!/usr/bin/env python3
"""
tube_clamp — ПЕРЕИСПОЛЬЗУЕМЫЙ модуль (НЕ самостоятельный генератор STL).

ЧИСТЫЙ ПАРАМЕТРИЧЕСКИЙ разрезной хомут (split-collar) под трубу Ø22 алюминий —
строится геометрией, а НЕ импортом меша. Хомут сына (incoming/son_tube_clamp.stl)
ВЫВЕДЕН ИЗ ОБОРОТА: мы повторили его функцию (бор Ø22 + прижимной болт-стяжка)
в чистой параметрической форме, без импорта STL, без косынок/арок/тонких шеек.

Профиль (канон):
  • бор Ø22 (+зазор) под ручки-защёлки труб, ось бора вдоль +Z, низ z=0;
  • стенка 4 мм → наружный Ø ≈ 30.4;
  • прорезь (щель 2.2 мм) от бора наружу на +X — воротник раздвигается;
  • две проушины по бокам щели с поперечным отверстием M5 (Ø5.4) — прижимной
    болт стягивает щёки и зажимает трубу.
Профиль призматичен вдоль оси бора (постоянное сечение) → печатается
вертикальным отверстием без поддержек, поперечный болт мостится (bridging).

Другие генераторы узлов (пауки, гнёзда, лапы) ИМПОРТИРУЮТ этот модуль и
приваривают (union) хомут к своим телам через place_clamp(). Публичное API и
имена констант сохранены — генераторы узлов работают без изменений.

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
OUTDIR = Path(__file__).parent / "stl"

BORE = 22.4             # бор под трубу Ø22 (+зазор), мм
WALL = 4.0             # стенка хомута, мм
OD   = BORE + 2 * WALL  # наружный Ø воротника ≈ 30.4, мм
EAR  = 6.0             # вылет проушины за OD, мм
M5   = 5.4             # Ø поперечного прижимного болта M5, мм
SLIT = 2.2             # ширина прорези (щели), мм

CLAMP_H  = 46.0         # высота канонического хомута по умолчанию, мм
CIRC_SEG = 96           # фасеты цилиндров демо-пластины
_SEG     = 64           # фасеты тел хомута

ENGINE = "manifold"


# ============================ ХЕЛПЕРЫ ============================
def _uni(ps):
    return trimesh.boolean.union(ps, engine=ENGINE)


def _dif(a, ps):
    return trimesh.boolean.difference([a] + list(ps), engine=ENGINE)


def _cyl(r, h, T=None, seg=_SEG):
    c = trimesh.creation.cylinder(radius=r, height=h, sections=seg)
    if T is not None:
        c.apply_transform(T)
    return c


def _box(x, y, z, T=None):
    b = trimesh.creation.box(extents=(x, y, z))
    if T is not None:
        b.apply_transform(T)
    return b


def _tr(x, y, z):
    M = np.eye(4)
    M[:3, 3] = (x, y, z)
    return M


# ============================ ГЕОМЕТРИЯ ХОМУТА ============================
def clamp_cyl(height):
    """Чистый разрезной цилиндр-хомут в каноне: ось бора +Z в (0,0), низ z=0,
    прорезь (щель) смотрит на +X, две проушины с отверстием M5 поперёк (вдоль Y).
    (эталон: truss/_proto_reference.py::clamp_cyl)"""
    body = _cyl(OD / 2, height, _tr(0, 0, height / 2))
    bore = _cyl(BORE / 2, height + 2, _tr(0, 0, height / 2))
    part = _dif(body, [bore])
    # щель разреза: тонкий вырез от бора наружу по +X
    slit = _box(OD, SLIT, height + 2, _tr(OD / 2, 0, height / 2))
    part = _dif(part, [slit])
    # две проушины по бокам щели (по ±Y от неё)
    ears = []
    for sy in (+1, -1):
        e = _box(EAR + WALL, WALL, height,
                 _tr(OD / 2 + (EAR + WALL) / 2 - WALL, sy * (WALL / 2 + 1.1), height / 2))
        ears.append(e)
    part = _uni([part] + ears)
    # отверстие болта M5 поперёк проушин (вдоль Y)
    bolt = _cyl(M5 / 2, OD + 2 * EAR + 8,
                _tr(OD / 2 + EAR / 2, 0, height / 2)
                @ trimesh.transformations.rotation_matrix(math.radians(90), [1, 0, 0]))
    part = _dif(part, [bolt])
    part.merge_vertices()
    part.process(validate=True)
    return part


# ============================ КОНСТАНТЫ ============================
BORE_D   = round(BORE, 2)            # Ø бора под трубу, мм
BOLT_D   = round(M5, 2)              # Ø поперечного прижимного болта M5, мм
CLAMP_OD = round(OD, 1)             # наружный Ø воротника, мм


def _selfcheck():
    print("tube_clamp self-check (чистый параметрический разрезной хомут):")
    print(f"  бор Ø{BORE_D} мм (под трубу Ø22 + зазор), стенка {WALL} мм → воротник Ø{CLAMP_OD} мм")
    print(f"  прорезь {SLIT} мм на +X; проушины вылет {EAR} мм; прижимной болт M5 Ø{BOLT_D} мм поперёк")
    print(f"  высота по умолчанию CLAMP_H={CLAMP_H} мм; профиль призматичен вдоль +Z (печать без поддержек)")


# ============================ ПУБЛИЧНОЕ API ============================
def clamp_mesh(height=CLAMP_H):
    """Канонический хомут: ось бора вдоль +Z в (0,0), прорезь на +X, низ z=0.
    Возвращает watertight trimesh высотой `height`."""
    return clamp_cyl(height)


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
    mesh.merge_vertices()
    mesh.process(validate=True)
    out = OUTDIR / f"{name}.stl"
    mesh.export(out)
    bb = mesh.bounds
    print(f"  {name}.stl  watertight={mesh.is_watertight}  vol={mesh.volume/1000:.2f}cm³  "
          f"bbox={bb[1,0]-bb[0,0]:.0f}×{bb[1,1]-bb[0,1]:.0f}×{bb[1,2]-bb[0,2]:.0f}mm")
    return mesh


def _demo():
    """Три хомута на болванке-пластине под 0/120/240° радиально —
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
        part = _uni([part, c])
    return _finish(part, "_clamp_demo")


if __name__ == "__main__":
    _selfcheck()
    print("Демо: 3 хомута на пластине (0/120/240°)…")
    _demo()
    print(f"\nГотово → {OUTDIR}")
else:
    _selfcheck()
