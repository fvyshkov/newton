#!/usr/bin/env python3
"""
Энкодер ВЫСОТЫ v3 «на поводке» для фанерного ровербокса (build123d, B-rep).

Идея (страница https://begemot.pebble.ink/enkoder-povodok/): чип и магнит держит
СВОЙ подшипник 608ZZ — они всегда соосны. Коробка только не даёт чипу крутиться:
длинный поводок упирается пазом в штырь на стенке. Люфт колеса в V уходит в паз,
ошибка ≈ люфт / R_поводка (0,5 мм / 140 → ~12′) вместо ~1° у v2 (чип на мосту).

Координаты СБОРКИ (мм): начало = ось колеса в плоскости НАРУЖНОЙ грани стенки,
+z наружу (от телескопа), y вверх, x вдоль стенки.
  колесо Ø200 (Rover Box Weel.stl): наружная грань z=-1 (утоплено на 1),
  3 отверстия Ø4.7 на R15.4 (30/150/270°), сплошное тело до r≈38, дальше окна;
  концы болтов торчат на 3.15 (обмер 26.07).
  стенка 16.5, ширина 250 (±125), V: верхушки y=-30, дно y=-140 (обмеры v2).

Детали (печать PLA, ЛЕВОЕ сопло 0.4):
  v3_fit_bearing.stl  — ПРОБНИК посадок 608ZZ: 3 стакана (Ø22.00/22.15/22.30) и
                        3 шипа (Ø7.85/7.95/8.05), риски 1/2/3. Печатать ПЕРВЫМ.
  v3_alt_hub.stl      — ступица: диск Ø56 гнёздами на концы болтов колеса +
                        клей, шип под подшипник, магнит Ø6×2.5 в торце шипа.
  v3_alt_carrier.stl  — стакан с чипом + поводок R140 с пазом (одна деталь).
  v3_alt_post.stl     — штырь Ø8 на площадке, 2 самореза в стенку.
  *.step              — то же в STEP.

Запуск:  ./.venv-cad/bin/python gen_encoder_lever_alt.py
После пробника: вписать победителей в SPIGOT_D / POCKET_D и перезапустить.
"""
from pathlib import Path
import math

from build123d import (Align, Box, Cone, Cylinder, Pos, Rot, RegularPolygon,
                       SlotCenterToCenter, RectangleRounded, extrude, export_stl,
                       export_step)

OUT = Path(__file__).parent / 'stl' / 'encoder'
MIN = (Align.CENTER, Align.CENTER, Align.MIN)

# ---------------- посадки (ПОСЛЕ ПРОБНИКА поменять на победителей) ----------------
SPIGOT_D = 7.95          # шип под внутреннее кольцо 608 (Ø8): риска 2 пробника
POCKET_D = 22.15         # стакан под наружное кольцо 608 (Ø22): риска 2 пробника
SPIGOT_TRY = [7.85, 7.95, 8.05]
POCKET_TRY = [22.00, 22.15, 22.30]

# ---------------- колесо / стенка (обмеры) ----------------
WHEEL_FACE_Z = -1.0      # наружная грань колеса (утоплено на 1 мм)
BOLT_R, BOLT_ANG = 15.4, (30, 150, 270)
BOLT_PROT = 3.15         # концы болтов над гранью колеса
SOCKET_D, SOCKET_DEPTH = 4.6, 3.6   # из v2 (пробник 4.4 + 0.2 на три штыря сразу)
WHEEL_SOLID_R = 38.0     # до этого радиуса грань колеса сплошная (окна дальше)
WALL_T, WALL_HALF_W = 16.5, 125.0
V_TOP_Y, V_BOT_Y = -30.0, -140.0

# ---------------- подшипник 608ZZ / магнит / плата ----------------
BRG_OD, BRG_ID, BRG_W = 22.0, 8.0, 7.0
BRG_IN_RING_OD, BRG_OUT_RING_ID = 12.1, 19.0
MAG_D, MAG_H, MAG_FIT, MAG_RECESS = 6.0, 2.5, 0.2, 0.4
AIR_GAP = 1.5
BRD_L, BRD_W, BRD_T = 17.0, 15.0, 1.6   # плата-малютка, 2 дырки Ø2.1 на 12.0
PIN_PITCH = 12.0
PIN_SHANK_D, PIN_ROOT_D, PIN_FLARE_H = 2.0, 2.35, 0.8
PIN_TIP_D, PIN_TIP_H, PIN_OVER = 1.2, 1.1, 0.4
BOSS_D, BOSS_H = 5.5, 1.2      # плата лежит чипом К МАГНИТУ, под ней 1.2 на детальки
CHIP_H = 1.1

# ---------------- ступица (z в сборке) ----------------
HUB_D, HUB_T = 56.0, 5.0                  # диск z -1..4 (r28 < 38: на сплошной грани)
SHOULDER_D, SHOULDER_H = 11.0, 3.0        # z 4..7, держит только внутреннее кольцо
SPIGOT_EXTRA = 1.5                        # шип выше подшипника (магнит в окне плиты)
HUB_TOP = WHEEL_FACE_Z + HUB_T            # 4.0
BRG_Z0 = HUB_TOP + SHOULDER_H             # 7.0  низ подшипника
BRG_Z1 = BRG_Z0 + BRG_W                   # 14.0
SPIGOT_TOP = BRG_Z1 + SPIGOT_EXTRA        # 15.5
MAG_FACE = SPIGOT_TOP - MAG_RECESS        # 15.1
CHIP_FACE = MAG_FACE + AIR_GAP            # 16.6

# ---------------- стакан + поводок ----------------
CAR_IN = BRG_Z0                           # 7.0  внутренняя грань = низ подшипника (вровень)
POCKET_DEPTH = BRG_W + 0.4                # 7.4  над подшипником 0.4 воздуха
CEIL = CAR_IN + POCKET_DEPTH              # 14.4 потолок кармана
BRD_IN = CHIP_FACE + CHIP_H               # 17.7 нижняя (чиповая) грань платы
PLATE_OUT = BRD_IN - BOSS_H               # 16.5 наружная грань плиты
WINDOW_D = 10.0                           # окно плиты: шип Ø8 и чип проходят
CUP_R = 17.0
RIM_IN_R, RIM_TOP = 12.2, PLATE_OUT + BOSS_H + BRD_T + PIN_OVER + PIN_TIP_H + 0.2
RIM_NOTCH_W = 8.0
ARM_R = 140.0                             # ось → центр паза
ARM_ANG = -45.0                           # куда смотрит поводок (вниз-вбок, гравитация
                                          # прижимает паз к штырю → люфта нет)
ARM_W, ARM_T = 12.0, 8.0                  # z 7..15
END_W, SLOT_TRAVEL = 18.0, 20.0           # паз r 130..150
POST_D = 8.0
SLOT_W = POST_D + 0.4
TIE_R = (50.0, 95.0)                      # дырки под стяжки провода

# ---------------- штырь на стенке ----------------
POST_BASE, POST_BASE_T, POST_H = 30.0, 3.0, 21.0   # штырь z 3..24
SCREW_D, SCREW_CS_D = 4.0, 7.6            # саморез 3.5–4, потай


def cyl(r, z0, h, x=0.0, y=0.0):
    return Pos(x, y, z0) * Cylinder(r, h, align=MIN)


def cone(r0, r1, z0, h, x=0.0, y=0.0):
    return Pos(x, y, z0) * Cone(r0, r1, h, align=MIN)


def box(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def notches(n, x0, y, z0, z1, step=3.0):
    """n рисок-пропилов 1.2 шириной по краю детали (номер варианта)."""
    return [box(x0 + k * step - 0.6, x0 + k * step + 0.6, y - 1.0, y + 1.0, z0, z1)
            for k in range(n)]


# ======================= 1. СТУПИЦА (сборка) =======================
def build_hub(spigot_d=SPIGOT_D):
    z0 = WHEEL_FACE_Z
    hub = cyl(HUB_D / 2, z0, HUB_T)
    hub += cyl(SHOULDER_D / 2, HUB_TOP, SHOULDER_H)
    hub += cyl(spigot_d / 2, BRG_Z0 - 0.01, SPIGOT_TOP - BRG_Z0 + 0.01)
    # заход на шип (фаска 0.5) — подшипник надевается ровно
    hub -= (cyl(spigot_d / 2 + 1, SPIGOT_TOP - 0.5, 1)
            - cone(spigot_d / 2 - 0.5, spigot_d / 2 + 0.5, SPIGOT_TOP - 0.5, 1.0))
    # карман магнита в торце шипа
    hub -= cyl((MAG_D + MAG_FIT) / 2, MAG_FACE - MAG_H - 0.2, MAG_H + MAG_RECESS + 0.2 + 0.01)
    # гнёзда на концы болтов + фаска-заход у колеса
    for a in BOLT_ANG:
        x, y = BOLT_R * math.cos(math.radians(a)), BOLT_R * math.sin(math.radians(a))
        hub -= cyl(SOCKET_D / 2, z0 - 0.01, SOCKET_DEPTH + 0.01, x, y)
        hub -= cone(SOCKET_D / 2 + 0.8, SOCKET_D / 2, z0 - 0.01, 0.8, x, y)
    # кольцевая канавка под лишний клей (между гнёздами и краем)
    hub -= cyl(24.0, z0 - 0.01, 0.6) - cyl(22.0, z0 - 0.02, 0.62)
    return hub


# ======================= 2. СТАКАН + ПОВОДОК (сборка, поводок вдоль +x) =======================
def board_pins():
    parts = None
    for sx in (-1, 1):
        x = sx * PIN_PITCH / 2
        p = cyl(BOSS_D / 2, PLATE_OUT - 0.01, BOSS_H + 0.01, x)
        p += cone(PIN_ROOT_D / 2, PIN_SHANK_D / 2, BRD_IN - 0.01, PIN_FLARE_H, x)
        p += cyl(PIN_SHANK_D / 2, BRD_IN, BRD_T + PIN_OVER, x)
        p += cone(PIN_SHANK_D / 2, PIN_TIP_D / 2, BRD_IN + BRD_T + PIN_OVER - 0.01, PIN_TIP_H, x)
        parts = p if parts is None else parts + p
    return parts


def build_carrier(pocket_d=POCKET_D):
    car = cyl(CUP_R, CAR_IN, PLATE_OUT - CAR_IN)
    # обод вокруг платы (защита) с вырезом под провод в сторону поводка
    rim = cyl(CUP_R, PLATE_OUT - 0.01, RIM_TOP - PLATE_OUT + 0.01) - cyl(RIM_IN_R, PLATE_OUT - 1, 30)
    rim -= box(0, CUP_R + 2, -RIM_NOTCH_W / 2, RIM_NOTCH_W / 2, PLATE_OUT, RIM_TOP + 1)
    car += rim
    # поводок (вдоль +x) + лопатка с пазом
    car += box(CUP_R - 3, ARM_R - SLOT_TRAVEL / 2, -ARM_W / 2, ARM_W / 2, CAR_IN, CAR_IN + ARM_T)
    end = Pos(ARM_R, 0, CAR_IN) * extrude(
        SlotCenterToCenter(SLOT_TRAVEL + 6, END_W), amount=ARM_T)
    car += end
    # плавный переход поводок → лопатка
    car += Pos(ARM_R - SLOT_TRAVEL / 2 - 6, 0, CAR_IN) * extrude(
        RectangleRounded(14, END_W - 2, 3), amount=ARM_T)
    car += board_pins()
    # --- вырезы ---
    car -= cyl(pocket_d / 2, CAR_IN - 0.01, POCKET_DEPTH + 0.01)          # карман 608
    car -= cone(pocket_d / 2 + 0.6, pocket_d / 2, CAR_IN - 0.01, 0.6)       # фаска-заход
    car -= cyl(WINDOW_D / 2, CEIL - 0.1, PLATE_OUT - CEIL + 0.2)           # окно плиты
    car -= Pos(ARM_R, 0, CAR_IN - 1) * extrude(SlotCenterToCenter(SLOT_TRAVEL, SLOT_W),
                                             amount=ARM_T + 2)            # паз под штырь
    for r in TIE_R:                                                       # стяжки
        car -= box(r - 2.25, r + 2.25, -1.1, 1.1, CAR_IN - 1, CAR_IN + ARM_T + 1)
    return car


# ======================= 3. ШТЫРЬ НА СТЕНКУ (поза печати = сборки, центр в 0) =======================
def build_post():
    p = extrude(RectangleRounded(POST_BASE, POST_BASE, 4.0), amount=POST_BASE_T)
    p += cone(POST_D / 2 + 3.0, POST_D / 2, POST_BASE_T - 0.01, 3.0)        # галтель-конус
    p += cyl(POST_D / 2, POST_BASE_T, POST_H)
    p -= (cyl(POST_D / 2 + 1, POST_BASE_T + POST_H - 0.6, 1)
          - cone(POST_D / 2, POST_D / 2 - 0.6, POST_BASE_T + POST_H - 0.6, 0.6))
    for sx, sy in ((-1, -1), (1, 1)):
        x, y = sx * 10.0, sy * 10.0
        p -= cyl(SCREW_D / 2, -0.01, POST_BASE_T + 0.02, x, y)
        h = (SCREW_CS_D - SCREW_D) / 2
        p -= cone(SCREW_D / 2, SCREW_CS_D / 2, POST_BASE_T - h + 0.01, h, x, y)
    return p


# ======================= 4. ПРОБНИК ПОСАДОК 608 =======================
def build_coupon():
    parts = None
    for i, d in enumerate(POCKET_TRY):          # стаканы: как карман стакана (дно = стол)
        x = i * 34.0
        c = cyl(15.0, 0, POCKET_DEPTH + 2.1, x)
        c -= cyl(d / 2, -0.01, POCKET_DEPTH + 0.01, x)
        c -= cone(d / 2 + 0.6, d / 2, -0.01, 0.6, x)
        c -= cyl(WINDOW_D / 2, POCKET_DEPTH - 0.1, 3, x)
        for n in notches(i + 1, x - 3.0 * i / 2, 15.0, POCKET_DEPTH + 1.1, POCKET_DEPTH + 2.2):
            c -= n
        parts = c if parts is None else parts + c
    for i, d in enumerate(SPIGOT_TRY):          # шипы: как на ступице
        x = i * 34.0
        y = -34.0
        s = cyl(9.0, 0, 2.5, x, y) + cyl(SHOULDER_D / 2, 2.49, 1.01, x, y)
        s += cyl(d / 2, 3.49, BRG_W + SPIGOT_EXTRA + 0.01, x, y)
        top = 3.5 + BRG_W + SPIGOT_EXTRA
        s -= cyl(d / 2 + 1, top - 0.5, 1, x, y) - cone(d / 2 - 0.5, d / 2 + 0.5, top - 0.5, 1.0, x, y)
        for n in notches(i + 1, x - 3.0 * i / 2, y + 9.0, 1.4, 2.6):
            s -= n
        parts += s
    return parts


# ======================= проверки в сборке =======================
def wall_ok_at(x, y, margin):
    """точка на фанере стенки с запасом margin от краёв (стенка ±125, V сверху)"""
    if abs(x) > WALL_HALF_W - margin:
        return False
    # V: прямые (±125,-30) → (0,-140); фанера ниже/снаружи V
    nx, ny = 110.0, -125.0          # нормаль правой кромки, внутрь фанеры
    L = math.hypot(nx, ny)
    d = (nx * (abs(x) - 125.0) + ny * (y - V_TOP_Y)) / L
    return d >= margin


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    hub, car, post, coupon = build_hub(), build_carrier(), build_post(), build_coupon()
    for name, part in (('hub', hub), ('carrier', car), ('post', post), ('coupon', coupon)):
        assert part.is_valid, f'{name}: невалидный B-rep'

    # --- сборка: поводок разворачиваем на ARM_ANG, штырь — в центр паза ---
    car_w = Rot(0, 0, ARM_ANG) * car
    a = math.radians(ARM_ANG)
    px, py = ARM_R * math.cos(a), ARM_R * math.sin(a)
    post_w = Pos(px, py, 0) * post

    # модели купленного: подшипник, магнит, плата с чипом
    brg_in = cyl(BRG_IN_RING_OD / 2, BRG_Z0, BRG_W) - cyl(BRG_ID / 2, BRG_Z0 - 1, BRG_W + 2)
    brg_out = cyl(BRG_OD / 2, BRG_Z0, BRG_W) - cyl(BRG_OUT_RING_ID / 2, BRG_Z0 - 1, BRG_W + 2)
    magnet = cyl(MAG_D / 2, MAG_FACE - MAG_H, MAG_H)
    board = box(-BRD_L / 2, BRD_L / 2, -BRD_W / 2, BRD_W / 2, BRD_IN, BRD_IN + BRD_T)
    for sx in (-1, 1):
        board -= cyl(1.05, BRD_IN - 1, BRD_T + 2, sx * PIN_PITCH / 2)
    chip = box(-3.2, 3.2, -2.5, 2.5, CHIP_FACE, BRD_IN)
    board_w, chip_w = Rot(0, 0, ARM_ANG) * board, Rot(0, 0, ARM_ANG) * chip

    def vol(s):
        try:
            return s.volume
        except Exception:
            return 0.0

    checks = {
        'ступица ∩ стакан': vol(hub & car_w),
        'стакан ∩ штырь (паз)': vol(car_w & post_w),
        'плата ∩ стакан (кроме штырьков)': vol(board_w & (car_w - pin_zone_w())),
        'чип ∩ стакан': vol(chip_w & car_w),
        'чип ∩ ступица': vol(chip_w & hub),
        'внутр.кольцо ∩ стакан': vol(brg_in & car_w),
        'наруж.кольцо ∩ ступица': vol(brg_out & hub),
        'магнит ∩ стакан': vol(magnet & car_w),
    }
    # плата надета на штырьки — пересечение = только штырьки в дырках (объём ~0)
    print('ПЕРЕСЕЧЕНИЯ (должны быть 0):')
    bad = False
    for k, v in checks.items():
        flag = 'OK' if v < 0.05 else 'ПЛОХО'
        bad |= v >= 0.05
        print(f'  {k:34s} {v:8.3f} мм³  {flag}')

    gaps = {
        'стакан над диском ступицы (z)': CAR_IN - HUB_TOP,
        'потолок кармана над подшипником': CEIL - BRG_Z1,
        'окно плиты вокруг шипа (радиально)': WINDOW_D / 2 - SPIGOT_D / 2,
        'чип над магнитом (рабочий зазор)': CHIP_FACE - MAG_FACE,
        'чип над торцом шипа': CHIP_FACE - SPIGOT_TOP,
        'чип над плитой': CHIP_FACE - PLATE_OUT,
        'поводок над стенкой (z)': CAR_IN - 0.0,
        'поводок над площадкой штыря': CAR_IN - POST_BASE_T,
        'штырь выше поводка (запас наружу)': POST_BASE_T + POST_H - (CAR_IN + ARM_T),
        'зазор паз–штырь (на сторону)': (SLOT_W - POST_D) / 2,
        'диск ступицы до окон колеса (r)': WHEEL_SOLID_R - HUB_D / 2,
        'обод стакана над кончиками штырьков': RIM_TOP - (BRD_IN + BRD_T + PIN_OVER + PIN_TIP_H),
        'металл шипа вокруг магнита': (SPIGOT_D - MAG_D - MAG_FIT) / 2,
    }
    print('ЗАЗОРЫ, мм:')
    for k, v in gaps.items():
        print(f'  {k:38s} {v:6.2f}')
    for k in ('стакан над диском ступицы (z)', 'потолок кармана над подшипником',
              'чип над торцом шипа', 'поводок над площадкой штыря'):
        assert gaps[k] > 0.3, k

    # штырь на фанере: площадка 30×30 целиком на стенке с запасом ≥8 до кромок
    corners = [(px + sx * POST_BASE / 2, py + sy * POST_BASE / 2) for sx in (-1, 1) for sy in (-1, 1)]
    margin = min(min(WALL_HALF_W - abs(x), 1e9) for x, _ in corners)
    on_wall = all(wall_ok_at(x, y, 8.0) for x, y in corners)
    print(f'ШТЫРЬ: центр ({px:.1f}, {py:.1f}), площадка на фанере с запасом ≥8: {on_wall}, '
          f'до бокового края {margin:.1f}')
    assert on_wall, 'площадка штыря вылезает за фанеру'
    err = math.degrees(0.5 / ARM_R) * 60
    print(f'ОШИБКА при люфте колеса 0.5 мм поперёк поводка: {err:.0f}′ (у v2 ~60′)')

    # --- экспорт в позах печати ---
    poses = {
        'v3_alt_hub': Pos(0, 0, -WHEEL_FACE_Z) * hub,             # диском на стол, гнёзда снизу
        'v3_alt_carrier': Pos(0, 0, -CAR_IN) * car,               # внутренней гранью на стол
        'v3_alt_post': post,                                      # площадкой на стол
        'v3_fit_bearing': coupon,
    }
    import trimesh
    for name, part in poses.items():
        stl, step = OUT / f'{name}.stl', OUT / f'{name}.step'
        export_stl(part, str(stl), tolerance=0.01, angular_tolerance=0.1)
        export_step(part, str(step))
        m = trimesh.load(stl)
        bb = m.bounds[1] - m.bounds[0]
        print(f'{name:16s} bbox {bb[0]:6.1f}×{bb[1]:6.1f}×{bb[2]:5.1f}  '
              f'{m.volume/1000:5.1f} см³  watertight={m.is_watertight}  zmin={m.bounds[0][2]:.2f}')

    # --- сборка для превью/проверки (мировые координаты) ---
    asm = {'hub': hub, 'carrier': car_w, 'post': post_w, 'bearing_in': brg_in,
           'bearing_out': brg_out, 'magnet': magnet, 'board': board_w, 'chip': chip_w}
    asm_dir = OUT / '_asm_v3_alt'
    asm_dir.mkdir(exist_ok=True)
    for k, s in asm.items():
        export_stl(s, str(asm_dir / f'{k}.stl'), tolerance=0.02, angular_tolerance=0.2)
    print('сборка →', asm_dir)
    if bad:
        raise SystemExit('ЕСТЬ ПЕРЕСЕЧЕНИЯ')


def pin_zone_w():
    """цилиндры вокруг штырьков: там плата и должна сидеть туго (клин у корня)"""
    z = None
    for sx in (-1, 1):
        c = cyl(PIN_ROOT_D / 2 + 0.2, BRD_IN - 0.5, BRD_T + 1.0, sx * PIN_PITCH / 2)
        z = c if z is None else z + c
    return Rot(0, 0, ARM_ANG) * z


if __name__ == '__main__':
    main()
