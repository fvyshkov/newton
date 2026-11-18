#!/usr/bin/env python3
"""
СТОЛ для Bambu H2D: энкодер высоты v3 — все 4 детали за один раз.
  пробник 608ZZ + ступица + стакан с поводком + штырь.
→ stl/encoder/STOL_v3_alt.3mf (детали на своих местах) + .stl + _STOL_v3_alt.png

Запуск (после gen_encoder_lever_alt.py):  python3 _stol_v3_alt.py
Печать: PLA, ЛЕВОЕ сопло 0.4, слой 0.2, 4 стенки, заполнение 40%, без поддержек.
"""
from pathlib import Path
import numpy as np
import trimesh

ENC = Path(__file__).parent / 'stl' / 'encoder'
# центр стола H2D ≈ (175,160); рабочая полоса ~300 по X (углы режут зоны сопел)
LAYOUT = [  # имя, подпись, центр X,Y относительно центра стола, поворот°
    ('v3_alt_carrier', 'стакан + поводок', 0, 55, 0),
    ('v3_fit_bearing', 'пробник 608ZZ', 10, -45, 0),
    ('v3_alt_hub', 'ступица', -100, -45, 0),
    ('v3_alt_post', 'штырь', 108, -45, 0),
]
BED_C = np.array([175.0, 160.0])

meshes, info = [], []
for name, label, cx, cy, rot in LAYOUT:
    m = trimesh.load(ENC / f'{name}.stl', process=False)
    m.merge_vertices()            # без слияния Bambu считает меш дырявым
    if rot:
        m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(rot), [0, 0, 1]))
    b = m.bounds
    m.apply_translation([BED_C[0] + cx - (b[0][0] + b[1][0]) / 2,
                         BED_C[1] + cy - (b[0][1] + b[1][1]) / 2, -b[0][2]])
    meshes.append((name, m))
    info.append((name, label, m))

# проверки: не пересекаются в плане (зазор ≥5), в пределах рабочей зоны
polys = []
for name, label, m in info:
    p = m.projected(normal=[0, 0, 1])
    polys.append((label, p))
for i in range(len(polys)):
    for j in range(i + 1, len(polys)):
        d = polys[i][1].polygons_full[0].distance(polys[j][1].polygons_full[0]) \
            if polys[i][1].polygons_full and polys[j][1].polygons_full else 99
        assert d >= 5.0, f'{polys[i][0]} и {polys[j][0]} ближе 5 мм ({d:.1f})'
allb = np.array([m.bounds for _, m in meshes])
lo, hi = allb[:, 0, :].min(0), allb[:, 1, :].max(0)
print(f'занято X {lo[0]:.0f}..{hi[0]:.0f}, Y {lo[1]:.0f}..{hi[1]:.0f} (стол 350×320), высота {hi[2]:.1f}')
assert lo[0] >= 25 and hi[0] <= 325 and lo[1] >= 10 and hi[1] <= 310

scene = trimesh.Scene()
for name, m in meshes:
    scene.add_geometry(m, node_name=name, geom_name=name)
scene.export(ENC / 'STOL_v3_alt.3mf')
trimesh.util.concatenate([m for _, m in meshes]).export(ENC / 'STOL_v3_alt.stl')
vol = sum(m.volume for _, m in meshes) / 1000
print(f'STOL_v3_alt.3mf + .stl: {len(meshes)} детали, {vol:.1f} см³ (≈{vol*1.24*0.6:.0f} г PLA при 4 стенках/40%)')

# картинка стола (SVG → PNG через браузер не нужен: рисуем сразу SVG)
S = 2.0
W, H = 350 * S, 320 * S
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H+60:.0f}" '
       f'viewBox="0 0 {W:.0f} {H+60:.0f}" font-family="system-ui,sans-serif">',
       f'<rect width="100%" height="100%" fill="#fff"/>',
       f'<rect x="0" y="0" width="{W}" height="{H}" fill="#2b2f35"/>',
       f'<rect x="{25*S}" y="0" width="{300*S}" height="{H}" fill="#33383f"/>']
cols = {'v3_alt_carrier': '#2f6fd6', 'v3_fit_bearing': '#9aa3ad', 'v3_alt_hub': '#e07b39', 'v3_alt_post': '#8a4fd1'}
for name, label, m in info:
    for poly in m.projected(normal=[0, 0, 1]).polygons_full:
        def path(ring):
            pts = np.array(ring.coords)
            return 'M' + ' L'.join(f'{x*S:.1f},{H - y*S:.1f}' for x, y in pts) + ' Z'
        d = path(poly.exterior) + ''.join(path(i) for i in poly.interiors)
        svg.append(f'<path d="{d}" fill="{cols[name]}" fill-rule="evenodd" stroke="#fff" stroke-width="1"/>')
    c = m.bounds.mean(0)
    top = m.bounds[1][1]
    svg.append(f'<text x="{c[0]*S:.0f}" y="{H - top*S - 8:.0f}" fill="#fff" font-size="15" '
               f'text-anchor="middle">{label}</text>')
svg.append(f'<text x="10" y="{H+24}" font-size="15" fill="#222">H2D, вид сверху. PLA, левое сопло 0.4, '
           f'слой 0.2, 4 стенки, 40%, без поддержек</text>')
svg.append(f'<text x="10" y="{H+46}" font-size="13" fill="#666">светлая полоса = рабочая зона ~300 мм '
           f'(углы режут зоны сопел)</text>')
svg.append('</svg>')
(ENC / '_STOL_v3_alt.svg').write_text('\n'.join(svg))
print('картинка →', ENC / '_STOL_v3_alt.svg')
