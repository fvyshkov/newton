#!/usr/bin/env python3
"""Схема азимута v2: разрез (механизм + перевёрнутый мотор на подставке) + план."""
import math
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyArrowPatch, Polygon as MPoly

import generate_az2 as G

PLASTIC = "#d98a3d"; PLASTIC_E = "#9c5e22"
ROT = "#e0a94a"     # вращающееся кольцо (светлее)
METAL = "#9aa3ad";  METAL_E = "#4a4f55"
TEFLON = "#e8f0f5"; TEFLON_E = "#7fa8bf"
MAGNET = "#c0392b"; PCB = "#1f7a3a"
WOOD = "#caa472"

OUT = Path(__file__).parent


def rect(ax, x, y, w, h, fc, ec=PLASTIC_E, hatch=None, z=3, lw=1.4, alpha=1):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec,
                           linewidth=lw, hatch=hatch, zorder=z, alpha=alpha))


def lbl(ax, x, y, t, tx, ty, c="#222", ha="left", fs=9.5):
    ax.annotate(t, xy=(x, y), xytext=(tx, ty), fontsize=fs, ha=ha, va="center",
                color=c, arrowprops=dict(arrowstyle="->", color=c, lw=1.1), zorder=30)


# ============================ ГЕОМЕТРИЯ РАЗРЕЗА (без подписей) ============================
def draw_geometry(ax):
    # фанера
    rect(ax, -290, -16, 580, 16, WOOD, "#8a6d3b", hatch="////", z=1)

    for s in (-1, 1):   # обе стороны от оси
        xr = lambda R0, R1: (s * R0 if s > 0 else s * R1)   # левый край блока
        w = lambda R0, R1: (R1 - R0)
        # неподвижное кольцо (тело z0..8) + буртик (z8..17)
        rect(ax, xr(G.FIX_R_IN, G.FIX_R_OUT), 0, w(G.FIX_R_IN, G.FIX_R_OUT),
             G.BODY_T, PLASTIC, z=4)
        rect(ax, xr(G.LIP_R_IN, G.LIP_R_OUT), G.FIX_Z1, w(G.LIP_R_IN, G.LIP_R_OUT),
             G.LIP_Z1 - G.FIX_Z1, PLASTIC, z=6)
        # тефлоновый пятачок
        rect(ax, xr(G.PAD_R - 7, G.PAD_R + 7), G.FIX_Z1, 14, G.PTFE_GAP + 0.4,
             TEFLON, TEFLON_E, z=7)
        # вращающееся кольцо тело z9..17 + зубья z9..19
        rect(ax, xr(G.ROT_R_IN, G.BODY_R_OUT), G.ROT_Z0, w(G.ROT_R_IN, G.BODY_R_OUT),
             G.BODY_T, ROT, z=8)
        rect(ax, xr(G.RIM_R_IN, G.RING_TIP_R), G.ROT_Z0, w(G.RIM_R_IN, G.RING_TIP_R),
             G.RIM_H, ROT, z=8)
        for k in range(3):   # зубцы наружу
            zc = G.ROT_Z0 + 2 + k * 3
            tx = s * G.RING_TIP_R
            ax.add_patch(MPoly([(tx, zc), (tx + s * 4, zc + 1.5), (tx, zc + 3)],
                               closed=True, facecolor=ROT, edgecolor=PLASTIC_E,
                               lw=0.8, zorder=8))

    # ЦЕНТР: колонна энкодера + спайдер + магнит + чип
    plat_top = G.CHIP_TOP_Z - G.BOARD_WALL - G.BOARD_BOSS_H
    rect(ax, -35, 0, 70, 6, PLASTIC, z=5)
    rect(ax, -20, 0, 40, plat_top, PLASTIC, z=5)
    rect(ax, -17, plat_top, 34, G.BOARD_WALL, PLASTIC, z=6)
    rect(ax, -14, G.CHIP_TOP_Z - 1.6, 28, 1.6, PCB, "#14562a", z=9)
    rect(ax, -4, G.CHIP_TOP_Z, 8, 1.2, "#333", "#000", z=10)
    for s in (-1, 1):   # лучи спайдера
        rect(ax, (0 if s > 0 else -190.5), G.ROT_Z1, 190.5, 3.0, ROT, PLASTIC_E, z=11)
    rect(ax, -10, G.ROT_Z1, 20, 5, ROT, PLASTIC_E, z=12)
    rect(ax, -G.MAGNET_D/2, G.MAG_FACE_Z, G.MAGNET_D, G.MAGNET_H, MAGNET, "#7b241c", z=13)

    # стойка (лево)
    rect(ax, -(G.POST_R + 15), G.ROT_Z1, 30, G.POST_BOSS_H, ROT, PLASTIC_E, z=9)
    rect(ax, -(G.POST_R + 11), G.ROT_Z1 + 8, 22, 55, METAL, METAL_E, z=8)

    # перевёрнутый мотор на подставке (право). R-координаты соответствуют детали:
    #   плита R218..274 (внутр. край над телом кольца, вне мётлы стоек)
    #   ноги в стороне от плоскости разреза (штрих) R233..267
    #   мотор R219..261, вал/шестерня по оси R240 вниз
    px = G.CENTER_DIST
    ax.add_patch(Rectangle((233, 0), 34, G.PED_TOP_Z, fill=False, ec=PLASTIC_E,
                           lw=1.1, ls="--", zorder=3))                       # ноги (штрих)
    rect(ax, 262, 0, 8, G.PED_TOP_Z, PLASTIC, z=4)                          # задняя стенка
    rect(ax, 218, G.PED_TOP_Z - G.PED_PLATE_T, 56, G.PED_PLATE_T, PLASTIC, z=6)  # плита
    rect(ax, 219, G.PED_TOP_Z, 42, 40, METAL, METAL_E, z=9)                 # корпус NEMA17
    ax.text(px, G.PED_TOP_Z + 20, "NEMA17\n(перевёрнут,\nосью ВНИЗ)", fontsize=8.5,
            color="w", ha="center", va="center", zorder=12, weight="bold")
    rect(ax, px - 2.5, 8, 5, G.PED_TOP_Z - 4, METAL, METAL_E, z=8)          # вал вниз
    rect(ax, px - 18, 8, 36, 10, "#b5762e", PLASTIC_E, z=10)                # шестерня 16T
    ax.text(px, 13, "16T", fontsize=8, color="w", ha="center", va="center", zorder=11)


def panel_drive(ax):
    ax.set_title("РАЗРЕЗ — ПРИВОД (справа) и опора кольца", fontsize=11.5, pad=8)
    draw_geometry(ax)
    px = G.CENTER_DIST
    ax.add_patch(FancyArrowPatch((px - 24, G.PED_TOP_Z + 3), (px + 8, G.PED_TOP_Z + 3),
                 arrowstyle="<->", mutation_scale=13, color="#0a6", lw=2, zorder=15))
    ax.text(px - 8, G.PED_TOP_Z + 7, "прорези = натяг", fontsize=8.5,
            color="#0a6", ha="center", zorder=15)
    lbl(ax, G.RING_TIP_R, G.ROT_Z0 + 5, "зубья НАРУЖУ", 172, 55, c=PLASTIC_E)
    lbl(ax, G.PAD_R, G.FIX_Z1 + 0.7, "тефлон-пятачки", 178, 40, c=TEFLON_E)
    lbl(ax, G.LIP_R_OUT, 13, "буртик R185\n(центрирует)", 176, 66, c="#b00")
    lbl(ax, px, 13, "шестерня 16T\nна валу Ø5", 200, 62, c=PLASTIC_E)
    lbl(ax, (G.FIX_R_IN+G.FIX_R_OUT)/2, 4, "неподвиж. кольцо\n→ фанера M4",
        176, -13, c=PLASTIC_E)
    lbl(ax, (G.ROT_R_IN+G.BODY_R_OUT)/2, G.ROT_Z1, "вращ. кольцо", 250, 46, c="#a06a1a")
    ax.set_xlim(162, 306); ax.set_ylim(-18, 74)
    ax.set_aspect("equal"); ax.axis("off")


def panel_center(ax):
    ax.set_title("РАЗРЕЗ — ЦЕНТР (энкодер по оси)", fontsize=11.5, pad=8)
    draw_geometry(ax)
    ax.annotate("", xy=(0, G.CHIP_TOP_Z + 0.2), xytext=(0, G.MAG_FACE_Z - 0.2),
                arrowprops=dict(arrowstyle="<->", color="#b00", lw=1.2), zorder=20)
    ax.text(3, (G.CHIP_TOP_Z + G.MAG_FACE_Z) / 2, f"зазор {G.AIR_GAP}", fontsize=8.5,
            color="#b00", va="center", zorder=20)
    lbl(ax, 0, G.MAG_FACE_Z + G.MAGNET_H, "магнит Ø6 на спайдере\n(вращается, по центру)",
        18, 24, c=MAGNET)
    lbl(ax, 0, G.CHIP_TOP_Z, "чип AS5048A (неподвижен)", 20, 8, c=PCB)
    lbl(ax, 25, G.ROT_Z1 + 1.5, "спайдер (4 луча)", 30, 20, c="#a06a1a")
    lbl(ax, -18, 5, "колонна\n(на фанере)", -55, 14, c=PLASTIC_E)
    ax.set_xlim(-58, 82); ax.set_ylim(-6, 27)
    ax.set_aspect("equal"); ax.axis("off")


# ============================ ПЛАН ============================
def plan(ax):
    ax.set_title("ВИД СВЕРХУ", fontsize=12, pad=10)
    # кольцо: наружный (зубья) и внутренний борт
    ax.add_patch(Circle((0, 0), G.RING_TIP_R, fill=False, ec=PLASTIC_E, lw=1.0, zorder=3))
    ax.add_patch(Circle((0, 0), G.BODY_R_OUT, fc=ROT, ec=PLASTIC_E, lw=1.2, zorder=2))
    ax.add_patch(Circle((0, 0), G.ROT_R_IN, fc="white", ec=PLASTIC_E, lw=1.2, zorder=4))
    # зубья (штрихи наружу)
    for k in range(0, G.RING_TEETH, 2):
        a = math.radians(k * 360 / G.RING_TEETH)
        ax.plot([G.RING_ROOT_R*math.cos(a), G.RING_TIP_R*math.cos(a)],
                [G.RING_ROOT_R*math.sin(a), G.RING_TIP_R*math.sin(a)],
                color=PLASTIC_E, lw=0.4, zorder=3)
    # буртик (внутр)
    ax.add_patch(Circle((0, 0), G.LIP_R_OUT, fill=False, ec="#b00", lw=1.0, ls="--", zorder=5))
    # стыки 4 сегментов (joints at 0/90/180/270), центры сегментов 45..
    for jang in (0, 90, 180, 270):
        a = math.radians(jang)
        ax.plot([G.ROT_R_IN*math.cos(a), G.RING_TIP_R*math.cos(a)],
                [G.ROT_R_IN*math.sin(a), G.RING_TIP_R*math.sin(a)],
                color="#333", lw=1.6, zorder=6)
    # тефлоновые пятачки
    for k in range(G.PAD_N):
        a = math.radians((k + 0.5) * 360 / G.PAD_N)
        ax.add_patch(Circle((G.PAD_R*math.cos(a), G.PAD_R*math.sin(a)), G.PAD_D/2,
                            fc=TEFLON, ec=TEFLON_E, lw=0.8, zorder=7))
    # стойки (4, по центрам сегментов 45/135/225/315)
    for pang in (45, 135, 225, 315):
        a = math.radians(pang)
        ax.add_patch(Circle((G.POST_R*math.cos(a), G.POST_R*math.sin(a)),
                            G.POST_BOSS_D/2, fc="#cf9b52", ec=PLASTIC_E, lw=1.2, zorder=9))
        ax.add_patch(Circle((G.POST_R*math.cos(a), G.POST_R*math.sin(a)),
                            G.POST_TUBE_D/2, fc=METAL, ec=METAL_E, lw=1.0, zorder=10))
    # спайдер (4 луча) + магнит + чип
    for aang in (45, 135, 225, 315):
        a = math.radians(aang)
        ax.plot([0, (G.ROT_R_IN)*math.cos(a)], [0, (G.ROT_R_IN)*math.sin(a)],
                color=ROT, lw=4, zorder=11, solid_capstyle="round")
    ax.add_patch(Circle((0, 0), 10, fc=ROT, ec=PLASTIC_E, lw=1, zorder=12))
    ax.add_patch(Circle((0, 0), G.MAGNET_D/2, fc=MAGNET, ec="#7b241c", zorder=13))
    # привод: шестерня + мотор на 270° (−Y)
    mx, my = 0, -G.CENTER_DIST
    ax.add_patch(Circle((mx, my), G.PIN_TIP_R, fc="#b5762e", ec=PLASTIC_E, lw=1, zorder=9))
    for k in range(G.PIN_TEETH):
        a = math.radians(k*360/G.PIN_TEETH)
        ax.plot([mx+G.PIN_ROOT_R*math.cos(a), mx+G.PIN_TIP_R*math.cos(a)],
                [my+G.PIN_ROOT_R*math.sin(a), my+G.PIN_TIP_R*math.sin(a)],
                color=PLASTIC_E, lw=0.5, zorder=9)
    ax.add_patch(Rectangle((mx-21, my-30), 42, 42, fc=METAL, ec=METAL_E, lw=1.4, zorder=8))
    ax.text(mx, my-9, "NEMA17\nна подставке", fontsize=8, color="w", ha="center",
            va="center", zorder=9, weight="bold")
    # мётла стоек (внешний край боссов) и внутр. край плиты подставки — зазор
    sweep = G.POST_R + G.POST_BOSS_D / 2
    ax.add_patch(Circle((0, 0), sweep, fill=False, ec="#0a6", lw=0.9, ls=":", zorder=5))
    ax.text(0, sweep + 6, "мётла стоек", fontsize=7.5, color="#0a6", ha="center", zorder=20)

    ax.annotate("вращается\n(лёгкое)", xy=(G.POST_R*math.cos(math.radians(45)),
                G.POST_R*math.sin(math.radians(45))), xytext=(150, 150),
                fontsize=9, color=PLASTIC_E,
                arrowprops=dict(arrowstyle="->", color=PLASTIC_E, lw=1.1))
    ax.text(0, G.LIP_R_OUT+8, "буртик R185", fontsize=8, color="#b00", ha="center", zorder=20)

    lim = 285
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)
    ax.set_aspect("equal"); ax.axis("off")


fig = plt.figure(figsize=(20, 10))
gs = fig.add_gridspec(2, 2, width_ratios=[1.05, 1.0], height_ratios=[1.0, 1.0])
panel_drive(fig.add_subplot(gs[0, 0]))
panel_center(fig.add_subplot(gs[1, 0]))
plan(fig.add_subplot(gs[:, 1]))
fig.suptitle("Азимут v2 — осевой поворотный узел («ленивая Сюзанна»), венец Ø452, привод 14:1 (обычный NEMA17)",
             fontsize=15, y=0.99)
fig.tight_layout(rect=[0, 0, 1, 0.97])
p = OUT / "az2_scheme.png"
fig.savefig(p, dpi=120, bbox_inches="tight")
print(f"saved -> {p}")
