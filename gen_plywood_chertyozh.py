#!/usr/bin/env python3
"""
Plywood cut chertyozh for 8" f/5.9 Newtonian Dobsonian.
Based on Stellafane Dobson design (stellafane.org/tm/dob/).
Scaled for: mirror Ø203mm, sonotube ID Ø250 / OD Ø258, 18mm plywood.

Output: plywood_cuts_a4.svg
"""
import math
from pathlib import Path

# ============ INPUTS ============
MIRROR_D = 203.0
TUBE_ID = 250.0
TUBE_OD = 258.0
PLY = 18.0

# ============ COMPUTED DIMENSIONS ============
# Mirror cell (Seronik-style 2-plate)
TOP_D = MIRROR_D + 12                # 215
Y_ENV_D = TUBE_ID                    # 250 (ears reach tube ID)
PUSH_R = round(0.70 * MIRROR_D / 2)  # 71
PULL_R = round(0.55 * MIRROR_D / 2)  # 56
BOLT_D = 6                           # M5 clearance
EAR_SCREW_R = TUBE_ID/2 - 10         # 115
EAR_SCREW_D = 5
VENT_D = 60                          # central vent in top plate

# Cradle (2 rings + 4 battens, simple)
CRADLE_ID = TUBE_OD + 4              # 262
CRADLE_OD = CRADLE_ID + 58           # 320
BATTEN_HOLE_R = (CRADLE_ID + CRADLE_OD)/4  # 145.5
BATTEN_HOLE_D = 4
CRADLE_LENGTH_MM = 300               # batten length

# Side bearings (Stellafane: 1 disk halved → 2 semicircles)
BEARING_D = 380                      # 1.47 × TUBE_OD, in 1.2-1.8 range
BEARING_SCREW_R = BEARING_D/2 - 25    # 165
BEARING_SCREW_D = 4

# Rocker box (compromised to fit 80×120 sheet)
ROCKER_SIDE_W = 310                  # 1.2 × TUBE_OD, along tube axis
ROCKER_SIDE_H = 380                  # height (Stellafane suggests 600 but tight on sheet)
SIDE_CUTOUT_R = BEARING_D/2 + 2      # 192 (bearing radius + 2mm laminate)
SIDE_CUTOUT_CHORD = ROCKER_SIDE_W    # 310 — full side wall width
SIDE_CUTOUT_DEPTH = SIDE_CUTOUT_R - math.sqrt(SIDE_CUTOUT_R**2 - (SIDE_CUTOUT_CHORD/2)**2)  # ~79mm
PTFE_ANGLE_DEG = 40                  # PTFE pads at ±40° from cutout bottom (inside the chord ends)

ROCKER_FRONT_W = 350                 # ширина передней (по перпендикуляру к оси трубы)
ROCKER_FRONT_H = 350

# Bottom + ground (Stellafane: circles)
BOTTOM_D = 380                       # rocker bottom diameter
GROUND_D = 400                       # ground board diameter
AZIMUTH_BOLT_D = 10                  # M10
PTFE_R_GROUND = 150                  # PTFE pads radius on ground board
FEET_R_GROUND = 170                  # rubber feet radius

# ============ DRAWING PARAMETERS ============
PAGE_W = 210.0  # mm A4
PAGE_H = 297.0
SCALE = 0.125   # 1:8 — visual scale for parts on the page

def mm(v):
    """Scale a real-mm value to visual page mm."""
    return v * SCALE

# ============ SVG HELPERS ============
def svg_header():
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{PAGE_W}mm" height="{PAGE_H}mm" '
            f'viewBox="0 0 {PAGE_W} {PAGE_H}" font-family="Helvetica, Arial, sans-serif">\n'
            '''  <style>
    .ttl { font: bold 5px Helvetica; fill: #fff; }
    .sub { font: 2.6px Helvetica; fill: #cfd8dc; }
    .sech { font: bold 3.1px Helvetica; fill: #fff; }
    .lbl { font: bold 2.7px Helvetica; fill: #1a2b3c; }
    .qty { font: bold 2.3px Helvetica; fill: #b8860b; }
    .nt { font: italic 2.0px Helvetica; fill: #555; }
    .dim { font: 2.4px Helvetica; fill: #c0392b; }
    .ds { font: 2.0px Helvetica; fill: #c0392b; }
    .src { font: italic 1.7px Helvetica; fill: #888; }
    .part { fill: #fdf6e3; stroke: #2c3e50; stroke-width: 0.5; }
    .hole { fill: white; stroke: #1565c0; stroke-width: 0.35; }
    .vent { fill: white; stroke: #1565c0; stroke-width: 0.4; }
    .env { fill: none; stroke: #888; stroke-width: 0.25; stroke-dasharray: 1.2,1.0; }
    .axisL { stroke: #999; stroke-width: 0.18; stroke-dasharray: 0.8,0.8; fill: none; }
    .ftLn { stroke: #888; stroke-width: 0.4; stroke-dasharray: 3,2; fill: none; }
    .secbar { fill: #34495e; }
  </style>\n''')

def section_bar(y, title):
    return (f'<rect x="0" y="{y}" width="{PAGE_W}" height="4.5" class="secbar"/>\n'
            f'<text x="3" y="{y+3.3}" class="sech">{title}</text>\n')

def part_block(cx, cy, label, qty, draw_inner, dims_below):
    """Wrap a part with a centered group."""
    s = f'<g transform="translate({cx},{cy})">\n'
    s += '  <g transform="scale(' + str(SCALE) + ')">\n'
    s += draw_inner + '\n'
    s += '  </g>\n'
    if label:
        s += f'  <text x="0" y="{-mm(BEARING_D/2 if False else 100)-10}" text-anchor="middle" class="lbl">{label}</text>\n'
    return s

# ============ DRAW EACH PART AS INNER (real-mm coords) ============

def front_plate_inner():
    """Top plate of mirror cell: Ø215 with vent + 6 collimation holes."""
    r = TOP_D/2
    s = f'<circle cx="0" cy="0" r="{r}" class="part"/>\n'
    s += f'<circle cx="0" cy="0" r="{VENT_D/2}" class="vent"/>\n'
    # 3 push holes: aligned with Y ears (top, lower-right, lower-left)
    push_pos = [
        (0, -PUSH_R),
        (PUSH_R * math.cos(math.radians(30)), PUSH_R * math.sin(math.radians(30))),
        (-PUSH_R * math.cos(math.radians(30)), PUSH_R * math.sin(math.radians(30))),
    ]
    for x, y in push_pos:
        s += f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{BOLT_D/2}" class="hole"/>\n'
    # 3 pull holes between pushes
    pull_pos = [
        (PULL_R * math.cos(math.radians(-30)), PULL_R * math.sin(math.radians(-30))),
        (0, PULL_R),
        (-PULL_R * math.cos(math.radians(-30)), PULL_R * math.sin(math.radians(-30))),
    ]
    for x, y in pull_pos:
        s += f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{BOLT_D/2}" class="hole"/>\n'
    # axes
    s += f'<line x1="-{r-3}" y1="0" x2="{r-3}" y2="0" class="axisL"/>\n'
    s += f'<line x1="0" y1="-{r-3}" x2="0" y2="{r-3}" class="axisL"/>\n'
    return s

def y_plate_inner():
    """Y-plate: 3 fat ears (overlapping circles) reach tube ID; 6 through-holes + 3 ear screws."""
    # Envelope (dashed)
    s = f'<circle cx="0" cy="0" r="{Y_ENV_D/2}" class="env"/>\n'
    # 3 overlapping circles for ears: R=75 at distance 50 from origin
    Re = 75
    Rc = 50
    # Tangent point pairs (precomputed for path)
    # outer intersections of adjacent ear circles
    # Top ear at (0,-50), LR at (43.3, 25), LL at (-43.3, 25)
    # Intersections farthest from origin = outer corners of Y
    A = (74.68, -43.12)   # top ⋂ LR (outer)
    B = (0, 86.24)        # LR ⋂ LL (outer)
    C = (-74.68, -43.12)  # LL ⋂ top (outer)
    s += (f'<path d="M {A[0]},{A[1]} '
          f'A {Re},{Re} 0 1,0 {C[0]},{C[1]} '
          f'A {Re},{Re} 0 1,0 {B[0]},{B[1]} '
          f'A {Re},{Re} 0 1,0 {A[0]},{A[1]} Z" class="part"/>\n')
    # 6 through-holes (matching front plate)
    push_pos = [
        (0, -PUSH_R),
        (PUSH_R * math.cos(math.radians(30)), PUSH_R * math.sin(math.radians(30))),
        (-PUSH_R * math.cos(math.radians(30)), PUSH_R * math.sin(math.radians(30))),
    ]
    pull_pos = [
        (PULL_R * math.cos(math.radians(-30)), PULL_R * math.sin(math.radians(-30))),
        (0, PULL_R),
        (-PULL_R * math.cos(math.radians(-30)), PULL_R * math.sin(math.radians(-30))),
    ]
    for x, y in push_pos + pull_pos:
        s += f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{BOLT_D/2}" class="hole"/>\n'
    # 3 ear screw holes at R=115 (tube wall mounting)
    for angle_deg in (-90, 30, 150):  # top, LR, LL directions
        a = math.radians(angle_deg)
        x = EAR_SCREW_R * math.cos(a)
        y = EAR_SCREW_R * math.sin(a)
        s += f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{EAR_SCREW_D/2}" class="hole"/>\n'
    # axes
    s += f'<line x1="-20" y1="0" x2="20" y2="0" class="axisL"/>\n'
    s += f'<line x1="0" y1="-20" x2="0" y2="20" class="axisL"/>\n'
    return s

def cradle_ring_inner():
    """Cradle ring: annulus, OD/ID, 4 batten holes."""
    s = f'<circle cx="0" cy="0" r="{CRADLE_OD/2}" class="part"/>\n'
    s += f'<circle cx="0" cy="0" r="{CRADLE_ID/2}" fill="white" stroke="#2c3e50" stroke-width="0.5"/>\n'
    for ang in (45, 135, 225, 315):
        a = math.radians(ang)
        x = BATTEN_HOLE_R * math.cos(a)
        y = BATTEN_HOLE_R * math.sin(a)
        s += f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{BATTEN_HOLE_D/2}" class="hole"/>\n'
    s += '<line x1="-20" y1="0" x2="20" y2="0" class="axisL"/>\n'
    s += '<line x1="0" y1="-20" x2="0" y2="20" class="axisL"/>\n'
    return s

def bearing_disk_inner():
    """Bearing disk Ø380, with dashed cut line dividing it into 2 semicircles."""
    r = BEARING_D/2
    s = f'<circle cx="0" cy="0" r="{r}" class="part"/>\n'
    # The cut line (where we will saw the disk in half)
    s += f'<line x1="-{r+5}" y1="0" x2="{r+5}" y2="0" class="ftLn"/>\n'
    # 3 screw holes in EACH half — total 6, at R=165, at angles 60°/120°/90° in each half
    # Upper half (y<0): 3 screws
    for ang in (135, 90, 45):
        a = math.radians(ang)
        x = BEARING_SCREW_R * math.cos(a)
        y = -BEARING_SCREW_R * math.sin(a)  # upper half = negative y
        s += f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{BEARING_SCREW_D/2}" class="hole"/>\n'
    # Lower half (y>0): 3 screws
    for ang in (135, 90, 45):
        a = math.radians(ang)
        x = BEARING_SCREW_R * math.cos(a)
        y = BEARING_SCREW_R * math.sin(a)
        s += f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{BEARING_SCREW_D/2}" class="hole"/>\n'
    return s

def rocker_side_inner():
    """Rocker side wall: rect 310×380 with cutout at top center (chord = full width)."""
    W = ROCKER_SIDE_W
    H = ROCKER_SIDE_H
    R = SIDE_CUTOUT_R
    # Cutout arc geometry:
    #   - chord at top edge (y = -H/2), endpoints at (∓W/2, -H/2)
    #   - arc bulges DOWN INTO the rect by depth = R - sqrt(R² - (W/2)²)
    #   - arc circle center is ABOVE the rect (negative y, outside) so arc on opposite side (inside rect)
    arc_center_y = -H/2 - math.sqrt(R**2 - (W/2)**2)
    # Path: top-left → arc (left-to-right, INTO rect, sweep=0) → top-right → down → bottom → close
    s = (f'<path d="M -{W/2},-{H/2} '
         f'A {R},{R} 0 0,0 {W/2},-{H/2} '
         f'L {W/2},{H/2} '
         f'L -{W/2},{H/2} Z" class="part"/>\n')
    # PTFE pads on the arc at ±PTFE_ANGLE_DEG from the cutout's deepest point
    # Deepest point at SVG angle 90° from arc center (straight down). Pads at 90°±angle.
    for sign in (-1, 1):
        a = math.radians(90 + PTFE_ANGLE_DEG * sign)
        x_pad = R * math.cos(a)
        y_pad = arc_center_y + R * math.sin(a)
        s += f'<circle cx="{x_pad:.2f}" cy="{y_pad:.2f}" r="10" class="hole"/>\n'
    # axes
    s += '<line x1="-15" y1="0" x2="15" y2="0" class="axisL"/>\n'
    s += '<line x1="0" y1="-15" x2="0" y2="15" class="axisL"/>\n'
    # vertical guide from cutout deepest point to bottom
    deepest_y = arc_center_y + R
    s += f'<line x1="0" y1="{deepest_y:.2f}" x2="0" y2="{H/2 - 5}" class="axisL"/>\n'
    return s

def rocker_front_inner():
    """Front wall: 350×350 rectangle."""
    W = ROCKER_FRONT_W
    H = ROCKER_FRONT_H
    s = f'<rect x="-{W/2}" y="-{H/2}" width="{W}" height="{H}" class="part"/>\n'
    # 4 corner screw holes
    for sx in (-1, 1):
        for sy in (-1, 1):
            s += f'<circle cx="{sx*(W/2 - 15):.0f}" cy="{sy*(H/2 - 15):.0f}" r="2.5" class="hole"/>\n'
    return s

def rocker_bottom_inner():
    """Bottom: circle Ø380 with center hole for M10 axle."""
    r = BOTTOM_D/2
    s = f'<circle cx="0" cy="0" r="{r}" class="part"/>\n'
    s += f'<circle cx="0" cy="0" r="{AZIMUTH_BOLT_D/2}" class="hole"/>\n'
    s += '<line x1="-15" y1="0" x2="15" y2="0" class="axisL"/>\n'
    s += '<line x1="0" y1="-15" x2="0" y2="15" class="axisL"/>\n'
    return s

def ground_inner():
    """Ground board: circle Ø400 with center hole + 3 PTFE positions + 3 feet positions."""
    r = GROUND_D/2
    s = f'<circle cx="0" cy="0" r="{r}" class="part"/>\n'
    # center hole for M10
    s += f'<circle cx="0" cy="0" r="{AZIMUTH_BOLT_D/2}" class="hole"/>\n'
    # 3 PTFE pads at 90/210/330° (top, lower-right, lower-left in SVG)
    for ang in (-90, 30, 150):
        a = math.radians(ang)
        x = PTFE_R_GROUND * math.cos(a)
        y = PTFE_R_GROUND * math.sin(a)
        s += f'<circle cx="{x:.2f}" cy="{y:.2f}" r="10" class="hole"/>\n'
    # 3 rubber feet at 30/150/270° (between PTFE), dashed
    for ang in (-30, 90, 210):
        a = math.radians(ang)
        x = FEET_R_GROUND * math.cos(a)
        y = FEET_R_GROUND * math.sin(a)
        s += (f'<circle cx="{x:.2f}" cy="{y:.2f}" r="15" '
              f'fill="none" stroke="#888" stroke-width="0.7" stroke-dasharray="3,2"/>\n')
    # axes
    s += '<line x1="-20" y1="0" x2="20" y2="0" class="axisL"/>\n'
    s += '<line x1="0" y1="-20" x2="0" y2="20" class="axisL"/>\n'
    return s

# ============ ASSEMBLE PAGE ============
def build_svg():
    out = svg_header()
    # Header bar
    out += f'<rect x="0" y="0" width="{PAGE_W}" height="13" fill="#1a2b3c"/>\n'
    out += f'<text x="{PAGE_W/2}" y="6" text-anchor="middle" class="ttl">ВЫПИЛЫ ИЗ ФАНЕРЫ 18 мм</text>\n'
    out += f'<text x="{PAGE_W/2}" y="10" text-anchor="middle" class="sub">Ньютон 200/1200 Dobson · Stellafane-стиль · масштаб видов 1:8 · размеры в мм</text>\n'

    # ===== SECTION 1: MIRROR CELL =====
    out += section_bar(14, '1.  ОПРАВА ЗЕРКАЛА (Seronik-style)  ·  2 детали  ·  лист 60×120')
    # Front plate at (50, 50)
    out += f'<g transform="translate(50,50)"><g transform="scale({SCALE})">\n'
    out += front_plate_inner()
    out += '</g>\n'
    out += '<text x="0" y="-19" text-anchor="middle" class="lbl">Передняя пластина</text>\n'
    out += '<text x="0" y="-16" text-anchor="middle" class="qty">1 шт</text>\n'
    out += '<text x="0" y="20" text-anchor="middle" class="dim">круг Ø 215  ·  вент. отв. Ø 60 в центре</text>\n'
    out += f'<text x="0" y="23" text-anchor="middle" class="ds">3 нажимных Ø 6 на R=71 (по ушам Y, через 120°)</text>\n'
    out += f'<text x="0" y="25.5" text-anchor="middle" class="ds">3 прижимных Ø 6 на R=56 (между нажимными)</text>\n'
    out += '</g>\n'

    # Y-plate at (155, 50)
    out += f'<g transform="translate(155,50)"><g transform="scale({SCALE})">\n'
    out += y_plate_inner()
    out += '</g>\n'
    out += '<text x="0" y="-19" text-anchor="middle" class="lbl">Задняя Y-пластина</text>\n'
    out += '<text x="0" y="-16" text-anchor="middle" class="qty">1 шт</text>\n'
    out += f'<text x="0" y="22" text-anchor="middle" class="dim">3 уха вписаны в Ø 250 (= ID трубы)</text>\n'
    out += f'<text x="0" y="25" text-anchor="middle" class="ds">6 сквозных Ø 6 совпадают с передней пластиной</text>\n'
    out += f'<text x="0" y="27.5" text-anchor="middle" class="ds">3 отв. Ø 5 в ушах (R=115) под шурупы к трубе</text>\n'
    out += '</g>\n'

    # ===== SECTION 2: CRADLE + BEARINGS =====
    out += section_bar(80, '2.  ЛЮЛЬКА (кольца+бруски) + ВЫСОТНЫЕ ПОДШИПНИКИ  ·  лист 60×120')
    # Cradle ring at (50, 115)
    out += f'<g transform="translate(50,115)"><g transform="scale({SCALE})">\n'
    out += cradle_ring_inner()
    out += '</g>\n'
    out += '<text x="0" y="-23" text-anchor="middle" class="lbl">Кольцо люльки</text>\n'
    out += '<text x="0" y="-20" text-anchor="middle" class="qty">2 шт (одинаковые)</text>\n'
    out += f'<text x="0" y="23" text-anchor="middle" class="dim">OD 320  ·  ID 262 (= труба + 4мм)</text>\n'
    out += '<text x="0" y="26" text-anchor="middle" class="ds">4 отв. Ø 4 на R=146 (по углам, под брус 30×30)</text>\n'
    out += '<text x="0" y="28.5" text-anchor="middle" class="src">2 кольца соединить брусками 30×30×300мм (= длина люльки)</text>\n'
    out += '</g>\n'

    # Bearing disk at (155, 115)
    out += f'<g transform="translate(155,115)"><g transform="scale({SCALE})">\n'
    out += bearing_disk_inner()
    out += '</g>\n'
    out += '<text x="0" y="-27" text-anchor="middle" class="lbl">Диск подшипников</text>\n'
    out += '<text x="0" y="-24" text-anchor="middle" class="qty">1 диск → 2 полукруга</text>\n'
    out += f'<text x="0" y="27" text-anchor="middle" class="dim">круг Ø 380 (= 1.47×OD трубы)</text>\n'
    out += '<text x="0" y="30" text-anchor="middle" class="ds">распилить пополам → 2 полукруглых подшипника</text>\n'
    out += '<text x="0" y="32.5" text-anchor="middle" class="ds">3 отв. Ø 4 в каждой половине к боку люльки</text>\n'
    out += '<text x="0" y="35" text-anchor="middle" class="src">обклеить торец PTFE-полосой 25 мм</text>\n'
    out += '</g>\n'

    # ===== SECTION 3: ROCKER BOX =====
    out += section_bar(150, '3.  РОКЕР-БОКС  ·  4 детали  ·  лист 80×120')
    # Side wall at (45, 195)
    out += f'<g transform="translate(45,195)"><g transform="scale({SCALE})">\n'
    out += rocker_side_inner()
    out += '</g>\n'
    out += '<text x="0" y="-29" text-anchor="middle" class="lbl">Боковая стенка</text>\n'
    out += '<text x="0" y="-26" text-anchor="middle" class="qty">2 шт</text>\n'
    out += f'<text x="0" y="27" text-anchor="middle" class="dim">310 × 380</text>\n'
    out += f'<text x="0" y="29.5" text-anchor="middle" class="ds">вырез R=192, глубина ≈ 79 мм</text>\n'
    out += '<text x="0" y="32" text-anchor="middle" class="ds">2 PTFE-пятака через 80° на дуге</text>\n'
    out += '</g>\n'

    # Front wall at (105, 195)
    out += f'<g transform="translate(105,195)"><g transform="scale({SCALE})">\n'
    out += rocker_front_inner()
    out += '</g>\n'
    out += '<text x="0" y="-25" text-anchor="middle" class="lbl">Передняя стенка</text>\n'
    out += '<text x="0" y="-22" text-anchor="middle" class="qty">1 шт</text>\n'
    out += '<text x="0" y="25" text-anchor="middle" class="dim">350 × 350</text>\n'
    out += '<text x="0" y="28" text-anchor="middle" class="ds">саморезы в торец боковин (4×60)</text>\n'
    out += '</g>\n'

    # Bottom at (170, 195) — circle
    out += f'<g transform="translate(170,195)"><g transform="scale({SCALE})">\n'
    out += rocker_bottom_inner()
    out += '</g>\n'
    out += '<text x="0" y="-28" text-anchor="middle" class="lbl">Дно рокера (круг!)</text>\n'
    out += '<text x="0" y="-25" text-anchor="middle" class="qty">1 шт</text>\n'
    out += '<text x="0" y="28" text-anchor="middle" class="dim">круг Ø 380</text>\n'
    out += f'<text x="0" y="31" text-anchor="middle" class="ds">центр Ø 10 под M10 (сверлить вместе с ground board)</text>\n'
    out += '</g>\n'

    # ===== SECTION 4: GROUND BOARD =====
    out += section_bar(232, '4.  GROUND BOARD (опорная плита)  ·  1 деталь  ·  лист 80×120')
    # Smaller scale for ground board so it fits with labels
    GBSCALE = 0.10  # 1:10 → Ø400 → 40mm
    out += f'<g transform="translate(50,265)"><g transform="scale({GBSCALE})">\n'
    out += ground_inner()
    out += '</g>\n'
    out += '<text x="0" y="-23" text-anchor="middle" class="lbl">Ground board · 1 шт</text>\n'
    out += '<text x="0" y="24" text-anchor="middle" class="dim">круг Ø 400</text>\n'
    out += '<text x="0" y="26.5" text-anchor="middle" class="ds">центр Ø 10 под ось M10</text>\n'
    out += '<text x="0" y="29" text-anchor="middle" class="ds">3 PTFE на R=150 через 120°</text>\n'
    out += '<text x="0" y="31.5" text-anchor="middle" class="src">пунктир — 3 рез. ножки на R=170</text>\n'
    out += '</g>\n'

    # Notes on right side
    out += '<g transform="translate(105,243)">\n'
    out += '<text x="0" y="0" class="lbl">ОТЛИЧИЯ от предыдущей версии:</text>\n'
    out += '<text x="0" y="4.5" class="ds">• Подшипники: 1 диск Ø380 распилен пополам</text>\n'
    out += '<text x="0" y="7" class="ds">  (вместо 2 кружков Ø200 — слишком мало;</text>\n'
    out += '<text x="0" y="9.5" class="ds">  правило Stellafane: 1.2-1.8 × OD трубы)</text>\n'
    out += '<text x="0" y="13" class="ds">• Дно рокера КРУГ Ø 380 (был квадрат)</text>\n'
    out += '<text x="0" y="16" class="ds">• Ground board КРУГ Ø 400 (был квадрат)</text>\n'
    out += '<text x="0" y="19" class="ds">• Вырез боковины рокера — теперь вниз ✓</text>\n'
    out += '<text x="0" y="22" class="ds">• Y-пластина: 6 сквозных болтовых отв.</text>\n'
    out += '<text x="0" y="24.5" class="ds">  (раньше совсем отсутствовали)</text>\n'
    out += '<text x="0" y="28" class="src">Формулы: stellafane.org/tm/dob/mount/</text>\n'
    out += '<text x="0" y="30.5" class="src">Цели: mirror 8" / sonotube ID250 OD258 / 18мм ply</text>\n'
    out += '</g>\n'

    # Footer
    out += f'<rect x="0" y="287" width="{PAGE_W}" height="10" fill="#ecf0f1"/>\n'
    out += '<text x="3" y="291" class="nt" font-weight="bold" fill="#222">Замечания:</text>\n'
    out += '<text x="3" y="294" class="nt">• Размеры компромиссные — влезает на 60×120 + 80×120. Для более просторного рокера — лист 100×150.</text>\n'
    out += '<text x="3" y="296.8" class="nt">• Дно рокера и ground board сверлить Ø10 совместно — точная соосность оси. Кромки P120→P400.</text>\n'

    out += '</svg>\n'
    return out

if __name__ == "__main__":
    svg = build_svg()
    out = Path("/Users/mac/newton/plywood_cuts_a4.svg")
    out.write_text(svg, encoding="utf-8")
    print(f"Wrote {out} ({len(svg)} bytes)")
    print()
    print("=== ПЕРЕСЧИТАННЫЕ РАЗМЕРЫ ===")
    print(f"Mirror cell:  Front Ø{TOP_D:.0f} · Y env Ø{Y_ENV_D:.0f} · push R={PUSH_R:.0f} · pull R={PULL_R:.0f}")
    print(f"Cradle:       Ring OD {CRADLE_OD:.0f} · ID {CRADLE_ID:.0f}")
    print(f"Bearings:     1 диск Ø{BEARING_D:.0f} → 2 полукруга")
    print(f"Rocker:       Side {ROCKER_SIDE_W:.0f}×{ROCKER_SIDE_H:.0f}, cutout R={SIDE_CUTOUT_R:.0f}")
    print(f"              Front {ROCKER_FRONT_W:.0f}×{ROCKER_FRONT_H:.0f}, Bottom Ø{BOTTOM_D:.0f}")
    print(f"Ground:       Ø{GROUND_D:.0f}, PTFE@R={PTFE_R_GROUND:.0f}, feet@R={FEET_R_GROUND:.0f}")
