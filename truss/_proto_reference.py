#!/usr/bin/env python3
"""ВАРИАНТ 3: убрать радиали из углов. Топология рамы:
 - 3 УГЛА: только 2 хорды (под 60°) + ноги башен → компактно, хомуты не сливаются.
 - 3 СЕРЕДИНЫ ХОРД: 2 полухорды (180°) + 1 радиаль к центру (90°) → чисто.
 - ЦЕНТР: 3 радиали к серединам хорд (120°) + ось M10 + энкодер.
Все узлы: трубы разнесены ≥60° → разрезной хомут с ушками работает без каши."""
import sys, math
sys.path.insert(0,"/Users/mac/newton/truss")
import numpy as np, trimesh
import gen_rocker_comic as W
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

R=W.R_CORNER; Z=W.FRAME_Z
A=np.array(W.polar(R,30,Z)); B=np.array(W.polar(R,150,Z)); C=np.array(W.polar(R,270,Z))
verts={'A(30°)':A,'B(150°)':B,'C(270°)':C}
mids={'mAB':(A+B)/2,'mBC':(B+C)/2,'mCA':(C+A)/2}
apexes={'apexR':np.array([170,0,530]),'apexL':np.array([-170,0,530])}

# ---------- СХЕМА РАМЫ (top view) ----------
fig,ax=plt.subplots(figsize=(9,9),dpi=110)
# хорды (через середины)
for p,q in [(A,B),(B,C),(C,A)]:
    ax.plot([p[0],q[0]],[p[1],q[1]],'-',color='#444',lw=4,zorder=1)
# радиали центр→середины
for m in mids.values():
    ax.plot([0,m[0]],[0,m[1]],'-',color='#c0392b',lw=3,zorder=1)
# узлы
for n,p in verts.items():
    ax.plot(p[0],p[1],'o',ms=22,color='#3498db',zorder=3)
    ax.annotate(f"УГОЛ\n{n}\n2 хорды",(p[0],p[1]),color='w',ha='center',va='center',fontsize=8,fontweight='bold',zorder=4)
for n,m in mids.items():
    ax.plot(m[0],m[1],'s',ms=20,color='#e67e22',zorder=3)
    ax.annotate(f"СЕРЕД.\n2+радиаль",(m[0],m[1]),color='w',ha='center',va='center',fontsize=7,fontweight='bold',zorder=4)
ax.plot(0,0,'*',ms=34,color='#c0392b',zorder=3)
ax.annotate("ЦЕНТР\n3 радиали\n+ось M10",(0,0),color='w',ha='center',va='center',fontsize=8,fontweight='bold',zorder=4)
ax.set_aspect('equal'); ax.set_title("ВАРИАНТ 3: рама сверху\nуглы=2 хорды(60°), центр→середины хорд, узлы разнесены ≥60°",fontsize=11)
ax.set_xlabel("мм"); ax.grid(alpha=0.3)
fig.savefig("scheme_v3.png",bbox_inches="tight"); print("saved scheme_v3.png")

# ---------- эталон УГЛОВОГО узла (2 хорды под 60°) ----------
ENGINE="manifold"
def uni(ps): return trimesh.boolean.union(ps,engine=ENGINE)
def dif(a,ps): return trimesh.boolean.difference([a]+list(ps),engine=ENGINE)
def cyl(r,h,T=None,seg=64):
    c=trimesh.creation.cylinder(radius=r,height=h,sections=seg)
    if T is not None: c.apply_transform(T)
    return c
def box(x,y,z,T=None):
    b=trimesh.creation.box(extents=(x,y,z))
    if T is not None: b.apply_transform(T)
    return b
def tr(x,y,z): M=np.eye(4);M[:3,3]=(x,y,z);return M
BORE=22.4;WALL=4.0;OD=BORE+2*WALL;EAR=6.0;M5=5.4;SLIT=2.2;CLAMP_H=38.0
def clamp_cyl(h):
    # труба входит с НАРУЖНОГО торца (z=h) и упирается в ядро (z=0), поэтому
    # болт затяжки — у наружного торца (BZ), где труба ТОЧНО внутри, не в середине
    BZ=h-11.0
    part=dif(cyl(OD/2,h,tr(0,0,h/2)),[cyl(BORE/2,h+2,tr(0,0,h/2))])
    part=dif(part,[box(OD,SLIT,h+2,tr(OD/2,0,h/2))])
    ears=[box(EAR+WALL,WALL,16,tr(OD/2+(EAR+WALL)/2-WALL,sy*(WALL/2+SLIT/2+0.3),BZ)) for sy in (+1,-1)]
    part=uni([part]+ears)
    bolt=cyl(M5/2,OD+2*EAR+8,tr(OD/2+EAR/2,0,BZ)@trimesh.transformations.rotation_matrix(math.radians(90),[1,0,0]))
    return dif(part,[bolt])
def place(h,o,d,s):
    o=np.asarray(o,float);z=np.asarray(d,float);z/=np.linalg.norm(z)
    x=np.asarray(s,float);x=x-np.dot(x,z)*z;x/=np.linalg.norm(x);y=np.cross(z,x)
    T=np.eye(4);T[:3,0]=x;T[:3,1]=y;T[:3,2]=z;T[:3,3]=o
    m=clamp_cyl(h);m.apply_transform(T);return m
# угол A: 2 хорды к B и C
node=A.copy()
d1=(B-A);d1/=np.linalg.norm(d1); d2=(C-A);d2/=np.linalg.norm(d2)
core=trimesh.creation.icosphere(subdivisions=3,radius=14);core.apply_translation(node)
cl=[place(CLAMP_H,node,d1,[0,0,1.0]),place(CLAMP_H,node,d2,[0,0,1.0])]
part=uni([core]+cl); part.merge_vertices();part.process(validate=True)
ps=part.split(only_watertight=False)
if len(ps)>1: part=max(ps,key=lambda m:m.volume)
part.apply_translation([-node[0],-node[1],-part.bounds[0,2]])
print("угол-2хорды: watertight",part.is_watertight,"vol",round(part.volume/1000,1),"bbox",np.round(part.bounds[1]-part.bounds[0],0).tolist())
part.export("/Users/mac/newton/truss/_PROTO_corner_v3.stl")
fig=plt.figure(figsize=(10,5),dpi=100)
for i,(el,az,t) in enumerate([(22,-55,"iso"),(89,-90,"сверху: 2 хорды 60°")]):
    ax=fig.add_subplot(1,2,i+1,projection="3d")
    tri=part.vertices[part.faces];n=part.face_normals
    L=np.array([0.3,0.2,1.0]);L/=np.linalg.norm(L);it=np.clip(0.4+0.6*(n@L),0.3,1)
    fc=(np.array([[0.82,0.84,0.88]])*it[:,None]).clip(0,1)
    ax.add_collection3d(Poly3DCollection(tri,facecolors=fc,edgecolor="none"))
    c=(part.bounds[0]+part.bounds[1])/2;s=(part.bounds[1]-part.bounds[0]).max()*0.6
    ax.set_xlim(c[0]-s,c[0]+s);ax.set_ylim(c[1]-s,c[1]+s);ax.set_zlim(c[2]-s,c[2]+s)
    ax.view_init(el,az);ax.set_axis_off();ax.set_box_aspect((1,1,1));ax.set_title(t)
fig.savefig("proto_v3.png",bbox_inches="tight");print("saved proto_v3.png")


# ============ ЦЕНТР и СЕРЕДИНА ХОРДЫ (варианта 3) ============
def finish_node(solids, cuts, origin):
    part=uni(solids)
    if cuts: part=dif(part,cuts)
    part.merge_vertices(); part.process(validate=True)
    ps=part.split(only_watertight=False)
    if len(ps)>1: part=max(ps,key=lambda m:m.volume)
    part.apply_translation([-origin[0],-origin[1],-part.bounds[0,2]])
    return part

def center_node():
    """Центр: 3 радиали к серединам хорд (120°) + втулка M10 + место энкодера."""
    o=np.array([0,0,Z])
    ms=[(A+B)/2,(B+C)/2,(C+A)/2]
    dirs=[(m-o)/np.linalg.norm(m-o) for m in ms]
    bush=cyl(15,60,tr(0,0,Z))                        # втулка-ядро по оси M10
    cl=[place(38.0,o,d,[0,0,1.0]) for d in dirs]
    part=finish_node([bush]+cl,[cyl(10.6/2,80,tr(0,0,Z))],o)  # бор M10
    return part

def midchord_node():
    """Середина хорды AB: 2 полухорды (к A и к B, 180°) + радиаль к центру (90°)."""
    m=(A+B)/2
    dA=(A-m)/np.linalg.norm(A-m); dB=(B-m)/np.linalg.norm(B-m)
    dR=(np.array([0,0,Z])-m)/np.linalg.norm(np.array([0,0,Z])-m)
    core=trimesh.creation.icosphere(subdivisions=3,radius=14); core.apply_translation(m)
    cl=[place(34.0,m,dA,[0,0,1.0]),place(34.0,m,dB,[0,0,1.0]),place(34.0,m,dR,[0,0,1.0])]
    return finish_node([core]+cl,[],m)

cn=center_node(); mn=midchord_node()
print("центр: watertight",cn.is_watertight,"vol",round(cn.volume/1000,1),"bbox",np.round(cn.bounds[1]-cn.bounds[0],0).tolist())
print("середина: watertight",mn.is_watertight,"vol",round(mn.volume/1000,1),"bbox",np.round(mn.bounds[1]-mn.bounds[0],0).tolist())
cn.export("/Users/mac/newton/truss/_PROTO_center_v3.stl")
mn.export("/Users/mac/newton/truss/_PROTO_midchord_v3.stl")
# общий рендер трёх узлов
corner=trimesh.load("/Users/mac/newton/truss/_PROTO_corner_v3.stl")
fig=plt.figure(figsize=(15,5),dpi=100)
for i,(mesh,t) in enumerate([(corner,"УГОЛ: 2 хорды 60°"),(mn,"СЕРЕДИНА: 2 полухорды+радиаль"),(cn,"ЦЕНТР: 3 радиали+M10")]):
    ax=fig.add_subplot(1,3,i+1,projection="3d")
    tri=mesh.vertices[mesh.faces];n=mesh.face_normals
    L=np.array([0.3,0.2,1.0]);L/=np.linalg.norm(L);it=np.clip(0.4+0.6*(n@L),0.3,1)
    fc=(np.array([[0.82,0.84,0.88]])*it[:,None]).clip(0,1)
    ax.add_collection3d(Poly3DCollection(tri,facecolors=fc,edgecolor="none"))
    c=(mesh.bounds[0]+mesh.bounds[1])/2;s=(mesh.bounds[1]-mesh.bounds[0]).max()*0.6
    ax.set_xlim(c[0]-s,c[0]+s);ax.set_ylim(c[1]-s,c[1]+s);ax.set_zlim(c[2]-s,c[2]+s)
    ax.view_init(24,-55);ax.set_axis_off();ax.set_box_aspect((1,1,1));ax.set_title(t,fontsize=11)
fig.savefig("proto_v3_all.png",bbox_inches="tight");print("saved proto_v3_all.png")
