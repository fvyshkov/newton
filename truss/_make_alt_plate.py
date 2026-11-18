#!/usr/bin/env python3
"""Столы печати верхнего яруса v2. Всё на один стол не влезает, поэтому:
  STOL_1_towers    — 2 башни v2 (седло со встроенными щёчками), нестинг вплотную;
  STOL_2_rama_goto — 4 угла рамы + 2 мотор-крепежа + 2 энкодер-arm + ролики D35/D20.
(Косынки — STOL_3_gussets, собирает generate_alt_corner_gusset.py.)
Каждая деталь уже в позе печати. Тут шелф-раскладка + центровка на H2D 350×320.
ВНИМАНИЕ: .3mf слайсить заново из свежего .stl в Bambu Studio (CLI-слайсер сломан).
Запуск: /opt/homebrew/bin/python3 _make_alt_plate.py
"""
import math
from pathlib import Path
import numpy as np
import trimesh
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

D=Path(__file__).parent/"print_queue"/"alt_tower"; BED=(350,320); USABLE_W=300; GAP=8

KARKAS=[("Rocker_alt_tower_R.stl","башня R"),("Rocker_alt_tower_L.stl","башня L")]
GOTO=[("Rocker_alt_corner_FR.stl","угол FR"),("Rocker_alt_corner_BR.stl","угол BR"),
      ("Rocker_alt_corner_FL.stl","угол FL"),("Rocker_alt_corner_BL.stl","угол BL"),
      ("Rocker_alt_motor_mount_R.stl","мотор R"),("Rocker_alt_motor_mount_L.stl","мотор L"),
      ("Rocker_alt_encoder_arm_R.stl","энк R"),("Rocker_alt_encoder_arm_L.stl","энк L"),
      ("Rocker_alt_roller_D35.stl","ролик35"),("Rocker_alt_roller_D20.stl","ролик20")]

def rz(m,deg): m.apply_transform(trimesh.transformations.rotation_matrix(math.radians(deg),[0,0,1])); m.apply_translation([-m.bounds[0,0],-m.bounds[0,1],-m.bounds[0,2]])
def load(lst):
    out=[]
    for f,nm in lst:
        m=trimesh.load(D/f); m.apply_translation([-m.bounds[0,0],-m.bounds[0,1],-m.bounds[0,2]])
        out.append([m,nm,m.bounds[1,0],m.bounds[1,1]])
    return out
def shelf(items):
    items=sorted(items,key=lambda p:-p[3]); x=y=sh=0; pl=[]
    for m,nm,w,d in items:
        if x+w>USABLE_W: y+=sh+GAP; x=0; sh=0
        mm=m.copy(); mm.apply_translation([x,y,0]); pl.append((mm,nm)); x+=w+GAP; sh=max(sh,d)
    return pl
def nest2(items):
    """2 крупные детали ВПЛОТНУЮ друг к другу с поворотом каждой (треугольные башни
    сходятся, если одну развернуть). Полный перебор угол-угол-сдвиг по выпуклым
    оболочкам (не пересекаются → и меши не пересекаются). Возвращает [(mesh,nm),…]."""
    from shapely.geometry import MultiPoint
    from shapely.affinity import rotate, translate
    (mA,nA,_,_),(mB,nB,_,_)=items
    hA0=MultiPoint(mA.vertices[:,:2]).convex_hull; hB0=MultiPoint(mB.vertices[:,:2]).convex_hull
    best=None
    for aA in range(0,360,10):
        hA=rotate(hA0,aA,origin='centroid'); b=hA.bounds; hA=translate(hA,-b[0],-b[1])
        Aw,Ah=hA.bounds[2],hA.bounds[3]
        for aB in range(0,360,10):
            hB=rotate(hB0,aB,origin='centroid'); bBw=hB.bounds[2]-hB.bounds[0]; bBh=hB.bounds[3]-hB.bounds[1]
            for dx in range(0,360,10):
                if dx+bBw>USABLE_W: continue             # X-габарит ≤300: диагональные
                for dy in range(-200,240,10):            # зоны сопел H2D режут края стола
                    W=max(Aw,dx+bBw); H=max(Ah,dy+bBh)-min(0,dy)
                    if W>USABLE_W or H>BED[1]-GAP: continue      # дешёвый bbox-отсев ДО shapely
                    if best is not None and W*H>=best[0]: continue
                    hBp=translate(hB, dx-hB.bounds[0], dy-hB.bounds[1])
                    if hA.intersection(hBp).area>1: continue     # дорогой тест — только для кандидатов
                    best=(W*H,aA,aB,dx,dy)
    if best is None: return shelf(items)          # не вписались → обычная полка (сообщит «НЕ ВЛЕЗАЕТ»)
    _,aA,aB,dx,dy=best
    def place(m,deg,tx,ty):
        mm=m.copy(); mm.apply_transform(trimesh.transformations.rotation_matrix(math.radians(deg),[0,0,1]))
        b=mm.bounds; mm.apply_translation([tx-b[0,0],ty-b[0,1],-b[0,2]]); return mm
    return [(place(mA,aA,0,0),nA),(place(mB,aB,dx,dy),nB)]
def make(lst,name,title,pack=shelf):
    pl=pack(load(lst)); g=trimesh.util.concatenate([p[0] for p in pl]).bounds
    dx=(BED[0]-(g[1,0]-g[0,0]))/2-g[0,0]; dy=(BED[1]-(g[1,1]-g[0,1]))/2-g[0,1]
    for m,_ in pl: m.apply_translation([dx,dy,0])
    sc=trimesh.util.concatenate([p[0] for p in pl]); b=sc.bounds; W,Dp=b[1,0]-b[0,0],b[1,1]-b[0,1]
    sc.merge_vertices(); sc.update_faces(sc.nondegenerate_faces()); sc.remove_unreferenced_vertices()
    sc.export(D/f"{name}.stl"); fit=W<=BED[0] and Dp<=BED[1]
    print(f"{name}.stl: {len(pl)} дет, {W:.0f}×{Dp:.0f} → {'ВЛЕЗАЕТ' if fit else 'НЕ ВЛЕЗАЕТ'}")
    fig=plt.figure(figsize=(9,8.5)); ax=fig.add_subplot(111,projection="3d"); ax.set_facecolor("white"); fig.patch.set_facecolor("white")
    cols=plt.cm.tab20(np.linspace(0,1,max(len(pl),3)))
    for (m,nm),c in zip(pl,cols):
        ax.add_collection3d(Poly3DCollection(m.vertices[m.faces],facecolor=c,edgecolor="#888",lw=0.05,alpha=1))
        bb=m.bounds; ax.text((bb[0,0]+bb[1,0])/2,(bb[0,1]+bb[1,1])/2,bb[1,2]+3,nm,fontsize=8,ha="center",fontweight="bold")
    ax.plot([0,BED[0],BED[0],0,0],[0,0,BED[1],BED[1],0],[0]*5,color="#ced4da",lw=1.5,ls="--")
    ax.set_box_aspect((BED[0],BED[1],120)); ax.set_xlim(0,BED[0]); ax.set_ylim(0,BED[1]); ax.set_zlim(0,140)
    ax.view_init(elev=60,azim=-90); ax.set_zticks([])
    ax.set_title(f"{title}: {W:.0f}×{Dp:.0f} на {BED[0]}×{BED[1]} — {'влезает' if fit else 'НЕ влезает'}",fontsize=11,fontweight="bold")
    plt.tight_layout(); plt.savefig(D/f"_{name}.png",dpi=115,facecolor="white")

if __name__=="__main__":
    make(KARKAS,"STOL_1_towers","Стол 1 — 2 башни",pack=nest2)
    make(GOTO,"STOL_2_rama_goto","Стол 2 — углы рамы + GoTo + сёдла")
    # старый общий файл убираем, чтобы не путал (включая 3mf — печатают именно его!)
    for f in ("STOL_alt_tower.stl","_STOL_alt_tower.png","STOL_alt_tower.3mf"):
        (D/f).unlink(missing_ok=True)
    print(f"→ {D}")
