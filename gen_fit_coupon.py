#!/usr/bin/env python3
"""
Примерочные ПРОБНИКИ посадок для энкодерных колпачков (фанерный ровербокс).
v2: отдельные детали вместо общей плашки (соседние болты колеса мешали).

7 деталей на одном столике, печатать отверстиями ВВЕРХ, тем же пластиком/
профилем, что финальные колпачки (посадка зависит от усадки принтера!).

Ряд A — под АЗИМУТАЛЬНЫЙ болт (Ø6.2 резьба, торчит 15.6): ШЕСТИГРАННИКИ
    под ключ 13, глухой бор глубиной 12. НАКРУЧИВАТЬ (болт сам нарежет
    резьбу в PETG). Риски на гранях: 1 / 2 / 3 = Ø5.5 / 5.7 / 5.9.

Ряд B — под КОНЦЫ болтов колеса высоты (Ø≈4.7, торчат ~3.15): пятачки
    Ø10×6, гнездо глубиной 4.2. Риски по ободу: 1 / 2 / 3 / 4 =
    Ø4.4 / 4.6 / 4.8 / 5.0. Ищем «плотно, снимается со щелчком».

Запуск: /opt/homebrew/bin/python3 gen_fit_coupon.py
    → stl/encoder/fit_caps_plate.stl (все 7 вместе)
"""
import numpy as np
import trimesh
from trimesh.creation import box, cylinder
from pathlib import Path

AZ_BORES = [5.5, 5.7, 5.9]        # риски 1/2/3
ALT_SOCKETS = [4.4, 4.6, 4.8, 5.0]  # риски 1/2/3/4
HEX_AF = 13.0                     # шестигранник, размер под ключ (across flats)
HEX_H, AZ_DEPTH = 16.0, 12.0
PUCK_D, PUCK_H, ALT_DEPTH = 10.0, 6.0, 4.2


def at(m, dx, dy, dz):
    m.apply_translation([dx, dy, dz])
    return m


def notches(cx, cy, r_out, h, n):
    """n вертикальных рисок 1.2×1.0 на «севере» детали, шаг 3 мм по x."""
    cuts = []
    for k in range(n):
        x = cx - 1.5 * (n - 1) + 3.0 * k
        cuts.append(at(box(extents=[1.2, 2.0, h + 2]), x, cy + r_out, h / 2))
    return cuts


parts = []
# --- ряд A: шестигранники азимута ---
hex_R = HEX_AF / np.sqrt(3.0)     # circumradius для across-flats 13
for i, d in enumerate(AZ_BORES):
    cx = i * (HEX_AF + 8.0)
    body = at(cylinder(radius=hex_R, height=HEX_H, sections=6), cx, 0, HEX_H / 2)
    bore = at(cylinder(radius=d / 2, height=AZ_DEPTH + 1, sections=64),
              cx, 0, HEX_H - AZ_DEPTH / 2 + 0.5)
    piece = trimesh.boolean.difference(
        [body, bore] + notches(cx, 0, HEX_AF / 2, HEX_H, i + 1), engine='manifold')
    parts.append(piece)

# --- ряд B: пятачки колеса ---
for i, d in enumerate(ALT_SOCKETS):
    cx = i * (PUCK_D + 8.0)
    body = at(cylinder(radius=PUCK_D / 2, height=PUCK_H, sections=96), cx, 30, PUCK_H / 2)
    sock = at(cylinder(radius=d / 2, height=ALT_DEPTH + 1, sections=64),
              cx, 30, PUCK_H - ALT_DEPTH / 2 + 0.5)
    piece = trimesh.boolean.difference(
        [body, sock] + notches(cx, 30, PUCK_D / 2, PUCK_H, i + 1), engine='manifold')
    parts.append(piece)

plate = trimesh.util.concatenate(parts)
out = Path(__file__).parent / 'stl' / 'encoder'
out.mkdir(parents=True, exist_ok=True)
plate.export(out / 'fit_caps_plate.stl')
vols = [round(p.volume / 1000, 2) for p in parts]
print('pieces:', len(parts), '| watertight:', all(p.is_watertight for p in parts))
print('volumes cm3:', vols, '| total:', round(sum(vols), 1))
print('bbox:', np.round(plate.bounds[1] - plate.bounds[0], 1))

# ================= РАУНД 2 (26.07): азимут-болт не влез даже в Ø5.9 =========
# Три шестигранника Ø6.0/6.2/6.4, глубина 9, заходная фаска 45°.
# Метки: КРУГОВЫЕ КАНАВКИ вокруг тела (1/2/3), чтобы не путать с рисками р.1.
AZ_BORES_R2 = [6.0, 6.2, 6.4]
AZ_DEPTH_R2 = 9.0

def ring_cutter(cx, cy, z):
    ring = trimesh.boolean.difference(
        [at(cylinder(radius=9.0, height=1.2, sections=96), cx, cy, z),
         at(cylinder(radius=6.0, height=1.6, sections=96), cx, cy, z)],
        engine='manifold')
    return ring

parts2 = []
for i, d in enumerate(AZ_BORES_R2):
    cx = i * (HEX_AF + 8.0)
    body = at(cylinder(radius=hex_R, height=HEX_H, sections=6), cx, 0, HEX_H / 2)
    bore = at(cylinder(radius=d / 2, height=AZ_DEPTH_R2 + 1, sections=64),
              cx, 0, HEX_H - AZ_DEPTH_R2 / 2 + 0.5)
    # заходная фаска: конус 45°, широким основанием у устья
    rb = d / 2 + 1.2
    cham = trimesh.creation.cone(radius=rb, height=rb, sections=64)
    cham.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
    cham = at(cham, cx, 0, HEX_H + 0.01)          # остриём вниз, база на торце
    rings = [ring_cutter(cx, 0, 3.0 + 3.0 * k) for k in range(i + 1)]
    piece = trimesh.boolean.difference([body, bore, cham] + rings, engine='manifold')
    parts2.append(piece)

plate2 = trimesh.util.concatenate(parts2)
plate2.export(out / 'fit_caps_round2.stl')
print('ROUND2 pieces:', len(parts2), '| watertight:',
      all(p.is_watertight for p in parts2),
      '| total cm3:', round(sum(p.volume for p in parts2) / 1000, 1))
