#!/usr/bin/env python3
"""ЭТАЛОН v2: хомут = ЧИСТЫЙ параметрический разрезной цилиндр (бор Ø22, разрез
вверх, проушина под болт M5). Узел = union хомутов + минимальное ядро. Ничего
лишнего. Мир из gen_rocker_comic."""
import sys, math
sys.path.insert(0, "/Users/mac/newton/truss")
import numpy as np, trimesh
import gen_rocker_comic as W

ENGINE="manifold"
def uni(ps): return trimesh.boolean.union(ps, engine=ENGINE)
def dif(a,ps): return trimesh.boolean.difference([a]+list(ps), engine=ENGINE)
def cyl(r,h,T=None,seg=64):
    c=trimesh.creation.cylinder(radius=r,height=h,sections=seg)
    if T is not None: c.apply_transform(T)
    return c
def box(x,y,z,T=None):
    b=trimesh.creation.box(extents=(x,y,z))
    if T is not None: b.apply_transform(T)
    return b
def tr(x,y,z):
    M=np.eye(4);M[:3,3]=(x,y,z);return M

BORE=22.4          # бор под трубу Ø22 (+зазор)
WALL=4.0           # стенка хомута
OD=BORE+2*WALL     # наружный Ø ≈ 30.4
EAR=6.0            # вылет проушины за OD
M5=5.4

def clamp_cyl(height):
    """Чистый разрезной цилиндр-хомут в каноне: ось бора +Z в (0,0), низ z=0,
    разрез (щель) смотрит на +X вверх, две проушины с отверстием M5 поперёк."""
    body = cyl(OD/2, height, tr(0,0,height/2))
    bore = cyl(BORE/2, height+2, tr(0,0,height/2))
    part = dif(body, [bore])
    # щель разреза: тонкий вырез от бора наружу по +X (сверху)
    slit = box(OD, 2.2, height+2, tr(OD/2, 0, height/2))
    part = dif(part, [slit])
    # две проушины по бокам щели (по ±Y от неё), с отверстием M5 поперёк (вдоль Y)
    ears=[]
    for sy in (+1,-1):
        e = box(EAR+WALL, WALL, height, tr(OD/2+ (EAR+WALL)/2 - WALL, sy*(WALL/2+1.1), height/2))
        ears.append(e)
    part = uni([part]+ears)
    # отверстие болта M5 поперёк проушин (вдоль Y)
    bolt = cyl(M5/2, OD+2*EAR+8, tr(OD/2+EAR/2, 0, height/2) @ trimesh.transformations.rotation_matrix(math.radians(90),[1,0,0]))
    part = dif(part, [bolt])
    return part

def place(height, origin, tube_dir, slit_dir):
    origin=np.asarray(origin,float)
    z=np.asarray(tube_dir,float); z/=np.linalg.norm(z)
    x=np.asarray(slit_dir,float); x=x-np.dot(x,z)*z; x/=np.linalg.norm(x)
    y=np.cross(z,x)
    T=np.eye(4); T[:3,0]=x; T[:3,1]=y; T[:3,2]=z; T[:3,3]=origin
    m=clamp_cyl(height); m.apply_transform(T); return m

def clamp_toward(center, endpoint, height, inset=0.0):
    center=np.asarray(center,float); endpoint=np.asarray(endpoint,float)
    d=endpoint-center; d=d/np.linalg.norm(d)
    origin=center - d*inset
    s=np.array([0,0,1.0])
    if abs(np.dot(s,d))>0.9: s=np.array([1.0,0,0])
    return place(height, origin, d, s)

def hub_ground():
    Z=32.0; center=np.array([0,0,Z])
    ends=[np.array(W.polar(285,a,Z)) for a in W.CORNER_ANGLES]
    clamps=[clamp_toward(center,e,height=40) for e in ends]
    core=cyl(15,44,tr(0,0,Z))          # минимальное ядро-склейка
    part=uni([core]+clamps)
    m10=cyl(10.6/2,80,tr(0,0,Z))
    nut=cyl(17.4/2/math.cos(math.pi/6),8,tr(0,0,Z-24+4),seg=6)
    part=dif(part,[m10,nut])
    part.merge_vertices();part.process(validate=True)
    part.apply_translation([0,0,-part.bounds[0,2]])
    return part

if __name__=="__main__":
    import matplotlib;matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    # показать ОДИН хомут + узел
    single=clamp_cyl(40)
    m=hub_ground()
    print("clamp watertight",single.is_watertight,"| hub watertight",m.is_watertight,
          "vol",round(m.volume/1000,1),"bbox",np.round(m.bounds[1]-m.bounds[0],0).tolist())
    fig=plt.figure(figsize=(14,5),dpi=100)
    for i,(mesh,el,az,t) in enumerate([(single,25,-55,"ОДИН хомут-цилиндр"),
                                        (m,89,-90,"ступица сверху"),(m,24,-52,"ступица iso")]):
        ax=fig.add_subplot(1,3,i+1,projection="3d")
        tri=mesh.vertices[mesh.faces];n=mesh.face_normals
        L=np.array([0.3,0.2,1.0]);L/=np.linalg.norm(L);it=np.clip(0.4+0.6*(n@L),0.28,1)
        fc=(np.array([[0.82,0.84,0.88]])*it[:,None]).clip(0,1)
        ax.add_collection3d(Poly3DCollection(tri,facecolors=fc,edgecolor="none"))
        c=(mesh.bounds[0]+mesh.bounds[1])/2;s=(mesh.bounds[1]-mesh.bounds[0]).max()*0.6
        ax.set_xlim(c[0]-s,c[0]+s);ax.set_ylim(c[1]-s,c[1]+s);ax.set_zlim(c[2]-s,c[2]+s)
        ax.view_init(el,az);ax.set_axis_off();ax.set_box_aspect((1,1,1));ax.set_title(t)
    fig.savefig("proto_hub2.png",bbox_inches="tight");print("saved proto_hub2.png")
