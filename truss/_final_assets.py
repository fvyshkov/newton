#!/usr/bin/env python3
"""Финальные ассеты GoTo высотного узла (единое седло +Y тефлон / −Y ведущий ролик):
  _MECHANISM.png — 3D + схема (колесо, седло, мотор, ролик, энкодер);
  _BED_LAYOUT.png — 2 стола Bambu под все 8 деталей.
→ print_queue/verkhniy_yarus/"""
import math, numpy as np, trimesh
import generate_rocker_towers as TW
D = "print_queue/verkhniy_yarus/"

def _clean(mm,*a,**k):
    mm.merge_vertices(digits_vertex=5); mm.process(validate=True)
    ps=mm.split(only_watertight=False); return max(ps,key=lambda x:abs(x.volume)) if len(ps)>1 else mm
TW.finish=lambda mm,n,pose=None:_clean(mm); TW.tube_fit=TW.seat_enclosure_test=lambda *a,**k:True
def roty(d): return trimesh.transformations.rotation_matrix(math.radians(d),[0,1,0])
def tr(x,y,z):
    M=np.eye(4); M[:3,3]=(x,y,z); return M
WX,APZ,AXZ=170,460,590
ROLL_Y,ROLL_Z=TW.ROLL_Y, AXZ-TW.ROLL_DZ            # −Y ролик z=493.75
ROLL_XW=WX+5; MOT_Z=ROLL_Z-TW.BELT_CD

apex=TW.rocker_tower_apex(+1,"R",enc_pad=True); apex.apply_transform(tr(WX,0,APZ))
cr=TW.rocker_cradle_manual(+1,"R"); cr.apply_transform(roty(90)); cr.apply_transform(tr(WX,0,APZ))
dr=TW.rocker_alt_drive("d"); dr.apply_transform(roty(90)); dr.apply_transform(tr(WX,0,APZ))
disc=trimesh.creation.cylinder(radius=100,height=15,sections=72); disc.apply_transform(roty(90)); disc.apply_transform(tr(WX,0,AXZ))
mag=trimesh.creation.cylinder(radius=9,height=7,sections=24); mag.apply_transform(roty(90)); mag.apply_transform(tr(WX+11,0,AXZ))
arm=trimesh.load(TW.OUTDIR/"Rocker_alt_encoder_arm.stl")
roller=trimesh.creation.cylinder(radius=17.5,height=16,sections=32); roller.apply_transform(roty(90)); roller.apply_transform(tr(ROLL_XW,-ROLL_Y,ROLL_Z))
nema=trimesh.creation.box(extents=(48,42,42)); nema.apply_transform(tr(ROLL_XW+40,-ROLL_Y,MOT_Z))

import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Wedge
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
def shade(m,b):
    n=m.face_normals; L=np.array([0.5,0.35,1.0]); L/=np.linalg.norm(L)
    it=np.clip(0.4+0.6*(n@L),0.25,1.0); return m.vertices[m.faces],(np.array(b)[None]*it[:,None]).clip(0,1)

# ---------------- MECHANISM ----------------
CLR={"колесо Ø200 (крутится с трубой=ВЫСОТА)":(disc,(0.2,0.2,0.22)),
     "магнит в центре колеса":(mag,(0.85,0.2,0.2)),
     "вышка apex (неподв.)":(apex,(0.95,0.55,0.25)),
     "ЕДИНОЕ седло (неподв.)":(cr,(0.55,0.75,0.95)),
     "кронштейн мотора alt_drive":(dr,(0.75,0.6,0.9)),
     "энкодер-arm + плата AS5048A":(arm,(0.3,0.85,0.45)),
     "−Y ВЕДУЩИЙ ролик":(roller,(0.95,0.75,0.1)),
     "NEMA17":(nema,(0.15,0.15,0.15))}
fig=plt.figure(figsize=(19,10),dpi=115)
ax=fig.add_subplot(1,2,1,projection="3d"); ax.computed_zorder=False
g=[shade(m,c) for (m,c) in CLR.values()]
tri=np.vstack([x[0] for x in g]); fc=np.vstack([x[1] for x in g])
pc=Poly3DCollection(tri,facecolors=fc,edgecolor="none"); pc.set_rasterized(True); ax.add_collection3d(pc)
av=np.vstack([x[0].reshape(-1,3) for x in g]); lo,hi=av.min(0),av.max(0); c=(lo+hi)/2; s=(hi-lo).max()*0.55
ax.set_xlim(c[0]-s,c[0]+s); ax.set_ylim(c[1]-s,c[1]+s); ax.set_zlim(c[2]-s,c[2]+s)
ax.set_box_aspect((1,1,1)); ax.view_init(elev=16,azim=-58); ax.set_axis_off()
ax.set_title("3D: финальный GoTo-узел (R-сторона)",fontsize=14)
ax.legend(handles=[plt.Line2D([0],[0],marker='s',ls='',ms=11,mfc=c,mec='k',label=n) for n,(m,c) in CLR.items()],
          loc='upper left',bbox_to_anchor=(-0.05,0.98),fontsize=9.5,framealpha=0.9)

ax2=fig.add_subplot(1,2,2); ax2.set_aspect("equal"); ax2.axis("off")
ax2.set_title("Схема-разрез: +Y тефлон (держит рукой) / −Y ведущий ролик (мотор)",fontsize=13)
ax2.add_patch(Circle((0,AXZ),100,fc=(0.2,0.2,0.22),ec="k",lw=1.5))
ax2.add_patch(Wedge((0,AXZ),100,60,120,width=3,fc=(0.4,0.4,0.42)))
# +Y тефлон-пятак
cxp=100*math.sin(math.radians(35)); czp=AXZ-100*math.cos(math.radians(35))
ax2.add_patch(Rectangle((cxp-16,czp-14),32,14,fc="#7fd08a",ec="k"))
ax2.plot([cxp],[czp],"s",color="#e8e8e8",ms=9,mec="k")
# −Y ведущий ролик
ax2.add_patch(Circle((-cxp,czp),17.5,fc="#f0c040",ec="k",lw=1.5))
# мотор+ремень
ax2.add_patch(Rectangle((-cxp-21,MOT_Z-21),42,42,fc="#252525",ec="k"))
ax2.add_patch(Circle((-cxp,MOT_Z),8,fc="0.3",ec="k"))
ax2.plot([-cxp-8,-cxp-17],[MOT_Z,czp],color="0.3",lw=2); ax2.plot([-cxp+8,-cxp+17],[MOT_Z,czp],color="0.3",lw=2)
ax2.add_patch(Circle((0,AXZ),5,fc=(0.85,0.2,0.2),ec="k")); ax2.plot([0],[AXZ],"g+",ms=16,mew=3)
def note(x,y,tx,ty,txt):
    ax2.annotate(txt,xy=(x,y),xytext=(tx,ty),fontsize=9.5,arrowprops=dict(arrowstyle="->",lw=1.3),
                 va="center",bbox=dict(boxstyle="round",fc="#fffbe6",ec="0.6"))
note(cxp,czp,120,czp+40,"+Y ТЕФЛОН-пятак:\nтрение держит высоту РУКАМИ")
note(-cxp,czp,-250,czp+30,"−Y ВЕДУЩИЙ ролик:\nмотор→ремень→трение\nпо ободу катит колесо")
note(-cxp,MOT_Z,60,MOT_Z-15,"NEMA17 (только на R-седле)")
note(0,AXZ,120,AXZ+95,"МАГНИТ + чип AS5048A на арме:\nнеподвижен, читает угол")
ax2.text(-40,335,"ОДНО седло = и руками (тефлон держит), и GoTo (мотор+энкодер прикручены).\n"
                 "Неподвижно: седло+вышка+мотор+энкодер. Крутится: колесо с трубой.",ha="center",fontsize=9.5,
         bbox=dict(boxstyle="round",fc="#e8f4ff",ec="0.5"))
ax2.set_xlim(-270,190); ax2.set_ylim(325,720)
fig.tight_layout(); fig.savefig(D+"_MECHANISM.png",dpi=115,bbox_inches="tight"); plt.close(fig)
print("→",D+"_MECHANISM.png")

# ---------------- BED LAYOUT (2 стола, 8 деталей) ----------------
CR=(257,160); AP=(84,77); DRV=(93,46); ARM=(130,28); ROL=(35,35); MAG=(18,18); BED=(350,320)
def plate(ax, items, title):
    ax.add_patch(Rectangle((0,0),*BED,fc="#f4f4f4",ec="k",lw=2))
    ax.add_patch(Rectangle((3,3),BED[0]-6,BED[1]-6,fc="none",ec="0.6",ls="--"))
    for name,x,y,w,h,col in items:
        ax.add_patch(Rectangle((x,y),w,h,fc=col,ec="k",lw=1.3))
        ax.text(x+w/2,y+h/2,name,ha="center",va="center",fontsize=8.5,weight="bold")
    ax.set_xlim(-10,360); ax.set_ylim(-10,330); ax.set_aspect("equal"); ax.set_title(title,fontsize=12,weight="bold"); ax.grid(alpha=0.2)
fig,axes=plt.subplots(1,2,figsize=(15,7.5),dpi=115)
plate(axes[0],[("cradle_R\n257×160",6,6,*CR,"#8fbfe8"),("apex_R\n84×77",6,172,*AP,"#f0a95a"),
               ("alt_drive\n93×46",100,172,*DRV,"#c9a8e0"),("magnet\ncap",205,172,*MAG,"#e88"),
               ("roller",240,172,*ROL,"#f0c040")],
      "СТОЛ 1: седло_R + вышка_R + привод + ролик + магнит")
plate(axes[1],[("cradle_L\n257×160",6,6,*CR,"#8fbfe8"),("apex_L\n84×77",6,172,*AP,"#f0a95a"),
               ("encoder_arm (лёжа)\n130×28",100,172,*ARM,"#6fd88a"),("roller",245,172,*ROL,"#f0c040")],
      "СТОЛ 2: седло_L + вышка_L + энкодер-arm + ролик")
fig.suptitle("Финальный GoTo высотный узел на Bambu H2D (350×320), PETG — 8 деталей, 2 стола\n"
             "Два седла (2×160) на один стол не влезают → седло на каждый стол + мелочь рядом.",fontsize=12)
fig.tight_layout(rect=[0,0,1,0.92]); fig.savefig(D+"_BED_LAYOUT.png",dpi=115,bbox_inches="tight"); plt.close(fig)
print("→",D+"_BED_LAYOUT.png")
