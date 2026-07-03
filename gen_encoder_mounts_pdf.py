#!/usr/bin/env python3
"""
encoder_mounts.pdf — где и как ставить магнит + датчик AS5048A на наш Добсон.

Страницы:
  1. Титул + легенда
  2. Принцип: чип + магнит, зазор, "один крутится — другой стоит"
  3. Азимут (M10 болт)
  4. Высота (боковой круг R100, ось-пенёк по центру)
  5. Две печатные детали: колпачок с магнитом + кронштейн датчика
  6+. Реальные фото / диаграммы из найденных источников (что удалось скачать)
  посл. Полный список ссылок (включая то, что не вшилось)

Нарисованные чертежи генерятся всегда; фото-страницы — best-effort
(сайты за Cloudflare могут не отдать, тогда ссылка уходит в список).
"""
from pathlib import Path
import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle, Circle, Wedge, FancyArrowPatch, Polygon, FancyBboxPatch
import numpy as np
import requests
import fitz  # PyMuPDF
from PIL import Image

ROOT = Path(__file__).parent
OUT = ROOT / "encoder_mounts.pdf"
A4 = (8.27, 11.69)  # portrait, inches

# --- цветовая легенда -------------------------------------------------------
C_MOVE = "#E8923C"   # крутится
C_FIX  = "#9AA0A6"   # неподвижно
C_FIX2 = "#C7CBD1"
C_N    = "#D33A2C"   # магнит N
C_S    = "#2C6BD3"   # магнит S
C_CHIP = "#2E9B57"   # чип/плата
C_WOOD = "#D9B98A"   # дерево
C_TXT  = "#1a1a1a"

HEAD = dict(ha="center", va="center", fontsize=15, fontweight="bold", color=C_TXT)
LBL  = dict(fontsize=10.5, color=C_TXT)
SML  = dict(fontsize=9, color="#444")


def new_page(pdf, title):
    fig = plt.figure(figsize=A4)
    ax = fig.add_axes([0.06, 0.06, 0.88, 0.86])
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.set_aspect("equal")
    ax.axis("off")
    fig.text(0.5, 0.955, title, **HEAD)
    return fig, ax


def magnet_side(ax, x, y, w, h, label=True):
    """Магнит сбоку: левая половина N (красная), правая S (синяя)."""
    ax.add_patch(Rectangle((x - w/2, y), w/2, h, fc=C_N, ec="k", lw=1.2))
    ax.add_patch(Rectangle((x, y), w/2, h, fc=C_S, ec="k", lw=1.2))
    ax.text(x - w/4, y + h/2, "N", ha="center", va="center", color="w", fontweight="bold", fontsize=11)
    ax.text(x + w/4, y + h/2, "S", ha="center", va="center", color="w", fontweight="bold", fontsize=11)
    if label:
        ax.annotate("магнит\n(намагничен ПОПЕРЁК, N|S по диаметру)",
                    xy=(x + w/2, y + h/2), xytext=(x + w/2 + 14, y + h/2 + 6),
                    arrowprops=dict(arrowstyle="->", lw=1.2), **SML)


def magnet_top(ax, cx, cy, r, axial=False):
    """Магнит сверху: диаметральный (N|S слева/справа) или осевой (крест = не работает)."""
    if axial:
        ax.add_patch(Circle((cx, cy), r, fc="#bbb", ec="k", lw=1.2))
        d = r * 0.72
        ax.plot([cx - d, cx + d], [cy - d, cy + d], color=C_N, lw=4)
        ax.plot([cx - d, cx + d], [cy + d, cy - d], color=C_N, lw=4)
    else:
        ax.add_patch(Wedge((cx, cy), r, 90, 270, fc=C_N, ec="k", lw=1.2))
        ax.add_patch(Wedge((cx, cy), r, 270, 90, fc=C_S, ec="k", lw=1.2))
        ax.text(cx - r/2, cy, "N", ha="center", va="center", color="w", fontweight="bold")
        ax.text(cx + r/2, cy, "S", ha="center", va="center", color="w", fontweight="bold")


def rot_arrow(ax, cx, cy, r, color=C_MOVE, txt="крутится"):
    a = FancyArrowPatch((cx + r, cy), (cx, cy + r),
                        connectionstyle="arc3,rad=0.45",
                        arrowstyle="-|>", mutation_scale=16, lw=2, color=color)
    ax.add_patch(a)
    ax.text(cx + r*0.85, cy + r*0.85, txt, fontsize=9, color=color, fontweight="bold")


def gap_marker(ax, x, y0, y1, txt):
    """Чистая скоба зазора (без схлопывающихся стрелок)."""
    ax.plot([x, x], [y0, y1], color="#222", lw=1.2)
    ax.plot([x - 0.9, x + 0.9], [y0, y0], color="#222", lw=1.2)
    ax.plot([x - 0.9, x + 0.9], [y1, y1], color="#222", lw=1.2)
    ax.text(x + 2.5, (y0 + y1) / 2, txt, fontsize=9, color="#222", va="center")


# ===========================================================================
# СТРАНИЦА 1 — титул + легенда
# ===========================================================================
def page_title(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.5, 0.80, "Энкодеры AS5048A на нашем Добсоне", ha="center",
             fontsize=22, fontweight="bold", color=C_TXT)
    fig.text(0.5, 0.745, "куда ставится магнит и датчик на каждой оси", ha="center",
             fontsize=13, color="#444")

    ax = fig.add_axes([0.12, 0.30, 0.76, 0.36]); ax.axis("off")
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.set_aspect("equal")
    items = [
        (C_MOVE, "оранжевый — деталь КРУТИТСЯ (труба / рокер / болт)"),
        (C_FIX,  "серый — деталь НЕПОДВИЖНА (кронштейн на корпусе)"),
        (C_N,    "красный = N, синий = S — магнит (намагничен ПОПЕРЁК)"),
        (C_CHIP, "зелёный — чип/плата AS5048A"),
        (C_WOOD, "бежевый — дерево/фанера"),
    ]
    y = 92
    ax.text(0, y + 6, "Условные обозначения:", fontsize=12, fontweight="bold")
    for col, t in items:
        ax.add_patch(Rectangle((2, y - 3.2), 7, 5, fc=col, ec="k", lw=0.8))
        ax.text(13, y - 0.6, t, fontsize=11, va="center")
        y -= 12

    fig.text(0.5, 0.14,
             "Главное правило (повторяется на всех чертежах):\n"
             "магнит — на вращающейся детали, чип — на неподвижном кронштейне,\n"
             "они СООСНЫ (на одной оси) и разделены воздушным зазором ~1 мм. Контакта нет.",
             ha="center", fontsize=11.5, color=C_TXT,
             bbox=dict(boxstyle="round,pad=0.6", fc="#FFF6E9", ec=C_MOVE, lw=1.4))
    pdf.savefig(fig); plt.close(fig)


# ===========================================================================
# СТРАНИЦА 2 — принцип
# ===========================================================================
def page_principle(pdf):
    fig, ax = new_page(pdf, "1. Принцип: чип «видит» торец магнита")

    # --- ВЕРХ: главный чертёж (снизу вверх) ---
    cx = 42
    ax.add_patch(Rectangle((cx-22, 66), 44, 6, fc=C_FIX, ec="k", lw=1, hatch="///"))
    ax.text(cx, 63, "НЕПОДВИЖНЫЙ кронштейн", ha="center", **SML)
    ax.add_patch(Rectangle((cx-12, 72), 24, 4.5, fc="#1b5e20", ec="k", lw=1))   # плата
    ax.add_patch(Rectangle((cx-4.5, 76.5), 9, 4.5, fc=C_CHIP, ec="k", lw=1))    # чип
    ax.text(cx+16, 74, "плата AS5048A\n(чип смотрит вверх)", **SML, va="center")

    magnet_side(ax, cx, 87, 12, 7)
    rot_arrow(ax, cx, 90.5, 12)
    gap_marker(ax, cx, 81, 87, "зазор\n0.5–1.5 мм\n(воздух)")

    # --- СЕРЕДИНА: описание ---
    ax.text(50, 55,
            "Чип неподвижен. Магнит крутится прямо над ним, соосно.\n"
            "Чип читает угол поворота → число 0…16383 (14 бит).",
            ha="center", fontsize=11,
            bbox=dict(boxstyle="round,pad=0.5", fc="#F4F6F8", ec="#bbb", lw=1))

    # --- НИЗ: правильный vs неправильный магнит (вид сверху на торец) ---
    ax.text(50, 44, "Каким должен быть магнит (вид сверху на торец):",
            ha="center", fontsize=11, fontweight="bold")
    magnet_top(ax, 28, 30, 8, axial=False)
    ax.text(28, 17, "ПРАВИЛЬНО\nдиаметральный\n(N|S по бокам)",
            ha="center", fontsize=9.5, color=C_CHIP, fontweight="bold")
    magnet_top(ax, 72, 30, 8, axial=True)
    ax.text(72, 17, "НЕ РАБОТАЕТ\nосевой\n(N сверху, S снизу)",
            ha="center", fontsize=9.5, color=C_N, fontweight="bold")
    pdf.savefig(fig); plt.close(fig)


# ===========================================================================
# СТРАНИЦА 3 — азимут
# ===========================================================================
def page_azimuth(pdf):
    fig, ax = new_page(pdf, "2. Азимут — узел ПОД базой, на конце болта")

    # пояснение сверху
    ax.text(50, 94,
            "Магнит и чип — на РАЗНЫХ досках (одна крутится, другая стоит), обе по центру болта.\n"
            "Кто сверху/снизу — НЕважно. Между досками всего ~3 мм, поэтому узел выносим ПОД базу.",
            ha="center", fontsize=10,
            bbox=dict(boxstyle="round,pad=0.5", fc="#FFF6E9", ec=C_MOVE, lw=1.2))

    # --- дно рокера (крутится) ---
    ax.add_patch(Rectangle((18, 74), 64, 7, fc=C_MOVE, ec="k", lw=1))
    ax.text(50, 77.5, "дно рокера — КРУТИТСЯ с трубой", ha="center", fontsize=9,
            color="white", fontweight="bold")
    # голова болта закреплена в рокере
    ax.add_patch(Rectangle((45, 74.5), 10, 4.5, fc=C_FIX, ec="k", lw=1))
    ax.annotate("болт закреплён В РОКЕРЕ\n→ крутится вместе с трубой",
                xy=(55, 76.5), xytext=(70, 86), **SML,
                arrowprops=dict(arrowstyle="->", lw=1))
    # PTFE-пятаки
    for px in (30, 70):
        ax.add_patch(Rectangle((px-2, 70.5), 4, 2, fc="white", ec="k", lw=0.6))
    ax.text(15, 71.5, "PTFE\n~3 мм", ha="center", **SML)

    # --- опорная доска (неподвижна) ---
    ax.add_patch(Rectangle((12, 61), 76, 9, fc=C_WOOD, ec="k", lw=1))
    ax.text(50, 65.5, "опорная доска — НЕПОДВИЖНА", ha="center", fontsize=9)

    # --- болт сквозь всё, торчит вниз ---
    ax.add_patch(Rectangle((47.5, 38), 5, 41, fc=C_FIX, ec="k", lw=1))
    ax.text(50, 35.5, "болт M10 (СТАЛЬ)", ha="center", **SML)

    # --- ПОД базой: колпачок+магнит (крутятся) ---
    ax.add_patch(FancyBboxPatch((43.5, 49), 13, 7, boxstyle="round,pad=0.3",
                                fc=C_MOVE, ec="k", lw=1))
    magnet_side(ax, 50, 44, 11, 5, label=False)
    ax.annotate("колпачок с магнитом\nна конце болта — КРУТИТСЯ\n(пластик ≈5 мм отодвигает\nмагнит от стали болта)",
                xy=(56, 46), xytext=(63, 47), **SML,
                arrowprops=dict(arrowstyle="->", lw=1))
    rot_arrow(ax, 50, 52, 12)

    # --- чип на кронштейне под опорной доской (стоит), чипом ВВЕРХ ---
    ax.add_patch(Rectangle((62, 36), 3, 25, fc=C_FIX, ec="k", lw=1))    # арм к доске
    ax.add_patch(Rectangle((43, 36), 22, 3, fc=C_FIX, ec="k", lw=1))    # полка-держатель
    ax.add_patch(Rectangle((45, 39), 12, 2.6, fc="#1b5e20", ec="k", lw=1))  # плата
    ax.add_patch(Rectangle((47.5, 41.6), 5, 2.2, fc=C_CHIP, ec="k", lw=1))  # чип (вверх)
    ax.annotate("плата AS5048A на кронштейне\nПОД опорной доской — СТОИТ,\nчипом ВВЕРХ. Провода не\nзакручиваются.",
                xy=(46, 40), xytext=(8, 34), **SML,
                arrowprops=dict(arrowstyle="->", lw=1))

    gap_marker(ax, 58, 43.8, 41.5, "~1 мм")

    ax.text(50, 16,
            "Толкаешь по азимуту → рокер и болт с магнитом едут, чип на опорной доске стоит → угол.\n"
            "Хочешь наоборот? Закрепи болт в опорной доске, магнит на его конце (стоит),\n"
            "а чип — на рокере по центру (крутится над магнитом). Тоже верно.",
            ha="center", fontsize=9.5,
            bbox=dict(boxstyle="round,pad=0.5", fc="#EAF7EF", ec=C_CHIP, lw=1.1))
    pdf.savefig(fig); plt.close(fig)


# ===========================================================================
# СТРАНИЦА 4 — высота
# ===========================================================================
def _bearing(ax, cx, cy, r):
    """Полукруглый высотный подшипник (плоской гранью вверх, ось = центр сверху)."""
    ax.add_patch(Wedge((cx, cy), r, 180, 360, fc=C_WOOD, ec="k", lw=1.5))
    ax.add_patch(Circle((cx, cy), 1.4, fc=C_FIX, ec="k", lw=1))           # ось
    ax.plot([cx-2.4, cx+2.4], [cy, cy], "k", lw=0.7)
    ax.plot([cx, cx], [cy-2.4, cy+2.4], "k", lw=0.7)


def page_altitude(pdf):
    fig, ax = new_page(pdf, "3. Высота — у оси нет неподвижной опоры → 2 решения")

    ax.text(50, 95,
            "ЧИП — всегда на НЕПОДВИЖНОМ кронштейне (к нему провода). "
            "МАГНИТ/ролик — на КРУТЯЩЕМСЯ подшипнике.",
            ha="center", fontsize=9.5,
            bbox=dict(boxstyle="round,pad=0.45", fc="#F4F6F8", ec="#bbb", lw=1))

    # ===================== ВАРИАНТ A =====================
    ax.text(28, 88, "ВАРИАНТ A — магнит в ЦЕНТРЕ + кронштейн-мостик с чипом",
            ha="center", fontsize=10, fontweight="bold", color=C_CHIP)
    _bearing(ax, 28, 78, 15)
    ax.text(28, 65, "подшипник\n(крутится с трубой)", ha="center", fontsize=8)
    rot_arrow(ax, 28, 78, 17)
    # магнит в центре
    magnet_top(ax, 28, 78, 2.6, axial=False)
    ax.annotate("МАГНИТ приклеен\nв центр (крутится)", xy=(28, 78), xytext=(2, 64),
                **SML, arrowprops=dict(arrowstyle="->", lw=1))
    # неподвижный кронштейн-мостик от рокера к оси
    ax.add_patch(Rectangle((6, 56), 3.5, 26, fc=C_FIX, ec="k", lw=1))      # стойка на рокере
    ax.add_patch(Rectangle((6, 80), 24, 3, fc=C_FIX, ec="k", lw=1))        # мостик к оси
    ax.add_patch(Rectangle((25.5, 78.6), 5, 2.4, fc=C_CHIP, ec="k", lw=1)) # чип над центром
    ax.text(7, 53, "стойка на\nстенке рокера\n(неподвижна)", **SML, va="top")
    ax.annotate("ЧИП на мостике,\n~1 мм перед гранью", xy=(30, 79.5), xytext=(34, 84),
                **SML, arrowprops=dict(arrowstyle="->", lw=1))
    ax.text(50, 70,
            "1:1 → высота 0–90° = ¼ оборота →\n"
            "ИСТИННО АБСОЛЮТНЫЙ угол.\n"
            "Годится, пока до центра реально\n"
            "дотянуться жёстким кронштейном\n"
            "(небольшие подшипники ~R100).",
            fontsize=9.5, va="center",
            bbox=dict(boxstyle="round,pad=0.4", fc="#EAF7EF", ec=C_CHIP, lw=1))

    # ===================== ВАРИАНТ B =====================
    ax.text(28, 44, "ВАРИАНТ B — ролик/ремень по ОБОДУ (до центра НЕ тянемся)",
            ha="center", fontsize=10, fontweight="bold", color=C_MOVE)
    _bearing(ax, 28, 34, 15)
    ax.text(28, 26, "тот же\nподшипник", ha="center", fontsize=8)
    rot_arrow(ax, 28, 34, 17)
    # ролик у обода снизу + энкодер + кронштейн на рокере
    ax.add_patch(Circle((28, 17), 3.2, fc=C_FIX, ec="k", lw=1))            # ролик
    ax.add_patch(Circle((28, 17), 1.0, fc="#333"))
    ax.add_patch(Rectangle((20, 9), 16, 4, fc=C_FIX2, ec="k", lw=1))       # кронштейн/основание на рокере
    ax.add_patch(Rectangle((26.5, 12.5), 3, 2, fc="#1b5e20", ec="k", lw=1))# энкодер
    # пружина (зигзаг)
    sx = np.array([12, 13, 12, 13, 12, 13, 12]) + 6
    sy = np.linspace(11, 17, 7)
    ax.plot(sx, sy, color="#777", lw=1.2)
    ax.annotate("ролик с O-кольцом прижат\nк ОБОДУ (пружиной)", xy=(28, 19), xytext=(2, 22),
                **SML, arrowprops=dict(arrowstyle="->", lw=1))
    ax.text(40, 11, "энкодер на ролике;\nкронштейн на рокере\nУ САМОГО КРАЯ", **SML, va="center")
    ax.text(50, 34,
            "Кронштейн у обода, где рокер РЯДОМ —\n"
            "тянуться к центру не надо.\n"
            "Передача R/r множит разрешение.\n"
            "Для БОЛЬШИХ полукругов (как на фото).\n"
            "Для push-to ок (привязка по звёздам\n"
            "каждый раз компенсирует).",
            fontsize=9.5, va="center",
            bbox=dict(boxstyle="round,pad=0.4", fc="#FFF6E9", ec=C_MOVE, lw=1))
    pdf.savefig(fig); plt.close(fig)


# ===========================================================================
# СТРАНИЦА 5 — две детали
# ===========================================================================
def page_parts(pdf):
    fig, ax = new_page(pdf, "4. Две печатные детали (одинаковые на обе оси)")

    # Деталь А — колпачок с магнитом
    ax.text(27, 90, "А — колпачок с магнитом", ha="center", fontsize=12, fontweight="bold", color=C_MOVE)
    ax.add_patch(Rectangle((20, 40), 5, 22, fc=C_FIX, ec="k", lw=1))      # болт/пенёк
    ax.text(22.5, 36, "болт M10 /\nпенёк (сталь)", ha="center", **SML)
    ax.add_patch(FancyBboxPatch((14, 60), 17, 12, boxstyle="round,pad=0.3",
                                fc=C_MOVE, ec="k", lw=1.2))               # колпачок
    magnet_side(ax, 22.5, 72, 11, 5, label=False)
    ax.annotate("магнит запрессован сверху", xy=(22.5, 74), xytext=(33, 80),
                arrowprops=dict(arrowstyle="->", lw=1), **SML)
    ax.annotate("≈5 мм пластика\nмежду магнитом и сталью\n(иначе сталь портит поле)",
                xy=(22.5, 65), xytext=(33, 58),
                arrowprops=dict(arrowstyle="->", lw=1), **SML)

    # Деталь Б — кронштейн датчика
    ax.text(73, 90, "Б — кронштейн датчика", ha="center", fontsize=12, fontweight="bold", color=C_FIX)
    ax.add_patch(Rectangle((60, 30), 5, 30, fc=C_FIX, ec="k", lw=1))     # вертикальная стойка
    ax.add_patch(Rectangle((60, 58), 26, 4, fc=C_FIX, ec="k", lw=1))    # полка
    for hx in (62.5, 83.5):
        ax.add_patch(Circle((hx, 32 + (hx>70)*0), 0.0))  # noop
    ax.add_patch(Circle((62.5, 33), 1.1, fc="white", ec="k"))           # отв. крепления
    ax.add_patch(Circle((62.5, 38), 1.1, fc="white", ec="k"))
    ax.text(62.5, 27, "крепёж к корпусу", ha="center", **SML)
    ax.add_patch(Rectangle((70, 54), 14, 4, fc="#1b5e20", ec="k", lw=1))  # плата
    ax.add_patch(Rectangle((74, 51.5), 6, 3, fc=C_CHIP, ec="k", lw=1))    # чип
    ax.text(77, 64, "плата AS5048A\nчипом ВНИЗ", ha="center", **SML)
    magnet_side(ax, 77, 45, 9, 4.5, label=False)
    ax.text(90, 45, "← магнит\n(на детали А)", **SML, va="center")
    gap_marker(ax, 86, 49.5, 51.5, "зазор\n~1 мм")

    ax.text(50, 18,
            "Колпачок А — на каждую вращающуюся ось (болт M10 / пенёк в круге).\n"
            "Кронштейн Б — на неподвижный корпус, чип ровно по центру над магнитом.\n"
            "Печатаем PLA/PETG, по 2 шт каждой детали (азимут + высота).",
            ha="center", fontsize=10.5,
            bbox=dict(boxstyle="round,pad=0.5", fc="#EAF7EF", ec=C_CHIP, lw=1.2))
    pdf.savefig(fig); plt.close(fig)


# ===========================================================================
# РЕАЛЬНЫЕ ФОТО / ДИАГРАММЫ
# ===========================================================================
SESS = requests.Session()
SESS.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Accept": "image/avif,image/webp,image/*,*/*;q=0.8",
})

# (key, kind, url, page_index(for pdf), caption, source)
REFS = [
    ("alt_belt1", "img",
     "https://raw.githubusercontent.com/vlaate/DobsonianDSC/master/img/Alt_encoder_1.jpg", None,
     "АЛЬТЕРНАТИВА (вам НЕ нужна): ремень GT2 по ободу высотного круга → энкодер на стенке рокера. "
     "Так делают, когда центр оси недоступен. У вас центр доступен — см. чертёж 3.",
     "vlaate DobsonianDSC /img/Alt_encoder_1.jpg"),
    ("alt_belt2", "img",
     "https://raw.githubusercontent.com/vlaate/DobsonianDSC/master/img/Alt_encoder_2.jpg", None,
     "Тот же узел крупно: маленький шкив GT2 на валу энкодера цепляет ремень; "
     "энкодер в печатном кронштейне на стенке рокера.",
     "vlaate DobsonianDSC /img/Alt_encoder_2.jpg"),
    ("adapter_fig2", "pdf",
     "https://datasheet.octopart.com/AS5048A-AB-1.0-Austriamicrosystems-datasheet-17727185.pdf", 1,
     "ЭТАЛОННЫЙ ЧЕРТЁЖ. AS5048 Adapterboard, Fig.2 — разрез: вращающийся НЕферромагнитный держатель "
     "магнита Ø6×2.5 мм, зазор 0.5–2 мм, чип на неподвижной плате. Именно наша схема «магнит над чипом».",
     "AS5048A-AB Operation Manual, p.2, Fig.2"),
    ("ams_magnet", "pdf",
     "https://www.basecamelectronics.com/files/Encoders/AS5048_DS000298_3-00.pdf", 8,
     "Официальный datasheet ams AS5048A: требование к магниту — диаметральный (2-полюсный), "
     "эталон N35H Ø8×3 мм, зазор ~2 мм. Осевой магнит НЕ работает.",
     "ams AS5048A datasheet DS000298, p.9"),
    ("gso_alt", "pdf",
     "https://www.firstlightoptics.com/user/manuals/GSO-Encoder-Installation.pdf", 14,
     "Astro Devices / Nexus DSC — установка энкодеров на GSO-Добсон (как наш 8\"). "
     "Высотный узел: магнитная лента по ободу + ридер на стенке рокера, зазор 0.4 мм.",
     "Astro Devices GSO-Encoder-Installation.pdf (high-res фото)"),
]


def fetch_img(url):
    r = SESS.get(url, timeout=25)
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    return np.asarray(img)


def fetch_pdf_page(url, idx):
    r = SESS.get(url, timeout=40)
    r.raise_for_status()
    doc = fitz.open(stream=r.content, filetype="pdf")
    idx = max(0, min(idx, doc.page_count - 1))
    pix = doc[idx].get_pixmap(dpi=150)
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    return np.asarray(img)


def page_image(pdf, arr, caption, source):
    fig = plt.figure(figsize=A4)
    ax = fig.add_axes([0.06, 0.20, 0.88, 0.72]); ax.axis("off")
    ax.imshow(arr)
    fig.text(0.5, 0.15, caption, ha="center", va="top", fontsize=10.5, wrap=True,
             color=C_TXT)
    fig.text(0.5, 0.045, "источник: " + source, ha="center", fontsize=8, color="#777")
    pdf.savefig(fig); plt.close(fig)


# ===========================================================================
# СТРАНИЦА — все ссылки
# ===========================================================================
ALL_LINKS = [
    ("ГОТОВАЯ печатная модель магнитного DSC для Добсона (оба узла)",
     "thingiverse.com/thing:4221923  (xvedra DSC-V3, AS5600 — ставится как AS5048A)"),
    ("Эталонный разрез магнит/чип/зазор",
     "AS5048A-AB Operation Manual, Fig.2 (octopart PDF)"),
    ("Datasheet ams AS5048A (требования к магниту)",
     "basecamelectronics.com/files/Encoders/AS5048_DS000298_3-00.pdf"),
    ("Печатный держатель магнита+платы (адаптировать)",
     "printables.com/model/1493082  (AS5600 + подшипник 608)"),
    ("С исходником Fusion — подогнать размер (магнит сделать диаметральным!)",
     "github.com/scottbez1/AS5600Knob"),
    ("Высотный узел ремнём по ободу (фото)",
     "github.com/vlaate/DobsonianDSC  (/img/Alt_encoder_1.jpg, _2.jpg)"),
    ("Установка энкодеров на GSO-Добсон (как наш), много фото",
     "firstlightoptics.com/user/manuals/GSO-Encoder-Installation.pdf"),
    ("Заводской магнитный азимут (наглядно «диск + датчик»)",
     "orion-xt10.com/attach-azimuth-bearing.html"),
    ("Самая широкая подборка фото узлов на Добсонах (только в браузере)",
     "cloudynights.com/topic/772803-how-to-attach-altitude-encoders-to-dobsonians"),
    ("Прошивка push-to ESP32 → SkySafari",
     "github.com/grtyvr/DSS_32  (AS5048A) и github.com/vlaate/DobsonianDSC"),
]


def page_links(pdf, statuses):
    fig = plt.figure(figsize=A4)
    fig.text(0.5, 0.95, "Все ссылки (полный список)", **HEAD)
    ax = fig.add_axes([0.06, 0.08, 0.88, 0.82]); ax.axis("off")
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    y = 95
    for title, url in ALL_LINKS:
        ax.text(2, y, "• " + title, fontsize=10.5, fontweight="bold", va="top")
        y -= 3.8
        ax.text(6, y, url, fontsize=9.5, color="#2222aa", va="top")
        y -= 5.6
    n_ok = sum(1 for _, ok in statuses if ok)
    ax.text(2, 2, f"(в этот PDF вшито фото/диаграмм: {n_ok} из {len(statuses)})",
            fontsize=8.5, color="#777", va="bottom")
    pdf.savefig(fig); plt.close(fig)


# ===========================================================================
def main():
    statuses = []
    with PdfPages(OUT) as pdf:
        page_title(pdf)
        page_principle(pdf)
        page_azimuth(pdf)
        page_altitude(pdf)
        page_parts(pdf)
        for key, kind, url, idx, caption, source in REFS:
            try:
                arr = fetch_img(url) if kind == "img" else fetch_pdf_page(url, idx)
                page_image(pdf, arr, caption, source)
                statuses.append((key, True))
                print(f"OK   {key}")
            except Exception as e:
                statuses.append((key, False))
                print(f"SKIP {key}: {e}")
        page_links(pdf, statuses)
    print(f"\nwrote {OUT}  ({OUT.stat().st_size//1024} KB)")


if __name__ == "__main__":
    main()
