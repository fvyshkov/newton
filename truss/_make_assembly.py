#!/usr/bin/env python3
"""Полная СБОРКА (прямоугольная рама) + ПРОВЕРКА ЗЕНИТА: труба вертикальна, ящик Ø300
свисает 500 мм между ногами (x=±170), центр открыт. Экспорт ASSEMBLY_full.stl/.glb +
_ASSEMBLY_FULL.png (сборка) + _ZENITH_OK.png (проверка). Запуск: python3 _make_assembly.py
"""
import math, numpy as np, trimesh
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import generate_alt_tower as T
import generate_alt_drive_encoder as E
import generate_alt_corner_gusset as G

OUT=T.OUT; WX,APEX_Z,AXIS_H=T.WX,T.APEX_Z,T.AXIS_H
FR,BR,FL,BL=T.FR,T.BR,T.FL,T.BL
apR=np.array([WX,0,APEX_Z]); apL=np.array([-WX,0,APEX_Z])
OVER=500.0; BOXR=150.0     # свес ящика ниже оси, радиус ящика

def tube(p0,p1,r=11.,seg=24):
    p0=np.array(p0,float);p1=np.array(p1,float);v=p1-p0;L=np.linalg.norm(v)
    c=trimesh.creation.cylinder(radius=r,height=L,sections=seg); M=trimesh.geometry.align_vectors([0,0,1],v/L); M[:3,3]=(p0+p1)/2; c.apply_transform(M); return c
def disc(c,r,w,ax='x',seg=48):
    cc=trimesh.creation.cylinder(radius=r,height=w,sections=seg); M=trimesh.geometry.align_vectors([0,0,1],{'x':[1,0,0],'z':[0,0,1]}[ax]); M[:3,3]=c; cc.apply_transform(M); return cc

TUBECOL=[176,176,184,255]
items=[
 ("башня R",T.build(+1,assemble=True),[51,133,204,255]),
 ("башня L",T.build(-1,assemble=True),[90,170,230,255]),
 ("угол FR",T.ground_node(FR,apR,[FL,BR],"c",assemble=True),[150,110,70,255]),
 ("угол BR",T.ground_node(BR,apR,[BL,FR],"c",assemble=True),[150,110,70,255]),
 ("угол FL",T.ground_node(FL,apL,[FR,BL],"c",assemble=True),[170,125,80,255]),
 ("угол BL",T.ground_node(BL,apL,[BR,FL],"c",assemble=True),[170,125,80,255]),
 ("нога FR",tube(FR,apR),TUBECOL),("нога BR",tube(BR,apR),TUBECOL),
 ("нога FL",tube(FL,apL),TUBECOL),("нога BL",tube(BL,apL),TUBECOL),
 ("база перёд",tube(FR,FL),TUBECOL),("база зад",tube(BR,BL),TUBECOL),
 ("база бок R",tube(FR,BR),TUBECOL),("база бок L",tube(FL,BL),TUBECOL),
 # колесо по обмеру: наруж. торец на ±180, дорожка 15 (центр ±172.5), фланец 5 ИЗНУТРИ (центр ±162.5)
 ("колесо R",disc((172.5,0,AXIS_H),100,15),[60,60,66,255]),("фланец R",disc((162.5,0,AXIS_H),105,5),[120,90,200,255]),
 ("колесо L",disc((-172.5,0,AXIS_H),100,15),[60,60,66,255]),("фланец L",disc((-162.5,0,AXIS_H),105,5),[120,90,200,255]),
 ("энкодер",E.encoder_arm(+1,assemble=True),[140,90,200,255]),
 ("мотор",E.motor_mount(+1,assemble=True),[225,120,60,255]),
]
_gb=G.gusset_local()
for _nm,_cn,_ap,_b,_ in G.CORNERS:
    items.append((f"косынка {_nm}",G.place(_gb,_cn,_ap,_b)[0],[39,174,96,255]))
# ТРУБА в ЗЕНИТ: ящик Ø300 свисает 500 вниз (низ z=AXIS_H-OVER=200), струты+труба вверх
zbox=AXIS_H-OVER+42       # центр ящика
items.append(("зерк.ящик",disc((0,0,zbox),BOXR,85,ax='z'),[90,90,96,150]))
items.append(("труба OTA",tube((0,0,zbox+42),(0,0,AXIS_H+560),120),[200,205,210,80]))

scene=trimesh.Scene(); meshes=[]
for nm,m,col in items:
    m.visual.face_colors=col; scene.add_geometry(m,geom_name=nm); meshes.append(m)
scene.export(OUT/"ASSEMBLY_full.glb")
trimesh.util.concatenate(meshes).export(OUT/"ASSEMBLY_full.stl")

# --- численная проверка зенита: min зазор ящик(Ø300, z200..285) ↔ ноги/база ---
box_zlo=AXIS_H-OVER
legs=[(FR,apR),(BR,apR),(FL,apL),(BL,apL)]
minclr=1e9
for a,b in legs:
    for t in np.linspace(0,1,40):
        p=a+(b-a)*t
        if box_zlo-5<=p[2]<=box_zlo+90:                       # на высоте ящика
            r=math.hypot(p[0],p[1])
            minclr=min(minclr, r-BOXR)
print(f"ЗЕНИТ-проверка: min зазор ящик Ø300 ↔ ноги = {minclr:.0f} мм  ({'ПРОХОДИТ ✓' if minclr>0 else 'БЬЁТ ✗'})")

# --- рендеры ---
def render(fname,elev,azim,title):
    fig=plt.figure(figsize=(11,11)); ax=fig.add_subplot(111,projection="3d"); ax.set_facecolor("white"); fig.patch.set_facecolor("white")
    for nm,m,col in items:
        ax.add_collection3d(Poly3DCollection(m.vertices[m.faces],facecolor=np.array(col)/255,edgecolor="#777",lw=0.04,alpha=col[3]/255))
    ax.plot([-200,200,200,-200,-200],[-160,-160,160,160,-160],[0]*5,color='#ced4da',lw=1)
    ax.set_box_aspect((1,1,1.6)); ax.set_xlim(-260,260); ax.set_ylim(-260,260); ax.set_zlim(0,1300)
    ax.view_init(elev=elev,azim=azim); ax.set_axis_off(); ax.set_title(title,fontsize=12,fontweight="bold")
    plt.tight_layout(); plt.savefig(OUT/fname,dpi=120,facecolor="white")
render("_ASSEMBLY_FULL.png",15,-62,"Полная сборка (прямоуг. рама): труба в зенит, ящик проходит по центру")
render("_ZENITH_OK.png",6,-90,f"ЗЕНИТ спереди: ящик Ø300 между ногами x=±170 (зазор {minclr:.0f}мм)")
print(f"→ {OUT}/ASSEMBLY_full.stl/.glb + _ASSEMBLY_FULL.png + _ZENITH_OK.png")
