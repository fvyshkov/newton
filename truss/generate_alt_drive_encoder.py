#!/usr/bin/env python3
"""GoTo-кронштейны высоты (болтятся на монтажную плиту башни):
  • Rocker_alt_encoder_arm — держит плату AS5048A у магнита в ЦЕНТРЕ колеса (на оси),
    крепится на 2×M4 сверху плиты (world (183.5,0,621)/(…,633));
  • Rocker_alt_motor_mount — держит NEMA17 так, что ролик Ø35 на валу катит обод в
    точке −45° (вес трубы прижимает → фрикцион). Крепится на 2×M4 снизу плиты (±24,593).
  • Rocker_alt_roller — фрикц-ролик Ø35 на вал NEMA Ø5 (проточка под O-ring, M3-стопор).
Мир как в generate_alt_tower (ось колеса z=AXIS_H=700, колесо на x=side*170, наруж.
грань 180, плита x181..187). Печать: каждая на стол z=0. v1 — привод тюнить на стенде.
Запуск: python3 generate_alt_drive_encoder.py
"""
import math
from pathlib import Path
import numpy as np
import trimesh
from shapely.geometry import LineString

OUT = Path(__file__).parent / "print_queue" / "alt_tower"
ENGINE="manifold"
AXIS_H=700.0; APEX_Z=585.0; WX=170.0
R_T=100.0

def box(x0,x1,y0,y1,z0,z1):
    b=trimesh.creation.box(extents=(x1-x0,y1-y0,z1-z0)); b.apply_translation(((x0+x1)/2,(y0+y1)/2,(z0+z1)/2)); return b
def xcyl(x0,x1,y,z,d,seg=32):                       # цилиндр вдоль X
    c=trimesh.creation.cylinder(radius=d/2,height=x1-x0,sections=seg)
    c.apply_transform(trimesh.geometry.align_vectors([0,0,1],[1,0,0])); c.apply_translation(((x0+x1)/2,y,z)); return c
def uni(p): return trimesh.boolean.union(p,engine=ENGINE)
def dif(a,p): return trimesh.boolean.difference([a]+list(p),engine=ENGINE)
def finish(m,name,mirror,assemble=False):
    if mirror: m.apply_transform(np.diag([-1.0,1,1,1])); m.fix_normals()
    m.merge_vertices(digits_vertex=4); m.process(validate=True)
    if not m.is_watertight:
        trimesh.repair.fill_holes(m); m.fix_normals(); m.process(validate=True)
    bs=m.split(only_watertight=False)
    if len(bs)>1: m=max(bs,key=lambda x:abs(x.volume))
    if assemble: return m                     # мировые координаты (для сборки)
    m=_lay(m)
    OUT.mkdir(exist_ok=True); m.export(OUT/f"{name}.stl")
    b=m.bounds
    print(f"  {name}: wt={m.is_watertight} vol={m.volume/1000:.0f}cm³ bbox={b[1,0]-b[0,0]:.0f}×{b[1,1]-b[0,1]:.0f}×{b[1,2]-b[0,2]:.0f}")
    return m
def _lay(m):
    """положить на стол минимальной высотой (перебор 6 осевых поз + выбор min H с опорой)."""
    best=None
    for ax in (0,90,180,270):
        for ay in (0,90,180,270):
            T=trimesh.transformations.rotation_matrix(math.radians(ay),[0,1,0])@trimesh.transformations.rotation_matrix(math.radians(ax),[1,0,0])
            mm=m.copy(); mm.apply_transform(T); mm.apply_translation([0,0,-mm.bounds[0,2]])
            H=mm.bounds[1,2]-mm.bounds[0,2]
            n=mm.face_normals; a=mm.area_faces; fz=mm.vertices[mm.faces][:,:,2]
            base=a[(np.all(fz<1.2,axis=1))&(n[:,2]<-0.85)].sum()
            if base<50: continue
            if best is None or H<best[0]: best=(H,mm)
    return best[1] if best else m.apply_translation([0,0,-m.bounds[0,2]]) or m


# ---------- ЭНКОДЕР-ARM ----------
def encoder_arm(side=+1, name="Rocker_alt_encoder_arm_R", assemble=False):
    s=+1  # строим в R (x>0), mirror внутри finish
    foot=box(186,195,-9,9,610,644)                 # лапа к плите (наруж. грань 187)
    riser=box(182,188,-7,7,636,700)                # стойка вверх к оси
    head=box(182,189,-14,14,694,712)               # держатель платы у оси (z≈700)
    body=uni([foot,riser,head])
    cuts=[xcyl(184,197,0,621,4.4), xcyl(184,197,0,633,4.4)]      # 2×M4 в плиту
    cuts+= [xcyl(181,190,sy*9,704,2.7) for sy in (+1,-1)]        # 2×M2.5 плата
    cuts.append(box(181.4,183.0,-12,12,696,711))                 # карман платы (лицо к −X, к магниту)
    body=dif(body,cuts)
    return finish(body,name,mirror=(side<0),assemble=assemble)

# ---------- МОТОР-КРЕПЁЖ УНИВЕРСАЛЬНЫЙ (NEMA на СЛОТАХ вдоль −45° → любой ролик) ----------
def motor_mount(side=+1, name="Rocker_alt_motor_mount_R", assemble=False):
    # центр NEMA скользит по радиусу −45° → под ролик любого Ø (r=100+r_ролика):
    # Ø35→r117.5(5.7:1), Ø20→r110(10:1), Ø12→r106(16:1). Слот = и выбор, и натяг.
    uy,uz=-math.cos(math.radians(45)), -math.sin(math.radians(45))   # радиаль −45° в (y,z)
    rc=112.0; cy,cz=rc*uy, AXIS_H+rc*uz                              # центр слота (сред. r)
    SL=18.0                                                          # длина слота (r 103..121)
    xf=196.0
    foot  =box(186,196,-34,34,578,604)                              # лапа к плите (низ, ±24,593)
    face  =box(xf,xf+6, cy-32,cy+32, cz-32,cz+32)                   # плита NEMA (слоты внутри)
    bridge=box(186,xf+1, cy-32,-14, 580, cz+32)                     # мост лапа→NEMA
    body=uni([foot,bridge,face])
    def xslot(oy,oz,d,x0,x1):                                       # цельный слот-«стадион» вдоль −45°
        p0=(cy+oy+uy*(-SL/2), cz+oz+uz*(-SL/2)); p1=(cy+oy+uy*(SL/2), cz+oz+uz*(SL/2))
        poly=LineString([p0,p1]).buffer(d/2, cap_style=1, join_style=1)
        s=trimesh.creation.extrude_polygon(poly, x1-x0)
        s.apply_transform(np.array([[0,0,1,x0],[1,0,0,0],[0,1,0,0],[0,0,0,1]],float)); return s
    cuts=[xcyl(183,198,-24,593,4.4), xcyl(183,198,24,593,4.4),      # 2×M4 в плиту
          xslot(0,0,22.6,xf-3,xf+9)]                                # ПИЛОТ NEMA (слот)
    for sy in (+1,-1):
        for sz in (+1,-1):
            cuts.append(xslot(sy*15.5, sz*15.5, 3.6, xf-3,xf+9))   # 4×M3 NEMA (слоты)
    cuts.append(xslot(0,0,14, 150,xf-2))                            # зазор вал+ролик к ободу
    body=dif(body,cuts)
    return finish(body,name,mirror=(side<0),assemble=assemble)

# ---------- ФРИКЦ-РОЛИК Ø35 на вал NEMA Ø5 ----------
def roller(name="Rocker_alt_roller", od=35.0):
    r=od/2
    body=trimesh.creation.cylinder(radius=r,height=20,sections=64); body.apply_translation((0,0,10))
    groove=trimesh.creation.torus(major_radius=r,minor_radius=2.2,major_sections=48,minor_sections=16); groove.apply_translation((0,0,10))
    shaft=trimesh.creation.cylinder(radius=(5.0+0.2)/2,height=24,sections=32); shaft.apply_translation((0,0,10))
    grub=trimesh.creation.cylinder(radius=3.4/2,height=r,sections=16); grub.apply_transform(trimesh.geometry.align_vectors([0,0,1],[1,0,0])); grub.apply_translation((r/2,0,10))
    body=dif(body,[groove,shaft,grub])
    body.apply_translation([0,0,-body.bounds[0,2]])
    OUT.mkdir(exist_ok=True); body.export(OUT/f"{name}.stl")
    b=body.bounds; print(f"  {name}: wt={body.is_watertight} vol={body.volume/1000:.0f}cm³ Ø{od:.0f}×20 бор Ø5 → редукция {200/od:.1f}:1")
    return body

if __name__=="__main__":
    print("GoTo-кронштейны высоты (на монтажную плиту башни):")
    encoder_arm(+1,"Rocker_alt_encoder_arm_R"); encoder_arm(-1,"Rocker_alt_encoder_arm_L")
    motor_mount(+1,"Rocker_alt_motor_mount_R"); motor_mount(-1,"Rocker_alt_motor_mount_L")
    roller("Rocker_alt_roller_D35", 35.0)      # 5.7:1 (простой, много грипа)
    roller("Rocker_alt_roller_D20", 20.0)      # 10:1 (больше момент/точность)
    print(f"→ {OUT}")
