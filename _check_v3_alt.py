#!/usr/bin/env python3
"""
Проверка энкодера высоты v3 В СБОРКЕ с настоящим колесом (Rover Box Weel.stl)
и стенкой с V-вырезом + цветная модель для 3D-страницы.
Запуск после gen_encoder_lever_alt.py:  ./.venv-cad/bin/python _check_v3_alt.py
"""
from pathlib import Path
import math
import numpy as np
import trimesh

HERE = Path(__file__).parent
ASM = HERE / 'stl' / 'encoder' / '_asm_v3_alt'
WHEEL_STL = Path.home() / 'Documents' / 'Truss New' / 'Rover Box Weel.stl'

# колесо из STL: ось вдоль x, наружная грань x=-180, центр (y 0.0235, z 462.5)
# → сборка: z = -(x+180) - 1 (наружная грань z=-1), x' = -y, y' = z - 462.5
w = trimesh.load(WHEEL_STL)
T = np.array([[0, -1, 0, 0.0235],
              [0, 0, 1, -462.5],
              [-1, 0, 0, -181.0],
              [0, 0, 0, 1]], dtype=float)
w.apply_transform(T)
print(f'колесо: z {w.bounds[0][2]:.2f}..{w.bounds[1][2]:.2f}, R {np.abs(w.bounds[:, :2]).max():.1f}')

# стенка: 250 шириной, V (±125,-30)→(0,-140), низ условно -330, толщина 16.5
wall_poly = [(-125, -330), (125, -330), (125, -30), (0, -140), (-125, -30)]
from shapely.geometry import Polygon
wall = trimesh.creation.extrude_polygon(Polygon(wall_poly), 16.5)
wall.apply_translation([0, 0, -16.5])

parts = {k: trimesh.load(ASM / f'{k}.stl') for k in
         ('hub', 'carrier', 'post', 'bearing_in', 'bearing_out', 'magnet', 'board', 'chip')}


def inter(a, b):
    try:
        r = trimesh.boolean.intersection([a, b], engine='manifold')
        return 0.0 if r is None or r.is_empty else r.volume
    except Exception as e:
        return float('nan')


print('С КОЛЕСОМ И СТЕНКОЙ (мм³, нужно 0):')
bad = False
for name in ('hub', 'carrier', 'post', 'board', 'chip'):
    for oname, o in (('колесо', w), ('стенка', wall)):
        if name == 'post' and oname == 'стенка':
            continue      # площадка штыря лежит на стенке (касание z=0)
        v = inter(parts[name], o)
        ok = v < 0.5
        bad |= not ok
        print(f'  {name:8s} ∩ {oname:7s} {v:8.2f}  {"OK" if ok else "ПЛОХО"}')

# ступица против колеса: только гнёзда на болтах, диск лежит на сплошной грани
hub = parts['hub']
sec = w.section(plane_origin=[0, 0, -1.05], plane_normal=[0, 0, 1])
holes_r = []
for e in sec.entities:
    q = sec.vertices[e.points]
    c = q.mean(0)
    r = np.hypot(q[:, 0] - c[0], q[:, 1] - c[1]).mean()
    if r < 40:
        holes_r.append((math.hypot(c[0], c[1]), r))
inner_window = min(rc - r for rc, r in holes_r if rc > 40)
print(f'окна колеса начинаются с r={inner_window:.1f}, диск ступицы до r=28 → запас {inner_window-28:.1f}')

# качание трубы: ступица крутится вокруг оси — проверить зазор стакана на всём ходу 0..90°
worst = 1e9
car = parts['carrier']
for ang in range(0, 91, 15):
    R = trimesh.transformations.rotation_matrix(math.radians(ang), [0, 0, 1])
    h = hub.copy(); h.apply_transform(R)
    ww = w.copy(); ww.apply_transform(R)
    v = inter(car, h) + inter(car, ww)
    worst = min(worst, -v)
    if v > 0.05:
        bad = True
        print(f'  угол {ang}: пересечение {v:.2f}')
print(f'качание 0..90°: стакан не задевает ступицу и колесо: {worst >= -0.05}')

# цветная сборка для страницы (GLB)
colors = {'wheel': [135, 150, 171], 'wall': [228, 204, 156], 'hub': [224, 123, 57],
          'carrier': [47, 111, 214], 'post': [138, 79, 209], 'bearing_in': [180, 188, 198],
          'bearing_out': [180, 188, 198], 'magnet': [214, 58, 58], 'board': [31, 122, 69],
          'chip': [25, 25, 25]}
scene = trimesh.Scene()
for k, m in list(parts.items()) + [('wheel', w), ('wall', wall)]:
    mm = m.copy()
    mm.visual.face_colors = colors[k] + [255]
    scene.add_geometry(mm, node_name=k, geom_name=k)
glb = ASM / 'asm_v3_alt.glb'
scene.export(glb)
print('GLB →', glb, f'{glb.stat().st_size/1e6:.2f} МБ')
if bad:
    raise SystemExit('ЕСТЬ ПЕРЕСЕЧЕНИЯ')
