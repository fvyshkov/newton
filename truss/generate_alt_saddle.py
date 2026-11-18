#!/usr/bin/env python3
"""СЕДЛО-ПРИМЕРКА v2 — то же седло, что встроено в башню, отдельной деталью:
V-вырез (2 грани ±45°) + ступенька под фланец + ВСТРОЕННЫЕ ЩЁЧКИ (вторая стенка
фланцевого паза изнутри). Колесо пленено: наружу — уступ на lx15, внутрь — стенка
щёчки за карманом (осевой люфт AX_PLAY, радиальный зазор 1.5). Фланец по обмеру
Rover Box Weel.stl: ширина 5.0 мм (lx 15..20), дорожка 15, R100/R105.
Геометрию берём ИЗ generate_alt_tower.saddle_local() — примерка и башня не расходятся.
Печать: положить на бок (V-грани вниз), PETG, 3-4 стенки; паз щёчки печатается аркой.
Запуск: /opt/homebrew/bin/python3 generate_alt_saddle.py
"""
import numpy as np
import trimesh
import generate_alt_tower as T

OUT = T.OUT


def build(side=+1, name="Rocker_alt_saddle_R"):
    body = T.saddle_local()
    # крепёж примерки: 4×M4 сквозь ДНО ЖЁЛОБА (|y|=30 — там плита 9мм, отверстие
    # выходит в открытый жёлоб; на |y|≈64, как было, над отверстием 21мм склона V)
    holes = []
    for hx in (T.X_OUT+5, T.X_IN-5):
        for hy in (-30.0, 30.0):
            c = trimesh.creation.cylinder(radius=4.4/2, height=20, sections=20)
            c.apply_translation((hx, hy, T.Z_BOT+5))
            holes.append(c)
    body = T.dif(body, holes)
    if side < 0:                                   # L = зеркало по X
        body.apply_transform(np.diag([-1.0, 1.0, 1.0, 1.0])); body.fix_normals()
    body.apply_translation((0, 0, -body.bounds[0, 2]))     # на стол z=0
    body.merge_vertices(); body.process(validate=True)
    OUT.mkdir(exist_ok=True)
    body.export(OUT / f"{name}.stl")
    bb = body.bounds
    print(f"  {name}: watertight={body.is_watertight}  vol={body.volume/1000:.0f}cm³  "
          f"bbox={bb[1,0]-bb[0,0]:.0f}×{bb[1,1]-bb[0,1]:.0f}×{bb[1,2]-bb[0,2]:.0f}мм")
    return body


if __name__ == "__main__":
    print("Седло-примерка v2 (V + ступенька + встроенные щёчки):")
    print(f"  контакт ±{T.PHI:.0f}°, дорожка R{T.R_T}/фланец R{T.R_F}×{T.FLANGE_W:.0f}мм, "
          f"паз {T.X_STEP:.0f}..{T.POCKET_X1:.1f} (люфт {T.AX_PLAY}мм), щёчка до lx{T.CHEEK_X1:.1f}")
    T.verify_capture(T.saddle_local())
    build(+1, "Rocker_alt_saddle_R")
    build(-1, "Rocker_alt_saddle_L")
    print(f"→ {OUT}")
