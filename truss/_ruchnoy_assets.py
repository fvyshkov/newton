#!/usr/bin/env python3
"""Ассеты для папки ruchnoy_dob: рендер ручной люльки+колесо (тефлон-пятаки) и
раскладка на 2 стола Bambu. → print_queue/ruchnoy_dob/_MECHANISM.png, _BED_LAYOUT.png"""
import math, numpy as np, trimesh
import generate_rocker_towers as TW
D = "print_queue/ruchnoy_dob/"

def _clean(mm,*a,**k):
    mm.merge_vertices(digits_vertex=5); mm.process(validate=True)
    ps=mm.split(only_watertight=False); return max(ps,key=lambda x:abs(x.volume)) if len(ps)>1 else mm
TW.finish=lambda mm,n,pose=None:_clean(mm); TW.tube_fit=lambda *a,**k:True
def roty(d): return trimesh.transformations.rotation_matrix(math.radians(d),[0,1,0])
def tr(x,y,z):
    M=np.eye(4); M[:3,3]=(x,y,z); return M
WX,APZ,AXZ=170,460,590

cr=TW.rocker_cradle_manual(+1,"m"); cr.apply_transform(roty(90)); cr.apply_transform(tr(WX,0,APZ))
disc=trimesh.creation.cylinder(radius=100,height=15,sections=72); disc.apply_transform(roty(90)); disc.apply_transform(tr(WX,0,AXZ))

import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Wedge, FancyArrowPatch
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

# ---------- MECHANISM ----------
def shade(m,b):
    n=m.face_normals; L=np.array([0.5,0.35,1.0]); L/=np.linalg.norm(L)
    it=np.clip(0.4+0.6*(n@L),0.25,1.0); return m.vertices[m.faces],(np.array(b)[None]*it[:,None]).clip(0,1)
fig=plt.figure(figsize=(16,7.5),dpi=115)
ax=fig.add_subplot(1,2,1,projection="3d"); ax.computed_zorder=False
g=[shade(disc,(0.2,0.2,0.22)),shade(cr,(0.55,0.85,0.6))]
tri=np.vstack([x[0] for x in g]); fc=np.vstack([x[1] for x in g])
pc=Poly3DCollection(tri,facecolors=fc,edgecolor="none"); pc.set_rasterized(True); ax.add_collection3d(pc)
av=np.vstack([x[0].reshape(-1,3) for x in g]); lo,hi=av.min(0),av.max(0); c=(lo+hi)/2; s=(hi-lo).max()*0.55
ax.set_xlim(c[0]-s,c[0]+s); ax.set_ylim(c[1]-s,c[1]+s); ax.set_zlim(c[2]-s,c[2]+s)
ax.set_box_aspect((1,1,1)); ax.view_init(elev=16,azim=-58); ax.set_axis_off()
ax.set_title("3D: колесо Ø200 лежит в люльке (зелён)",fontsize=13)

ax2=fig.add_subplot(1,2,2); ax2.set_aspect("equal"); ax2.axis("off")
ax2.set_title("Схема (вид спереди): колесо на 2 тефлон-пятаках",fontsize=13)
ax2.add_patch(Circle((0,AXZ),100,fc=(0.2,0.2,0.22),ec="k",lw=1.5))
ax2.add_patch(Wedge((0,AXZ),100,60,120,width=3,fc=(0.4,0.4,0.42)))
for sy in (+1,-1):
    cx=sy*100*math.sin(math.radians(35)); cz=AXZ-100*math.cos(math.radians(35))
    ax2.add_patch(Rectangle((cx-18,cz-14),36,14,angle=0,fc="#7fd08a",ec="k"))
    ax2.plot([cx],[cz],"s",color="#e8e8e8",ms=10,mec="k")   # тефлон
ax2.annotate("ТЕФЛОН-пятак (PTFE в кармане):\nобод скользит по нему, трение\nдержит любую высоту руками",
             xy=(-57,490),xytext=(-240,560),fontsize=10,arrowprops=dict(arrowstyle="->",lw=1.3),
             va="center",bbox=dict(boxstyle="round",fc="#fffbe6",ec="0.6"))
ax2.annotate("колесо Ø200 прикручено к трубе\n= крутится по ВЫСОТЕ",xy=(0,AXZ+100),xytext=(60,AXZ+120),
             fontsize=10,arrowprops=dict(arrowstyle="->",lw=1.3),va="center",
             bbox=dict(boxstyle="round",fc="#e8f4ff",ec="0.6"))
ax2.text(0,360,"НЕТ роликов/мотора/энкодера. Только 2 пятака (V, ±35°) + губки от съезда вбок\n"
               "+ палец-антиподъём сверху. Балансируешь трубу — толкаешь рукой, стоит где оставил.",
         ha="center",fontsize=9.5,bbox=dict(boxstyle="round",fc="#e8f7ee",ec="0.5"))
ax2.set_xlim(-260,180); ax2.set_ylim(340,720)
fig.tight_layout(); fig.savefig(D+"_MECHANISM.png",dpi=115,bbox_inches="tight"); plt.close(fig)
print("→",D+"_MECHANISM.png")

# ---------- BED LAYOUT (2 стола: седло_manual + вышка) ----------
CR=(257.0,163.0); AP=(83.7,76.9); BED=(350,320)
fig,axes=plt.subplots(1,2,figsize=(15,7.5),dpi=115)
for si,ax in enumerate(axes):
    c="R" if si==0 else "L"
    ax.add_patch(Rectangle((0,0),*BED,fc="#f4f4f4",ec="k",lw=2))
    ax.add_patch(Rectangle((3,3),BED[0]-6,BED[1]-6,fc="none",ec="0.6",ls="--"))
    ax.add_patch(Rectangle((6,6),*CR,fc="#8fbfe8",ec="k",lw=1.4))
    ax.text(6+CR[0]/2,6+CR[1]/2,f"cradle_manual_{c}\n(тефлон) 257×163",ha="center",va="center",fontsize=10,weight="bold")
    ax.add_patch(Rectangle((6,178),*AP,fc="#f0a95a",ec="k",lw=1.4))
    ax.text(6+AP[0]/2,178+AP[1]/2,f"apex_{c}\n84×77",ha="center",va="center",fontsize=9,weight="bold")
    ax.set_xlim(-10,360); ax.set_ylim(-10,330); ax.set_aspect("equal")
    ax.set_title(f"СТОЛ {si+1}: седло_{c} + вышка_{c}",fontsize=13,weight="bold")
    ax.grid(alpha=0.2)
fig.suptitle("Ручной доб на Bambu H2D (350×320), PETG — всего 4 детали, 2 стола\n"
             "Два седла (2×163=326) на один стол НЕ влезают → седло+вышка на каждый стол.",fontsize=12)
fig.tight_layout(rect=[0,0,1,0.92]); fig.savefig(D+"_BED_LAYOUT.png",dpi=115,bbox_inches="tight"); plt.close(fig)
print("→",D+"_BED_LAYOUT.png")
