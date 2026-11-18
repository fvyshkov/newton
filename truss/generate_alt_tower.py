#!/usr/bin/env python3
"""ПОЛНАЯ деталь верхнего яруса (R и L): гнёзда 2 ног ВНИЗ (к нижнему ярусу) +
V-седло v2 под колесо (дорожка Ø200 + фланец Ø210×5 ИЗНУТРИ; несёт только дорожка,
фланец пленён в пазе: уступ снаружи + встроенная щёчка изнутри) + бонки под ЖЕЛЕЗО
СНАРУЖИ (энкодер к оси, мотор к ободу). Ось колеса = 700 мм над плоскостью нижнего
яруса (замер; фактически ≈699.3 — беговой зазор V). Собирается в МИРОВЫХ координатах.
Анти-раскрытие дают щёчки (пара колёс, база 340); жёсткость вбок — косынки углов
(generate_alt_corner_gusset.py). Запуск: /opt/homebrew/bin/python3 generate_alt_tower.py
"""
import math
from pathlib import Path
import numpy as np
import trimesh
from shapely.geometry import Polygon
import tube_clamp as tc
import gen_rocker_comic as W

OUT = Path(__file__).parent / "print_queue" / "alt_tower"
ENGINE = "manifold"

# --- мир ---
AXIS_H = 700.0                       # ось колеса над плоскостью рамы (пользователь: 70см)
LIFT = 115.0                         # ось над базой седла
APEX_Z = AXIS_H - LIFT               # 585  где сходятся ноги = база седла
FZ = 0.0                             # плоскость углов рамы
RC = W.R_CORNER                      # 210
WX = 170.0                           # апекс/колесо на x=±170

# --- колесо/седло (из реального STL) ---
R_T, R_F, TREAD_W, CLR = 100.0, 105.0, 15.0, 0.5
PHI = 45.0; phi = math.radians(PHI)
# Несёт колесо ТОЛЬКО дорожка (грани на R+CLR: колесо садится на них, проседая
# CLR/cos45≈0.7 → ось фактически ≈699.3, не 700). Фланцевые склоны утоплены на
# FL_RELIEF: иначе в покое фланец R105 тёрся бы о свои склоны одновременно с
# дорожкой (радиусы разные — чистого качения нет; найдено булевой проверкой
# реального колеса 2026-07-23). Осевой упор даёт СТЕНКА ступеньки, не склоны.
FL_RELIEF = 1.5
A_T = -(R_T+CLR)/math.cos(phi); A_F = -(R_F+FL_RELIEF)/math.cos(phi)
Y_MAX = R_T*math.sin(phi) + 9.0
Z_TOP = -R_T*math.cos(phi) + 10.0
FLOOR_Z = -R_T - 6.0
Z_BOT = FLOOR_Z - 9.0
X_OUT, X_STEP, X_IN = -1.0, TREAD_W, 18.0

# --- ЩЁЧКИ v2, ВСТРОЕНЫ в седло (2026-07-23). Фланец по обмеру Rover Box Weel.stl
# ШИРИНОЙ 5.0 мм (lx 15..20), а не 3 — отдельная щёчка (generate_alt_saddle_cheeks,
# грань на lx 18.7) утыкалась бы во фланец на 1.3 мм, колесо не садилось. Встроенная
# стенка стоит ЗА карманом: осевой люфт фланца в пазе AX_PLAY, радиальный зазор 1.5.
# Центр (|y|<24) свободен под ядро апекса; заход — фаска 2.5 на кромке стенки.
FLANGE_W  = 5.0                              # ширина фланца (обмер)
AX_PLAY   = 1.2                              # осевой люфт колеса уступ↔щёчка
POCKET_X1 = TREAD_W + FLANGE_W + AX_PLAY     # 21.2 — дно кармана (стенка щёчки)
CHEEK_X1  = POCKET_X1 + 3.5                  # 24.7 — наружная грань щёчки (world 155.3)
POCKET_R  = R_F + 1.5                        # 106.5 — карман: фланец не трёт радиально
CHEEK_Y0, CHEEK_Y1 = 24.0, 78.0              # пластины по ±y, центр свободен
CHEEK_Z1  = -70.0                            # верх щёчки (фланцевая дуга выходит на y≈78)

HUB_R = 17.0
CLAMP_H = 46.0
SOCKET_WALL_MARGIN = 4.0             # мин. стенка между борами 2 ног на старте гнезда, мм
# ПРЯМОУГОЛЬНАЯ рама (real-Dob): ноги в плоскостях x=±170 (мимо ящика Ø300), центр
# перёд↔зад открыт под размах трубы. Феты на R210 (на дорожку венца).
CX = WX                                    # ноги в плоскости колёс x=±170
CY = 123.0                                 # ±123 → R=√(170²+123²)=210 (венец)
FR=np.array([ CX, CY,0.]); BR=np.array([ CX,-CY,0.])   # правые феты (перед/зад)
FL=np.array([-CX, CY,0.]); BL=np.array([-CX,-CY,0.])   # левые феты


def print_pose(m, min_base=120, max_h=None):
    """Повернуть в позу печати: min ОБЪЁМ поддержки при устойчивой опоре на грань,
    посадить на стол z=0. max_h — брать только НИЗКИЕ позы (плашмя): высокие узкие
    детали на маленьком пятне рискуют оторваться, юзер печатает башни «набок»."""
    best=None
    for ax in range(0,360,15):
        for ay in range(0,360,15):
            Rx=trimesh.transformations.rotation_matrix(math.radians(ax),[1,0,0])
            Ry=trimesh.transformations.rotation_matrix(math.radians(ay),[0,1,0]); T=Ry@Rx
            mm=m.copy(); mm.apply_transform(T); mm.apply_translation([0,0,-mm.bounds[0,2]])
            if max_h is not None and mm.bounds[1,2]>max_h: continue
            n=mm.face_normals; a=mm.area_faces; zc=mm.triangles_center[:,2]
            need=n[:,2]<-0.707; vol=(a[need]*zc[need]).sum()
            fz=mm.vertices[mm.faces][:,:,2]
            base=a[(np.all(fz<1.5,axis=1))&(n[:,2]<-0.85)].sum()
            if base<min_base: continue
            if best is None or vol<best[0]: best=(vol,T)
    m.apply_transform(best[1]); m.apply_translation([0,0,-m.bounds[0,2]]); return m


def box(x0,x1,y0,y1,z0,z1):
    b=trimesh.creation.box(extents=(x1-x0,y1-y0,z1-z0)); b.apply_translation(((x0+x1)/2,(y0+y1)/2,(z0+z1)/2)); return b
def wedge(ap,x0,x1):
    h=x1-x0; poly=Polygon([(0,ap),(400,ap+400),(-400,ap+400)])
    w=trimesh.creation.extrude_polygon(poly,h)
    w.apply_transform(np.array([[0,0,1,x0],[1,0,0,0],[0,1,0,0],[0,0,0,1]],float)); return w
def uni(ps): return trimesh.boolean.union(ps, engine=ENGINE)
def dif(a,ps): return trimesh.boolean.difference([a]+list(ps), engine=ENGINE)
def inter(ps): return trimesh.boolean.intersection(ps, engine=ENGINE)
def axis_cyl(direction,z0,z1,dia,origin,seg=48):
    d=np.asarray(direction,float); d/=np.linalg.norm(d); o=np.asarray(origin,float); L=z1-z0
    c=trimesh.creation.cylinder(radius=dia/2,height=L,sections=seg)
    T=trimesh.geometry.align_vectors([0,0,1],d); T[:3,3]=o+d*(z0+L/2); c.apply_transform(T); return c
def cone_solid(apex_pt,root_pt,r1,seg=48,overlap=3.0):
    """Сплошной клин apex(точка)→root(круг радиуса r1): переходник между apex и
    гнездом ноги, чтобы боры 2 ног не сходились в одну точку (см. SOCKET_WALL_MARGIN).
    Торец `overlap` мм ЗАныривает за root вглубь хомута (иначе конус и хомут стыкуются
    ровно по совпадающей грани — boolean-движок на этом плодит вырожденные осколки)."""
    apex_pt=np.asarray(apex_pt,float); root_pt=np.asarray(root_pt,float)
    L=np.linalg.norm(apex_pt-root_pt)
    d=(apex_pt-root_pt)/L
    H=L+overlap; R=r1*H/L                      # тот же наклон конуса, продлённый на overlap
    c=trimesh.creation.cone(radius=R,height=H,sections=seg)   # база R@z=0 (радиус ~r1 у root), верш@z=H
    T=trimesh.geometry.align_vectors([0,0,1],d); T[:3,3]=root_pt-d*overlap; c.apply_transform(T)
    return c


def pocket_cuts():
    """Резы фланцевого паза (локальная система седла): карман + фаска-заход.
    Отдельно от saddle_local, чтобы башня могла резать их ПОСЛЕ union ядра апекса
    (иначе сфера, приваренная после, оставляла плавник в кармане, съедая люфт)."""
    pocket=axis_cyl([1,0,0], X_IN-0.2, POCKET_X1, 2*POCKET_R, origin=(0,0,0), seg=128)
    ch=Polygon([(POCKET_X1-0.1,CHEEK_Z1+0.1),(POCKET_X1+2.5,CHEEK_Z1+0.1),
                (POCKET_X1-0.1,CHEEK_Z1-2.5)])
    chw=trimesh.creation.extrude_polygon(ch, 2*Y_MAX)          # (mx=x, my=z, mz=y)
    chw.apply_transform(np.array([[1,0,0,0],[0,0,1,-Y_MAX],[0,1,0,0],[0,0,0,1]],float))
    if chw.volume<0: chw.invert()
    return [pocket, chw]


def saddle_local(with_pocket=True):
    """V-седло в локальной системе (x=ось колеса, 0=наруж.торец; z=0 центр колеса).
    v2: + встроенные щёчки — вторая стенка фланцевого паза с внутренней стороны.
    Колесо пленено: наружу уступ (lx15), внутрь стенка щёчки (lx POCKET_X1).
    with_pocket=False — карман не резать (башня режет его сама после union ядра)."""
    stock=box(X_OUT,X_IN,-Y_MAX,Y_MAX,Z_BOT,Z_TOP)
    clip=box(X_OUT-1,X_IN+1,-Y_MAX-1,Y_MAX+1,FLOOR_Z,Z_TOP+1)
    cuts=[inter([wedge(A_T,X_OUT-0.5,X_STEP),clip]), inter([wedge(A_F,X_STEP,X_IN+0.5),clip])]
    body=dif(stock,cuts)
    # щёчки: 2 пластины на внутренней грани (±y), низ заодно с базой седла
    plates=[box(X_IN-0.1, CHEEK_X1, min(sy*CHEEK_Y0,sy*CHEEK_Y1),
                max(sy*CHEEK_Y0,sy*CHEEK_Y1), Z_BOT, CHEEK_Z1) for sy in (+1,-1)]
    body=uni([body]+plates)
    return dif(body, pocket_cuts()) if with_pocket else body


def verify_capture(sad):
    """Колесо (дорожка R100 lx0..15 + фланец R105 lx15..20) в седле-с-щёчками:
    в номинале, на краях люфта и в ПОЛОЖЕНИИ ПОКОЯ (просед CLR/cos45≈0.7) не трёт;
    за люфтом — ловится (пересечение>0). Вертикальный чек ловит контакт фланца
    со склонами (дефект, найденный на реальном колесе 2026-07-23, лечит FL_RELIEF)."""
    def wheel(dx, dz=0.0):
        t=axis_cyl([1,0,0],0+dx,TREAD_W+dx,2*R_T,origin=(0,0,dz),seg=96)
        f=axis_cyl([1,0,0],TREAD_W+dx,TREAD_W+FLANGE_W+dx,2*R_F,origin=(0,0,dz),seg=96)
        return uni([t,f])
    def vol(m):
        i=trimesh.boolean.intersection([sad,m],engine=ENGINE)
        return abs(i.volume) if (i is not None and len(i.vertices)) else 0.0
    v0,vin,vcatch_in,vcatch_out=vol(wheel(0)),vol(wheel(AX_PLAY-0.1)),vol(wheel(AX_PLAY+0.4)),vol(wheel(-0.6))
    drop=CLR/math.cos(phi)-0.05                       # чуть выше реального покоя
    vrest=vol(wheel(0,-drop))
    print(f"    пленение колеса: номинал {v0/1000:.2f}см³, сдвиг внутрь {AX_PLAY-0.1:.1f} → "
          f"{vin/1000:.2f}см³, покой (просед {drop:.2f}) → {vrest/1000:.2f}см³ (норма ~0); "
          f"за люфтом: внутрь {vcatch_in/1000:.2f}, наружу {vcatch_out/1000:.2f}см³ (ловит, >0)")
    assert v0<0.05e3 and vin<0.05e3, "колесо трёт седло/щёчку в пределах люфта"
    assert vrest<0.05e3, "в покое фланец трёт склоны — FL_RELIEF мал"
    assert vcatch_in>0.1e3 and vcatch_out>0.1e3, "паз не ловит фланец"


def world_M(side):
    if side>0:  return np.array([[-1,0,0,180],[0,1,0,0],[0,0,1,AXIS_H],[0,0,0,1]],float)  # world_x=180-lx
    else:       return np.array([[ 1,0,0,-180],[0,1,0,0],[0,0,1,AXIS_H],[0,0,0,1]],float) # world_x=-180+lx


def saddle_world(side):
    s=saddle_local(with_pocket=False)          # карман башня режет после union ядра
    s.apply_transform(world_M(side));  s.fix_normals();  return s


def build(side=+1, name="Rocker_alt_tower_R", assemble=False):
    apex=np.array([side*WX,0,APEX_Z])
    # 2 ноги вниз на СВОЙ бок (перёд+зад), обе в плоскости x=side*170 → мимо ящика
    legs={"front":(FR if side>0 else FL), "rear":(BR if side>0 else BL)}
    parts=[trimesh.creation.icosphere(subdivisions=3,radius=HUB_R)]
    parts[0].apply_translation(apex)
    parts.append(saddle_world(side))
    # ---- развести гнёзда 2 ног от apex клиньями, иначе боры Ø22.4 сливаются ----
    # (2026-07-21: печать показала слипшуюся "восьмёрку" — оси гнёзд сходятся в apex
    # под углом ~24°, боры не успевали разойтись даже на всей длине хомута CLAMP_H=46мм;
    # см. обсуждение — минимум для касания бортов было 54мм > CLAMP_H)
    dirs={key:(cn-apex)/np.linalg.norm(cn-apex) for key,cn in legs.items()}
    ang=math.acos(np.clip(np.dot(dirs["front"],dirs["rear"]),-1.0,1.0))
    standoff=(tc.BORE+SOCKET_WALL_MARGIN)/(2*math.sin(ang/2))    # отступ гнезда от apex
    wall_at_root=2*standoff*math.sin(ang/2)-tc.BORE
    assert wall_at_root>=SOCKET_WALL_MARGIN-0.05, \
        f"стенка между гнёздами {wall_at_root:.1f}мм на старте — боры опять сольются"
    sockets=[]
    for key,cn in legs.items():
        d=dirs[key]
        slit=np.array([d[0],d[1],0.0]); slit/=np.linalg.norm(slit)   # прорезь горизонтально наружу
        root=apex+d*standoff
        parts.append(cone_solid(apex,root,tc.CLAMP_OD/2))             # клин apex→гнездо
        parts.append(tc.place_clamp(CLAMP_H, tuple(root), tube_dir=d, slit_dir=slit))
        sockets.append((key,root,d,CLAMP_H))
    print(f"  гнёзда разведены на {standoff:.0f}мм от apex (угол {math.degrees(ang):.1f}°, "
          f"стенка на старте гнезда {wall_at_root:.1f}мм)")
    # --- МОНТАЖНАЯ ПЛИТА ПОД ЖЕЛЕЗО, СНАРУЖИ колеса (world x за наруж. гранью 181) ---
    # Плоская плита на наруж. грани седла: СВЕРХУ 2×M4 под ЭНКОДЕР-arm (он тянется вверх
    # к магниту в центре колеса, ось z=AXIS_H), СНИЗУ 2×M4 под кронштейн МОТОРА (ролик к
    # ободу). Всё железо тут, снаружи; внутрь (к трубе) ничего не лезет.
    px_in, px_out = side*180.5, side*187.0
    parts.append(box(min(px_in,px_out), max(px_in,px_out), -35, 35, APEX_Z-2, APEX_Z+52))
    def xhole(x, y, z, d=3.4):                     # само-нарез M4 вдоль X сквозь плиту
        h=trimesh.creation.cylinder(radius=d/2, height=16, sections=16)
        h.apply_transform(trimesh.geometry.align_vectors([0,0,1],[1.0,0,0]))
        h.apply_translation((side*183.5, y, z)); return h
    mount=[xhole(0,0,APEX_Z+48), xhole(0,0,APEX_Z+36),          # ЭНКОДЕР (верх, вертик. пара)
           xhole(0,-24,APEX_Z+8), xhole(0,24,APEX_Z+8)]         # МОТОР (низ)
    body=uni(parts)
    # сквозная расточка боров ног Ø22.4 через ядро + крепёж + КАРМАН ФЛАНЦА
    # (карман режем тут, после union ядра апекса — иначе сфера оставляет плавник)
    pockets=[]
    for c in pocket_cuts():
        c=c.copy(); c.apply_transform(world_M(side))
        if c.volume<0: c.invert()
        pockets.append(c)
    drills=[axis_cyl(d,-4.0,entry,tc.BORE,origin=o) for _,o,d,entry in sockets]
    body=dif(body, drills+mount+pockets)
    # --- ОГИБАЮЩАЯ КОЛЕСА (2026-07-22, найдено на печати): ядро апекса (сфера R17,
    # центр на LIFT=115 под осью) торчало в жёлоб — до R98 под дорожкой R100 и до
    # R100 под фланцем R105 → колесо ложилось на шарик. Вырезаем колесо+фланец
    # с зазором CLR из ВСЕГО тела башни (страхует и от будущих утолщений ядра).
    # v2: фланец реальный 5мм (не 3) + люфт AX_PLAY — огибающая до дна кармана.
    def wcyl(r,x0,x1):
        c=trimesh.creation.cylinder(radius=r,height=abs(x1-x0),sections=96)
        M=trimesh.geometry.align_vectors([0,0,1],[1.0,0,0]); M[:3,3]=[(x0+x1)/2,0,AXIS_H]
        c.apply_transform(M); return c
    fo=side*180.0                                     # наружный торец колеса
    wheel_env=[wcyl(R_T+CLR, fo-side*(TREAD_W+AX_PLAY+0.5), fo+side*2.0),        # дорожка
               wcyl(R_F+CLR, fo-side*(POCKET_X1-0.05), fo-side*(TREAD_W-0.5))]   # фланец
    v0=body.volume
    body=dif(body, wheel_env)
    print(f"  вырез огибающей колеса из ядра: −{(v0-body.volume)/1000:.2f} см³")
    body.merge_vertices(); body.process(validate=True)
    bs=body.split(only_watertight=False)
    if len(bs)>1: body=max(bs,key=lambda m:abs(m.volume))
    if assemble: return body                               # мировые координаты (для сборки)
    body=print_pose(body, max_h=40)                        # ПЛАШМЯ (набок), на стол z=0
    OUT.mkdir(exist_ok=True); body.export(OUT/f"{name}.stl")
    bb=body.bounds
    print(f"  {name}: watertight={body.is_watertight} vol={body.volume/1000:.0f}cm³ "
          f"поза печати bbox={bb[1,0]-bb[0,0]:.0f}×{bb[1,1]-bb[0,1]:.0f}×{bb[1,2]-bb[0,2]:.0f} z0={bb[0,2]:.0f}")
    # длины ног (ось-в-ось); труба НЕ доходит до apex на standoff — конец трубы упирается
    # в дно гнезда (глухой карман, дно на -4мм от root), режется короче на ~standoff
    for key,cn in legs.items():
        full=np.linalg.norm(cn-apex)
        print(f"    нога {key}: {full:.0f}мм (апекс→угол) → резать {full-standoff:.0f}мм "
              f"(труба не доходит до apex на {standoff:.0f}мм — там клин, глухой карман)")
    return body


# --- СВЯЗКА z=490 («вариант A», tie_clamp) УДАЛЕНА (2026-07-23): она БИЛА БЫ ТРУБУ.
# В зените труба Ø240 стоит вертикально в центре (x²+y²<120², z от 284 вверх);
# точка связки (y=−20, z=490) — в 20 мм от оси трубы, т.е. на 100 мм ВНУТРИ неё.
# Комментарий «210 ниже оси > размах 180» был ошибкой: труба свисает к ящику на 415,
# ящик метёт радиусы 415..522. Между башнями ВЫШЕ z≈170 просвета нет вообще:
# перёд-верх метёт труба, зад-низ — труба+ящик. Анти-раскрытие теперь дают ЩЁЧКИ
# в седле (пара колёс, база 340, пленит башни), а жёсткость вбок — косынки в углах
# рамы (см. generate_alt_corner_gusset.py: там качание ничего не метёт, z<130).


def ground_node(cn, apex, neighbors, name, assemble=False):
    """Угловой узел ПРЯМОУГОЛЬНОЙ рамы: пятка на венце (z=0) + гнездо НОГИ вверх к апексу
    + горизонтальные гнёзда БАЗОВЫХ трубок к соседним углам (жёсткая рама, анти-раскрытие).
    Все ноги в плоскостях x=±170 → мимо ящика Ø300; центр перёд↔зад открыт."""
    cn=np.array(cn,float)
    parts=[box(cn[0]-32,cn[0]+32, cn[1]-30,cn[1]+30, 0,12)]
    parts.append(trimesh.creation.icosphere(subdivisions=3,radius=HUB_R)); parts[-1].apply_translation(cn+[0,0,13])
    socks=[]
    d=(np.array(apex)-cn); d/=np.linalg.norm(d)                    # НОГА вверх
    o=cn+[0,0,13]; parts.append(tc.place_clamp(CLAMP_H,tuple(o),tube_dir=d,slit_dir=np.array([d[0],d[1],0.])/np.linalg.norm(d[:2]))); socks.append((o,d,CLAMP_H))
    for nb in neighbors:                                            # БАЗОВЫЕ трубки (горизонт.)
        bd=(np.array(nb)-cn); bd/=np.linalg.norm(bd)
        o2=cn+[0,0,13]; parts.append(tc.place_clamp(CLAMP_H,tuple(o2),tube_dir=bd,slit_dir=np.array([0,0,1.]))); socks.append((o2,bd,CLAMP_H))
    body=uni(parts)
    body=dif(body,[axis_cyl(d,-4,h,tc.BORE,origin=o) for o,d,h in socks])
    body.merge_vertices(digits_vertex=4); body.process(validate=True)
    if not body.is_watertight:
        trimesh.repair.fill_holes(body); body.fix_normals(); body.process(validate=True)
    bs=body.split(only_watertight=False)
    if len(bs)>1: body=max(bs,key=lambda m:abs(m.volume))
    if assemble: return body
    body.apply_translation([0,0,-body.bounds[0,2]])
    OUT.mkdir(exist_ok=True); body.export(OUT/f"{name}.stl")
    bb=body.bounds
    print(f"  {name}: wt={body.is_watertight} vol={body.volume/1000:.0f}cm³ bbox={bb[1,0]-bb[0,0]:.0f}×{bb[1,1]-bb[0,1]:.0f}×{bb[1,2]-bb[0,2]:.0f}")

if __name__=="__main__":
    print(f"Полная деталь верх. яруса, ось колеса {AXIS_H:.0f}мм над рамой, апекс z={APEX_Z:.0f}:")
    print(f"  седло v2: щёчки встроены (фланец {FLANGE_W:.0f}мм по обмеру, люфт {AX_PLAY}мм, "
          f"карман R{POCKET_R:.1f} до lx{POCKET_X1:.1f}, стенка до lx{CHEEK_X1:.1f})")
    verify_capture(saddle_local())
    build(+1,"Rocker_alt_tower_R")
    build(-1,"Rocker_alt_tower_L")
    apR=np.array([WX,0,APEX_Z]); apL=np.array([-WX,0,APEX_Z])
    print("Угловые узлы ПРЯМОУГОЛЬНОЙ рамы (нога вверх + базовые трубки):")
    ground_node(FR, apR, [FL,BR], "Rocker_alt_corner_FR")   # правый-перед: база к FL(перёд) и BR(бок)
    ground_node(BR, apR, [BL,FR], "Rocker_alt_corner_BR")   # правый-зад
    ground_node(FL, apL, [FR,BL], "Rocker_alt_corner_FL")   # левый-перед
    ground_node(BL, apL, [BR,FL], "Rocker_alt_corner_BL")   # левый-зад
    print("Распил (труба Ø22):")
    print(f"    ноги ×4: РЕЗАТЬ {np.linalg.norm(FR-apR)-64:.0f}  (ось-в-ось {np.linalg.norm(FR-apR):.0f}, "
          f"минус 64 глухого кармана; все одинаковые)")
    print(f"    база перёд/зад ×2: {np.linalg.norm(FR-FL):.0f}   база бок ×2: {np.linalg.norm(FR-BR):.0f}")
    print(f"→ {OUT}")
