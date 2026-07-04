#!/usr/bin/env python3
"""
Наземная «звезда» рокера как ТРУБНАЯ рама (truss) — МИНИМАЛИСТИЧНАЯ версия.

СТАТИЧНАЯ земля: 3 радиальных трубы Ø22 под 120° (CORNER_ANGLES 30/150/270),
ось труб на z=32. Топология НЕ меняется (в отличие от вращающейся рамы v3):
хаб в центре → 3 трубы наружу → 3 лапы на полу; венец азимута лежит на 3 сёдлах.

Каждый узел = union ЧИСТЫХ разрезных хомутов (tube_clamp.place_clamp, эталон
truss/_proto_reference.py) + маленькое центральное ядро/лапа, ровно достаточное,
чтобы сварить их в одно водонепроницаемое тело, + ТОЛЬКО функциональные фичи (ось
M10, плоская лапа-стопа, плоское седло венца, юстировочный M4). БОЛЬШЕ НИЧЕГО.

ВСЕ направления труб вычисляются ИЗ КООРДИНАТ КОНЦОВ (polar() из общего мира
gen_rocker_comic), а не из углов «на глаз» — origin/ось хомута берутся из мировых
точек трубы, поэтому оси стыкуются со сборкой один-в-один.

БОЛТ-НА-ВХОДЕ: хомут (tube_clamp.clamp_cyl) кладёт болт-стяжку у ДАЛЬНЕГО от
origin торца (z=height). Поэтому origin ставим у «глухого» конца (ядро хаба /
терминал трубы), а ось ведём ТУДА, КУДА ВХОДИТ ТРУБА — тогда болт+проушины сидят
на входном торце, где труба ТОЧНО внутри:
  • ХАБ  — origin в центре, ось наружу → болт у R≈40 (труба входит снаружи внутрь);
  • ЛАПА — origin у терминала трубы R≈285, ось К ХАБУ → болт у R≈243 (вход от хаба);
  • СЕДЛО— пролётный хомут (труба сквозная), болт у наружного торца, вне седла.

УДАЛЕНО навсегда: скользящие площадки, косынки/гуссеты, дуги R200, седло-пьедестал
над прорезью, тонкие шейки, импорт меша сына.

Прорезь хомута: ВВЕРХ (+Z) для всех (трубы горизонтальны); ядро/фичи не заходят в
сектор прорези — зажим свободно затягивается.

  z=0        верх опорной доски (пол)
  z=32       ось радиальных труб Ø22 (бор всех хомутов)
  z=50       низ тела венца — верх седла (Rocker_ring_saddle_tube)

Детали / количества:
  1. Rocker_hub_truss.stl         ×1
  2. Rocker_leg_truss.stl         ×3
  3. Rocker_ring_saddle_tube.stl  ×3

ПОЗА ПЕЧАТИ (мир = координаты сборки, чтобы оси труб стыковались; экспорт =
переориентирован в естественную позу, плоская грань на столе, z_min=0):
  • Rocker_hub_truss — ось M10 ВЕРТИКАЛЬНА, плоское дно ядра на столе (мировая
    поза, только сдвиг z_min=0). Бор M10 вертикален, гекс-карман гайки открыт вниз.
  • Rocker_leg_truss — стопа (плоский прямоугольный пад) ПЛОСКО на столе, z=0;
    хомут-цилиндр сверху, бор горизонтален. Мировая поза, сдвиг z_min=0.
  • Rocker_ring_saddle_tube — ПЕРЕОРИЕНТИРОВАН: бор хомута поставлен ВЕРТИКАЛЬНО
    (канон хомута — печать без поддержек), плоский торец хомута на столе; седло
    венца торчит вбок. Поворот −90° вокруг Y + сдвиг z_min=0.
"""
import math
import sys
from pathlib import Path

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).parent))
from tube_clamp import place_clamp, CLAMP_OD          # noqa: E402 — чистый хомут
from gen_rocker_comic import (                          # noqa: E402 — общий мир
    CORNER_ANGLES, R_ARM_OUT, RING_Z, polar)

# ============================ ПАРАМЕТРЫ ============================
Z_ARM = 32.0            # высота оси радиальных труб (как ground_arms в комиксе)
CLAMP_H_ARM = 42.0      # длина хомута вдоль трубы (грип), мм
TUBE_OD = 22.0          # труба алюминий Ø22
SLIT_UP = (0.0, 0.0, 1.0)   # прорезь вверх (ортогонализуется к оси трубы)

# --- Мировая геометрия трубы (концы → направление) ---
# Труба стартует ВПРИТЫК к оси M10 (R11, чуть снаружи болта Ø10) и идёт до лапы
# R285 → длина ≈274мм. Так труба входит в хомут хаба на ~29мм (грип), а прижимной
# болт хомута (R≈29) реально обжимает трубу (раньше R35→грип всего 5мм, болт в пустом
# боре). Направление хомута хаба берётся из p_out, поэтому геометрия хаба не меняется —
# меняется только где труба стартует в сборке и длина реза.
R_TUBE_IN = 11.0        # труба стартует у оси на R11 (снаружи M10) → грип хаба ~29мм
R_TUBE_OUT = R_ARM_OUT  # труба заканчивается у лапы на R285 (терминал)

# --- Проверенные посадки этого принтера ---
M4_TAP = 2.7            # Ø под самонарез M4 (юстировочный винт-ножка)
M10_CLR = 10.6          # Ø сквозного M10 (ось азимута)
NUT10_AF = 17.4         # гекс-карман гайки M10 «под ключ»
NUT10_DEPTH = 8.0       # глубина кармана гайки M10

# --- 1. Хаб ---
HUB_CLAMP_H = 40.0      # длина хомутов хаба (из центра наружу)
HUB_CORE_R = 15.0       # радиус центрального ядра-склейки (≈ OD/2)
HUB_CORE_H = 44.0       # высота ядра

# --- 2. Лапа (Rocker_leg_truss) ---
LEG_FOOT_W = 34.0       # ширина стопы тангенциально
LEG_FOOT_TOP = 30.0     # верх стопы z=0..30 (сваривается с низом хомута)

# --- 3. Трубное седло венца (Rocker_ring_saddle_tube) ---
SAD_CLAMP_R0 = 150.0    # внутр. торец хомута на трубе (грип R150..R192)
SEAT_R_IN = 168.0       # плоский седловой таб СБОКУ (+Y), радиально наружу
SEAT_R_OUT = 214.0      # до-под тела венца (венец R200..218)
SEAT_Y_IN = 12.0        # внутр. грань таба по +Y: >11 (мимо трубы Ø22), мимо проушин
SEAT_Y_OUT = 30.0
SEAT_Z0 = 18.0          # низ таба
SEAT_TOP = RING_Z       # верх седла = низ тела венца (z=50)

SEG = 96
OUTDIR = Path(__file__).parent / "stl"
ENGINE = "manifold"

# --- Тест посадки трубы: Ø22 цилиндр длиной GRIP от входа бора внутрь ---
TUBE_FIT_D = 22.0       # идеальная труба Ø22 (номинал, бор Ø22.4)
TUBE_FIT_GRIP = 40.0    # требуемая глубина посадки, мм
TUBE_FIT_MAX = 0.08     # труба должна сидеть в ПОЛОМ боре ⇒ пересечение <8%

TUBE_SPAN = R_TUBE_OUT - R_TUBE_IN    # ≈ 250 мм (радиальный пролёт хаб→лапа)


# ============================ ХЕЛПЕРЫ ============================
def cyl(r, h, seg=SEG, T=None):
    c = trimesh.creation.cylinder(radius=r, height=h, sections=seg)
    if T is not None:
        c.apply_transform(T)
    return c


def box(x, y, z, T=None):
    b = trimesh.creation.box(extents=(x, y, z))
    if T is not None:
        b.apply_transform(T)
    return b


def tr(x, y, z):
    M = np.eye(4)
    M[:3, 3] = (x, y, z)
    return M


def roty(ang_deg):
    return trimesh.transformations.rotation_matrix(math.radians(ang_deg), [0, 1, 0])


def tube_pts(ang_deg):
    """Мировые концы радиальной трубы Ø22 на луче ang: (внутренний R35, внешний R285),
    ось на z=Z_ARM. ВСЕ направления хомутов считаются из этих точек."""
    p_in = np.array(polar(R_TUBE_IN, ang_deg, Z_ARM))
    p_out = np.array(polar(R_TUBE_OUT, ang_deg, Z_ARM))
    return p_in, p_out


def clamp_entry(p_blind, p_entry, height, slit_dir=SLIT_UP):
    """Хомут по КООРДИНАТАМ КОНЦОВ: origin у «глухого» торца p_blind, ось на p_entry
    (куда ВХОДИТ труба). Так как clamp_cyl держит болт у дальнего от origin торца
    (z=height), болт-стяжка + проушины оказываются на ВХОДНОМ торце — где труба
    точно внутри. Возвращает размещённый trimesh для union."""
    p_blind = np.asarray(p_blind, float)
    p_entry = np.asarray(p_entry, float)
    tube_dir = p_entry - p_blind
    tube_dir = tube_dir / np.linalg.norm(tube_dir)      # направление ИЗ координат концов
    return place_clamp(height, p_blind, tube_dir, slit_dir)


def finish(mesh, name, reorient=None):
    """Сварить вершины, валидировать, ВЫБРОСИТЬ мусорные тела (оставить самое
    крупное), опционально переориентировать в позу печати, посадить z_min=0."""
    OUTDIR.mkdir(parents=True, exist_ok=True)
    mesh.merge_vertices(digits_vertex=5)
    mesh.process(validate=True)
    # выбросить отпавшие мусорные тела — оставить самое крупное по объёму
    parts = mesh.split(only_watertight=False)
    if len(parts) > 1:
        mesh = max(parts, key=lambda m: m.volume)
    if reorient is not None:
        mesh.apply_transform(reorient)
    mesh.merge_vertices()
    mesh.process(validate=True)
    mesh.apply_translation([0, 0, -mesh.bounds[0, 2]])   # плоская грань на стол
    out = OUTDIR / f"{name}.stl"
    mesh.export(out)
    bb = mesh.bounds
    print(f"  {name}.stl  watertight={mesh.is_watertight}  vol={mesh.volume/1000:.2f}cm³  "
          f"bbox={bb[1,0]-bb[0,0]:.0f}×{bb[1,1]-bb[0,1]:.0f}×{bb[1,2]-bb[0,2]:.0f}mm")
    return mesh


def bore_cut(origin, tube_dir, length, r=11.2):
    """Цилиндр-вырез Ø22.4 (бор трубы) вдоль оси сокета от `origin` наружу на
    `length` — переоткрывает бор ПОСЛЕ приварки ядра/стопы: убирает материал,
    залезший в полый бор, но НЕ трогает стенки хомута (кольцо R11.2..15.2) → сварка
    цела, а труба садится на полную глубину."""
    d = np.asarray(tube_dir, float); d /= np.linalg.norm(d)
    center = np.asarray(origin, float) + d * (length / 2.0)
    R = trimesh.geometry.align_vectors([0, 0, 1], d)
    R[:3, 3] = center
    return cyl(r, length, seg=48, T=R)


def tube_fit_socket(part, origin, tube_dir, height, grip=TUBE_FIT_GRIP):
    """Ø22 цилиндр длиной grip от ВХОДА бора (дальний торец хомута, origin+dir*height)
    ВНУТРЬ (к origin) — пересекаем с телом узла. Труба обязана сидеть в ПОЛОМ боре ⇒
    пересечение с телом < 8% объёма трубы. Возвращает долю заполнения."""
    o = np.asarray(origin, float)
    d = np.asarray(tube_dir, float); d /= np.linalg.norm(d)
    entry = o + d * height                       # торец, куда входит труба
    center = entry - d * (grip / 2.0)            # центр тестового цилиндра
    R = trimesh.geometry.align_vectors([0, 0, 1], d)   # ось +Z → dir
    R[:3, 3] = center
    tube = cyl(TUBE_FIT_D / 2, grip, seg=48, T=R)
    v_tube = math.pi * (TUBE_FIT_D / 2) ** 2 * grip
    try:
        it = trimesh.boolean.intersection([part, tube], engine=ENGINE)
        v_it = abs(it.volume) if it is not None and len(it.faces) else 0.0
    except Exception:
        v_it = float("nan")
    return v_it / v_tube


def run_tube_fit(part, sockets):
    """Печатает PASS/FAIL посадки трубы на полную глубину грипа для каждого сокета."""
    print(f"  ТЕСТ ПОСАДКИ ТРУБ (Ø{TUBE_FIT_D:.0f}×{TUBE_FIT_GRIP:.0f} от входа бора внутрь; "
          f"PASS <{TUBE_FIT_MAX*100:.0f}%):")
    ok_all = True
    for nm, o, d, h in sockets:
        frac = tube_fit_socket(part, o, d, h)
        ok = frac < TUBE_FIT_MAX
        ok_all = ok_all and ok
        print(f"    {nm:16s} заполнение {frac*100:5.1f}%  {'PASS' if ok else 'FAIL'}")
    return ok_all


# ============================ 1. ХАБ ============================
def rocker_hub_truss():
    """3 чистых хомута из ЦЕНТРА наружу под 120° (направления — из координат концов
    труб) + маленькое ядро-цилиндр + сквозной бор M10 и гекс-карман гайки снизу.
    Прорезь вверх. Болт-на-входе: origin у центра (глухой), ось наружу → болт у
    R≈40, где труба уже внутри (труба стартует R35). Поза печати: ось M10
    вертикальна, плоское дно ядра на столе."""
    hub = np.array([0.0, 0.0, Z_ARM])                    # глухой центр (origin хомутов)
    clamps = []
    sockets = []
    for ang in CORNER_ANGLES:
        _, p_out = tube_pts(ang)                         # внешний конец трубы (лапа)
        d = (p_out - hub); d = d / np.linalg.norm(d)     # ось хаб→лапа
        clamps.append(clamp_entry(hub, p_out, HUB_CLAMP_H))   # болт снаружи (вход трубы)
        sockets.append((f"hub_{ang:.0f}", hub, d, HUB_CLAMP_H))
    core = cyl(HUB_CORE_R, HUB_CORE_H, T=tr(0, 0, Z_ARM))     # минимальное ядро-склейка
    part = core.union(clamps)

    m10 = cyl(M10_CLR / 2, 80, T=tr(0, 0, Z_ARM))
    nut = cyl(NUT10_AF / math.sqrt(3), NUT10_DEPTH, seg=6,
              T=tr(0, 0, Z_ARM - 24 + 4))                     # карман открыт вниз
    # СКВОЗНАЯ расточка бора Ø22.4 по каждому лучу — ядро НЕ должно заполнять полый
    # бор (иначе труба не садится на полный грип). Стенки хомута (кольцо снаружи
    # бора) целы → сварка держит, а бор чист.
    bores = [bore_cut(hub - d * 3.0, d, HUB_CLAMP_H + 3.0) for _, _, d, _ in sockets]
    part = part.difference([m10, nut] + bores)
    run_tube_fit(part, sockets)                              # труба входит на полный грип?
    return finish(part, "Rocker_hub_truss")


# ============================ 2. ЛАПА ============================
def rocker_leg_truss():
    """Один горизонтальный радиальный хомут (грип R243..R285, ось z=32) + одна
    МИНИМАЛЬНАЯ плоская стопа-пад (прямоугольная коробка, НЕ дуга) на пол +
    юстировочный M4 по центру. Прорезь вверх. Болт-на-входе: origin у ТЕРМИНАЛА
    трубы (R285), ось К ХАБУ → болт у R≈243, откуда труба входит от хаба. Поза
    печати: стопа плоско на столе (z=0)."""
    p_in, p_out = tube_pts(0.0)                          # луч ang=0 (печатается ×3)
    clamp = clamp_entry(p_out, p_in, CLAMP_H_ARM)        # origin=терминал R285, ось→хаб

    r_ctr = R_TUBE_OUT - CLAMP_H_ARM / 2.0               # центр хомута ≈ R264
    foot = box(CLAMP_H_ARM, LEG_FOOT_W, LEG_FOOT_TOP,
               T=tr(r_ctr, 0, LEG_FOOT_TOP / 2))         # z=0..30, варится с низом хомута
    part = clamp.union(foot)

    tap = cyl(M4_TAP / 2, 24, seg=32, T=tr(r_ctr, 0, 11))     # M4 винт-ножка (самонарез)
    d = (p_in - p_out); d = d / np.linalg.norm(d)             # ось терминал→хаб
    # расточка бора Ø22.4: стопа-пад приварена к НИЗУ хомута, но её верх (z=30)
    # лез в полый бор (ось z=32) и не давал трубе сесть. Убираем материал внутри
    # бора — стопа держится за стенки хомута снаружи бора.
    bore = bore_cut(p_out, d, CLAMP_H_ARM)
    part = part.difference([tap, bore])
    run_tube_fit(part, [("leg", p_out, d, CLAMP_H_ARM)])
    return finish(part, "Rocker_leg_truss")


# ============================ 3. ТРУБНОЕ СЕДЛО ВЕНЦА ============================
def rocker_ring_saddle_tube():
    """Один чистый ПРОЛЁТНЫЙ хомут на трубе (грип R150..R192, труба сквозная,
    прорезь ВВЕРХ свободна) + один МИНИМАЛЬНЫЙ плоский седловой таб СБОКУ (смещён
    по +Y, мимо трубы Ø22 и мимо проушин), радиально наружу до-под тела венца, верх
    плоский на z=50. Никаких дуг R200. Болт-на-входе: origin у внутр. торца, ось
    наружу → болт у наружного торца, где труба сквозная (внутри), вне седла. Поза
    печати: бор поставлен ВЕРТИКАЛЬНО (канон хомута), торец на столе."""
    sad_in = np.array(polar(SAD_CLAMP_R0, 0.0, Z_ARM))       # внутр. торец грипа R150
    _, p_out = tube_pts(0.0)                                 # наружу к лапе — ось трубы
    clamp = clamp_entry(sad_in, p_out, CLAMP_H_ARM)          # болт у наружного торца

    seat = box(SEAT_R_OUT - SEAT_R_IN, SEAT_Y_OUT - SEAT_Y_IN, SEAT_TOP - SEAT_Z0,
               T=tr((SEAT_R_IN + SEAT_R_OUT) / 2,
                    (SEAT_Y_IN + SEAT_Y_OUT) / 2,
                    (SEAT_Z0 + SEAT_TOP) / 2))
    part = clamp.union(seat)

    d = (p_out - sad_in); d = d / np.linalg.norm(d)           # ось наружу (труба сквозная)
    run_tube_fit(part, [("ring_saddle", sad_in, d, CLAMP_H_ARM)])
    # переориентация: бор радиальный (+X) → вертикаль (+Z), печать без поддержек
    return finish(part, "Rocker_ring_saddle_tube", reorient=roty(-90))


def main():
    print("Генерация наземной звезды рокера (трубная рама, минимал)…")
    print(f"  ось труб z={Z_ARM:.0f}, хомут-грип {CLAMP_H_ARM:.0f}мм, воротник "
          f"Ø{CLAMP_OD:.0f}; венец на 3 сёдлах z={RING_Z:.0f}")
    print(f"  труба хаб→лапа: радиальный пролёт R{R_TUBE_IN:.0f}→R{R_TUBE_OUT:.0f} ≈ "
          f"{TUBE_SPAN:.0f}мм, Ø{TUBE_OD:.0f}, ×3 (направления из координат концов)")
    rocker_hub_truss()
    rocker_leg_truss()
    rocker_ring_saddle_tube()
    print(f"\nГотово → {OUTDIR}")
    print("Количества: хаб ×1, лапа ×3, трубное седло ×3.")
    print(f"Трубы Ø22 алюминий: 3× по ~{TUBE_SPAN:.0f}мм (R{R_TUBE_IN:.0f}→R{R_TUBE_OUT:.0f}).")


if __name__ == "__main__":
    main()
