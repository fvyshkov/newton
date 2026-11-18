#!/usr/bin/env python3
"""
Держатели энкодеров AS5048A для ФАНЕРНОГО ровербокса — v2, ПО РЕАЛЬНЫМ ОБМЕРАМ
(26.07.2026, все посадки калиброваны пробниками gen_fit_coupon.py, PLA, левое сопло 0.4).

СХЕМА (отличается от v1! обмеры перевернули азимут):
  АЗИМУТ: болт Ø6.2 (~1/4") вклеен в НЕПОДВИЖНУЮ опорную доску, торчит ВВЕРХ
    внутрь коробки на 15.5 мм. Колпачок-гайка (бор Ø6.2 — победитель раунда-2)
    накручивается магнитом ВВЕРХ и стоит неподвижно. ЧИП смотрит ВНИЗ с мостика,
    прикрученного ко дну коробки; коробка вращается — чип едет вокруг магнита.
  ВЫСОТА: колесо Ø200 (обмер Rover Box Weel.stl): 3 болта-конца Ø4.7 торчат
    ~3.15 на R15.4 (стороны треугольника 26.6/26.6/26.9). Колпачок-«трилистник»
    садится гнёздами Ø4.4 (победитель) на концы болтов, магнит в центре = на оси.
    Колесо утоплено ~1 мм за наружную плоскость стенки (16.5 мм фанера).
    ЧИП — на мосту через V-вырез: пролёт ~250 между верхушками, ось на ~30 выше.

Детали (все в ПОЗЕ ПЕЧАТИ, z=0):
  v2_az_cap_hex.stl      — колпачок-гайка азимута (шестигранник под ключ 13)
  v2_az_bridge.stl       — мостик-козлик на дно коробки (печать вверх ногами)
  v2_alt_cap_trefoil.stl — трилистник на колесо (гнёздами вверх)
  v2_alt_bridge.stl      — мост через V-вырез (печать наружной гранью вниз)
  v2_shims.stl           — 4 прокладки 0.6 мм под лапы (юстировка зазора)
  fit_pins_coupon.stl    — пробник посадки платы на штырьки (печатать ПЕРВЫМ, ~5 мин)
  STOL_shtyrki.stl       — оба моста для перепечатки под плату-малютку

Крепёж: саморезы Ø3.5-4 в фанеру (слоты). Плата — БЕЗ винтов: приехала
«малютка» 15×17 (обмер 01.08.2026: 2 дырки Ø≈2.1, межцентровое 12.0 —
первый обмер 10.5 оказался тесен, 13.08 штырьки раздвинуты на +1.5, чип
ровно посередине, гребёнки нет) — надевается дырками на 2 штырька, клин у
корня штыря затягивает её туго при досадке до бобышек. Провода паять со
стороны мостика (там зазор 2.4 мм), НЕ со стороны чипа (там магнит в 1.5 мм).
Запуск: /opt/homebrew/bin/python3 gen_encoder_holders_v2.py
"""
import numpy as np
import trimesh
from trimesh.creation import box as _box, cylinder as _cyl, cone as _cone
from trimesh.transformations import rotation_matrix as rotmat
from pathlib import Path

OUT = Path(__file__).parent / 'stl' / 'encoder'
SEG = 96

# ---------- обмеры / посадки (ФАКТ, не менять без новой примерки) ----------
AZ_BOLT_D, AZ_BOLT_PROT = 6.2, 15.5   # болт и его вылет над дном коробки
AZ_BORE, AZ_BORE_DEPTH = 6.2, 9.0     # победитель раунда-2 (2 канавки)
ALT_SOCKET_D, ALT_SOCKET_DEPTH = 4.6, 3.6   # пробник-победитель 4.4 (одиночный!)
# +0.2: три штыря сразу — разброс треугольника ±0.15 съедает одиночный зазор,
# плюс гнёзда печатаются у стола (слоновья нога поджимает). Фаска-заход ниже.
ALT_BOLT_R, N_SOCK = 15.4, 3          # окружность концов болтов
WHEEL_RECESS = 1.0                    # колесо утоплено за плоскость стенки
V_SPAN = 250.0                        # между верхушками V
AXIS_ABOVE_TOPS = 30.0                # ось колеса выше верхушек V

# ---------- магнит / плата (проверено ранее) ----------
MAG_D, MAG_H, MAG_FIT, MAG_RECESS = 6.0, 2.5, 0.2, 0.4
STEEL_STANDOFF = 5.0                  # пластик между магнитом и сталью болта
# плата-«малютка» (обмер 01.08.2026, НЕ синяя 28×22!): 15×17, 2 дырки на
# линии через чип, чип ровно посередине; посадка на штырьки, туго, без винтов
BRD_L, BRD_W, BRD_T = 17.0, 15.0, 1.6
PIN_PITCH = 12.0                      # межцентровое дырок (обмер 10.5 промахнулся:
                                      # напечатанные штырьки встали впритык, 13.08 +1.5)
PIN_SHANK_D = 2.0                     # стержень — свободно в дырку Ø2.1-2.2
PIN_ROOT_D = 2.35                     # клин у корня: последние 0.8 мм затягивают
PIN_FLARE_H = 0.8
PIN_TIP_D, PIN_TIP_H = 1.2, 1.1       # заходный конус на кончике
PIN_OVER = 0.4                        # стержень за платой (кончик смотрит на магнит!)
PAD_OD, PAD_H = 5.5, 2.4              # бобышки вокруг штырей; 2.4 — канал под пайку
CHIP_H = 1.1                          # высота корпуса чипа над платой
AIR_GAP = 1.5                         # зазор чип-магнит
CHIP_STACK = PAD_H + BRD_T + CHIP_H   # бобышка->лицо чипа = 5.1
PIN_REACH = PAD_H + BRD_T + PIN_OVER + PIN_TIP_H  # полка->кончик штыря = 5.5
                                      # кончики всего на 0.4 ниже лица чипа

FOOT_SCREW_R = 2.15                   # слоты под саморез Ø3.5-4
SHELF_T = 2.4

def at(m, x, y, z):
    m.apply_translation([x, y, z]); return m

def cyl(r, h, seg=SEG): return _cyl(radius=r, height=h, sections=seg)
def diff(a, cuts): return trimesh.boolean.difference([a] + cuts, engine='manifold')
def uni(parts): return trimesh.boolean.union(parts, engine='manifold')

def slot_cut(length, r, h):
    """слот со скруглениями, ось вдоль X, центр в 0"""
    s = uni([at(_box(extents=[length, 2*r, h]), 0, 0, 0),
             at(cyl(r, h, 48), -length/2, 0, 0),
             at(cyl(r, h, 48),  length/2, 0, 0)])
    return s

def magnet_pocket(cx, cy, ztop):
    """карман магнита, открытый вверх, магнит утоплен на MAG_RECESS"""
    return at(cyl((MAG_D + MAG_FIT)/2, MAG_H + MAG_RECESS + 0.2, 64),
              cx, cy, ztop - (MAG_H + MAG_RECESS + 0.2)/2 + 0.1)

def frustum(r_bot, r_top, h, seg=48):
    """усечённый конус, центр в 0, широкое основание снизу (z=-h/2)"""
    m = _cyl(radius=r_bot, height=h, sections=seg)
    v = m.vertices.copy()
    top = v[:, 2] > 0
    v[top, 0] *= r_top / r_bot
    v[top, 1] *= r_top / r_bot
    m.vertices = v
    return m

def pin_solids(px, py, zf, up):
    """бобышка + штырь под дырку платы: стержень Ø2 проходит свободно,
    клин у корня (2.0→2.35 на последних 0.8 мм) затягивает плату ТУГО
    при досадке до бобышки; на кончике заходный конус."""
    sh_l = BRD_T + PIN_OVER
    parts = [at(cyl(PAD_OD/2, PAD_H, 48), px, py, zf + up*PAD_H/2),
             at(cyl(PIN_SHANK_D/2, sh_l, 48), px, py, zf + up*(PAD_H + sh_l/2))]
    flare = frustum(PIN_ROOT_D/2, PIN_SHANK_D/2, PIN_FLARE_H)
    tip = frustum(PIN_SHANK_D/2, PIN_TIP_D/2, PIN_TIP_H)
    if up < 0:
        flare.apply_transform(rotmat(np.pi, [1, 0, 0]))
        tip.apply_transform(rotmat(np.pi, [1, 0, 0]))
    parts.append(at(flare, px, py, zf + up*(PAD_H + PIN_FLARE_H/2)))
    parts.append(at(tip, px, py, zf + up*(PAD_H + sh_l + PIN_TIP_H/2)))
    return parts

def board_pad(shelf, cx, cy, z_shelf_face, up=+1):
    """посадка платы-малютки: 2 штырька по PIN_PITCH вдоль X, чип в (cx,cy).
    Возвращает (тело со штырьками, []) — резьбовых отверстий больше нет."""
    parts = []
    for sx in (-1, 1):
        parts += pin_solids(cx + sx*PIN_PITCH/2, cy, z_shelf_face, up)
    return uni([shelf] + parts), []

# ============================================================
# 1. Колпачок-гайка азимута (печать: бором ВНИЗ = магнитом вверх? нет —
#    печатаем как пробник, бором вверх; магнитный карман на нижней грани
#    печати = верх в сборке... проще: бор снизу в сборке, магнит сверху.
#    ПЕЧАТЬ: магнитным карманом ВВЕРХ, бор вниз->это roof Ø6.2 — плохо.
#    Решение: печать бором ВВЕРХ (как пробник, посадка важнее), карман
#    магнита снизу как neat roof Ø6.2x2.9 — допустимо, магнит на клей.
#    В СБОРКЕ деталь переворачивается бором вниз.
# ============================================================
HEX_AF = 13.0
hex_R = HEX_AF / np.sqrt(3.0)
CAP_H = AZ_BORE_DEPTH + STEEL_STANDOFF + MAG_H + MAG_RECESS  # 16.9

body = at(cyl(hex_R, CAP_H, 6), 0, 0, CAP_H/2)
bore = at(cyl(AZ_BORE/2, AZ_BORE_DEPTH + 0.2, 64), 0, 0, CAP_H - AZ_BORE_DEPTH/2 + 0.1)
rb = AZ_BORE/2 + 1.2
cham = _cone(radius=rb, height=rb, sections=64)
cham.apply_transform(rotmat(np.pi, [1, 0, 0]))
cham = at(cham, 0, 0, CAP_H + 0.01)
mag_dn = at(cyl((MAG_D + MAG_FIT)/2, MAG_H + MAG_RECESS + 0.2, 64),
            0, 0, (MAG_H + MAG_RECESS + 0.2)/2 - 0.1)
az_cap = diff(body, [bore, cham, mag_dn])

# ============================================================
# 2. Мостик-козлик азимута (сборка: дно коробки z=0)
# ============================================================
CAP_BOT = AZ_BOLT_PROT - AZ_BORE_DEPTH            # 6.5 над дном
MAG_FACE_AZ = CAP_BOT + CAP_H - MAG_RECESS        # 23.0
SHELF_BOT = MAG_FACE_AZ + AIR_GAP + CHIP_STACK    # 29.6 (низ полки)
LEG_X, LEG_T, BAR_W = 36.0, 8.0, 26.0             # легс на ±36, бар 26 шир.
SOLE_L, SOLE_W, SOLE_T = 30.0, 22.0, 5.0

bar = at(_box(extents=[2*LEG_X + LEG_T, BAR_W, SHELF_T]),
         0, 0, SHELF_BOT + SHELF_T/2)
legs = [at(_box(extents=[LEG_T, BAR_W, SHELF_BOT]), sx*LEG_X, 0, SHELF_BOT/2)
        for sx in (-1, 1)]
soles = [at(_box(extents=[SOLE_L, SOLE_W, SOLE_T]),
            sx*(LEG_X + LEG_T/2 + SOLE_L/2 - 4), 0, SOLE_T/2) for sx in (-1, 1)]
az_body = uni([bar] + legs + soles)
az_body, taps = board_pad(az_body, 0, 0, SHELF_BOT, up=-1)
cuts = list(taps)
for sx in (-1, 1):                                 # слоты в лапах, вдоль X
    scx = sx*(LEG_X + LEG_T/2 + SOLE_L/2 - 4)
    for sy in (-1, 1):
        cuts.append(at(slot_cut(8.0, FOOT_SCREW_R, SOLE_T + 2), scx, sy*6.5, SOLE_T/2))
az_bridge = diff(az_body, cuts)
# печать вверх ногами
az_bridge.apply_transform(rotmat(np.pi, [1, 0, 0]))
az_bridge.apply_translation([0, 0, -az_bridge.bounds[0][2]])

# проверка зазоров (в сборке): чип 24.5, магнит 23.0, верх колпачка 23.4
chip_face = SHELF_BOT - CHIP_STACK
cap_top = CAP_BOT + CAP_H
assert abs((chip_face - MAG_FACE_AZ) - AIR_GAP) < 1e-6
az_clear_rim = chip_face - cap_top                 # чип над ободом колпачка
az_pin_clear = (SHELF_BOT - PIN_REACH) - cap_top   # кончики штырей над ободом
assert az_pin_clear >= 0.5, f'штыри азимута цепляют колпачок: {az_pin_clear:.2f}'

# ============================================================
# 3. Трилистник высоты (сборка: наружная плоскость колеса = z0, наружу +z)
#    ПЕЧАТЬ: гнёздами вверх (посадка точнее), карман магнита — roof.
# ============================================================
TRE_D, TRE_T = 38.0, 8.0
HEAD_RELIEF = 1.5           # кольцевая проточка под кончики штырей платы моста
RELIEF_R_IN = 3.8           # штыри метут кольцо r 4.1..6.4 — с запасом 0.3
tre = at(cyl(TRE_D/2, TRE_T, SEG), 0, 0, TRE_T/2)
cuts = [magnet_pocket(0, 0, TRE_T)]
relief = diff(at(cyl(13.0, HEAD_RELIEF + 0.2, SEG), 0, 0, TRE_T - HEAD_RELIEF/2 + 0.1),
              [at(cyl(RELIEF_R_IN, HEAD_RELIEF + 0.6, 64), 0, 0, TRE_T - HEAD_RELIEF/2 + 0.1)])
cuts.append(relief)         # проточка r3.8..13, бобышка магнита в центре остаётся
# штыри (r 5.25±1.18) должны мести СТРОГО внутри проточки
assert RELIEF_R_IN <= PIN_PITCH/2 - PIN_ROOT_D/2 - 0.2, 'проточка уже размаха штырей'
assert PIN_PITCH/2 + PIN_ROOT_D/2 + 0.2 <= 13.0, 'штыри вылезают за проточку'
for k in range(N_SOCK):
    a = np.radians(90 + 120*k)
    sx, sy = ALT_BOLT_R*np.cos(a), ALT_BOLT_R*np.sin(a)
    cuts.append(at(cyl(ALT_SOCKET_D/2, ALT_SOCKET_DEPTH + 0.2, 48),
                   sx, sy, ALT_SOCKET_DEPTH/2 - 0.1))
    rch = ALT_SOCKET_D/2 + 0.8                 # фаска-заход 45° на устье (у стола)
    ch = _cone(radius=rch, height=rch, sections=48)
    cuts.append(at(ch, sx, sy, -0.01))
alt_cap = diff(tre, cuts)   # гнёзда снизу (z0), магнит сверху — уже поза печати
                            # (в сборке гнёздами к колесу, магнитом наружу)

# ============================================================
# 4. Мост высоты — А-РАМА на склоны V (стенка ВСЕГО 250 шириной, за
#    верхушками V фанеры НЕТ; на высоте −70 от оси доска сплошная от ±71).
#    Координаты сборки: x вдоль стены, y вверх (0 = ось колеса), z наружу
#    от наружной плоскости стенки (0 = стенка).
# ============================================================
MAG_FACE_ALT = -WHEEL_RECESS + TRE_T - MAG_RECESS       # +6.6 от стенки
SHELF_IN = MAG_FACE_ALT + AIR_GAP + CHIP_STACK          # +13.2 (внутр. грань)
FOOT_XC, FOOT_YC = 97.0, -75.0        # центры лап на склонах; саморезы ≥9мм от кромки V
FOOT_W, FOOT_H, FOOT_T = 25.0, 35.0, 6.0
HUB_L, HUB_W = 40.0, 32.0             # площадка платы вокруг чипа
ARM_W = 20.0

hub = at(_box(extents=[HUB_L, HUB_W, SHELF_T]), 0, 0, SHELF_IN + SHELF_T/2)
alt_parts = [hub]
for sx in (-1, 1):
    # лапа на стене + стойка до плоскости полки (r≈118 — вне колеса R100)
    alt_parts.append(at(_box(extents=[FOOT_W, FOOT_H, FOOT_T]),
                        sx*FOOT_XC, FOOT_YC, FOOT_T/2))
    alt_parts.append(at(_box(extents=[FOOT_W, ARM_W, SHELF_IN + SHELF_T]),
                        sx*FOOT_XC, FOOT_YC, (SHELF_IN + SHELF_T)/2))
    # плечо от ступицы к стойке (в плоскости полки, над колесом z>=12)
    ang = np.arctan2(FOOT_YC, sx*FOOT_XC)
    arm = _box(extents=[np.hypot(FOOT_XC, FOOT_YC), ARM_W, SHELF_T])
    arm.apply_transform(rotmat(ang, [0, 0, 1]))
    alt_parts.append(at(arm, sx*FOOT_XC/2, FOOT_YC/2, SHELF_IN + SHELF_T/2))
# поперечная связка между плечами (треугольник жёсткости)
alt_parts.append(at(_box(extents=[120.0, 12.0, SHELF_T]),
                    0, -42.0, SHELF_IN + SHELF_T/2))
alt_body = uni(alt_parts)
alt_body, taps = board_pad(alt_body, 0, 0, SHELF_IN, up=-1)
cuts = list(taps)
for sx, vert in ((-1, True), (1, False)):          # слева вертикальные, справа гориз.
    for k in (-1, 1):
        s = slot_cut(12.0, FOOT_SCREW_R, FOOT_T + 2)
        if vert:
            s.apply_transform(rotmat(np.pi/2, [0, 0, 1]))
            s = at(s, sx*FOOT_XC + k*8, FOOT_YC, FOOT_T/2)
        else:
            s = at(s, sx*FOOT_XC, FOOT_YC + k*11, FOOT_T/2)
        cuts.append(s)
alt_bridge = diff(alt_body, cuts)

# проверки высоты: чип-магнит зазор; трилистник не задевает мост (штыри
# опускаются ниже верха трилистника ТОЛЬКО над проточкой — см. asserts выше)
chipA = SHELF_IN - CHIP_STACK
assert abs((chipA - MAG_FACE_ALT) - AIR_GAP) < 1e-6
tre_top = -WHEEL_RECESS + TRE_T                    # верхняя плоскость трилистника
alt_pin_clear = (SHELF_IN - PIN_REACH) - tre_top   # кончики штырей над плоскостью
assert alt_pin_clear >= 0.5, f'штыри высоты цепляют трилистник: {alt_pin_clear:.2f}'
sweep = at(cyl(TRE_D/2 + 1.5, tre_top + WHEEL_RECESS, 64),
           0, 0, (tre_top - WHEEL_RECESS)/2)
inter = trimesh.boolean.intersection([alt_bridge, sweep], engine='manifold')
alt_hit = 0.0 if (inter is None or inter.is_empty) else inter.volume

# поза печати: наружной гранью вниз (бар на столе), лапы на поддержках
alt_bridge.apply_transform(rotmat(np.pi, [1, 0, 0]))
alt_bridge.apply_translation([0, 0, -alt_bridge.bounds[0][2]])

# ============================================================
# 5. Прокладки
# ============================================================
shims = []
for i in range(4):
    sh = diff(at(_box(extents=[28, 20, 0.6]), i*34, 60, 0.3),
              [at(slot_cut(8.0, FOOT_SCREW_R, 2), i*34, 60, 0.3)])
    shims.append(sh)
shim_plate = trimesh.util.concatenate(shims)

# ============================================================
OUT.mkdir(parents=True, exist_ok=True)
report = []
for name, m in [('v2_az_cap_hex', az_cap), ('v2_az_bridge', az_bridge),
                ('v2_alt_cap_trefoil', alt_cap), ('v2_alt_bridge', alt_bridge),
                ('v2_shims', shim_plate)]:
    m.export(OUT / f'{name}.stl')
    bb = np.round(m.bounds[1] - m.bounds[0], 1)
    report.append(f'{name}: bbox {bb} vol {m.volume/1000:.1f}cm3 wt={m.is_watertight}')
print('\n'.join(report))
print(f'AZ: магнит {MAG_FACE_AZ:.1f} над дном, чип {chip_face:.1f}, зазор {AIR_GAP}, '
      f'чип над ободом колпачка {az_clear_rim:.1f}мм, штыри над ободом '
      f'{az_pin_clear:.1f}мм (оба >0.5)')
print(f'ALT: магнит +{MAG_FACE_ALT:.1f} от стенки, чип +{chipA:.1f}, штыри над '
      f'трилистником {alt_pin_clear:.1f}мм (>0.5, над проточкой +{HEAD_RELIEF}), '
      f'пересечение трилистник∩мост = {alt_hit:.3f} см3 (должно быть 0)')

# ============================================================
# 6. ОБЩИЙ СТОЛ: все 5 деталей в позах печати, длинный мост — центральной
#    полосой (углы стола H2D режутся зонами сопел, середина безопасна).
# ============================================================
def place(m, tx, ty):
    c = m.copy()
    lo, hi = c.bounds
    c.apply_translation([tx - (lo[0]+hi[0])/2, ty - (lo[1]+hi[1])/2, -lo[2]])
    return c

stol = trimesh.util.concatenate([
    place(alt_bridge, 0, 0),        # А-рама ~220×110, центр
    place(az_bridge, 0, 76),        # козлик, верхняя полоса
    place(alt_cap, -85, -78),       # трилистник, нижняя полоса
    place(shim_plate, 10, -78),     # прокладки, нижняя полоса
    place(az_cap, 95, -78),         # колпачок-гайка, нижняя полоса
])
stol.export(OUT / 'STOL_pushto_v2.stl')
bb = np.round(stol.bounds[1] - stol.bounds[0], 1)
print(f'STOL_pushto_v2: bbox {bb} (центрировать на столе H2D)')

# стол «штырьки» (01.08): приехала плата-малютка 15×17 (2 дырки/10.5) вместо
# синей 28×22/4 дырки — перепечатать ОБА моста (посадка теперь штыри, тугая).
# Колпачки и прокладки от прошлой печати годны. Трилистник: проточка стала
# шире (r3.8..13) под метущие штыри — если уже напечатан старый (r4.8..13),
# он ГОДЕН: штыри в него не достают (зазор 0.7 над плоскостью, проточка
# нужна только как страховка при юстировке) — но лучше перепечатать.
coupon = uni([at(_box(extents=[30, 14, 3.0]), 0, 0, 1.5)]
             + pin_solids(-PIN_PITCH/2, 0, 3.0, +1)
             + pin_solids(+PIN_PITCH/2, 0, 3.0, +1))
coupon.export(OUT / 'fit_pins_coupon.stl')
print(f'fit_pins_coupon: bbox {np.round(coupon.bounds[1]-coupon.bounds[0],1)} '
      f'— печатать ПЕРВЫМ, плата должна досаживаться до бобышек туго')
pins_meshes = [place(alt_bridge, 0, 0), place(az_bridge, 0, 76)]
for m in pins_meshes:
    m.merge_vertices()   # без слияния Bambu считает меш дырявым (см. _az2_export_bambu)
trimesh.Scene(pins_meshes).export(OUT / 'STOL_shtyrki.3mf')
stol_pins = trimesh.util.concatenate(pins_meshes)
stol_pins.export(OUT / 'STOL_shtyrki.stl')
bb = np.round(stol_pins.bounds[1] - stol_pins.bounds[0], 1)
print(f'STOL_shtyrki: bbox {bb} → .3mf + .stl')
