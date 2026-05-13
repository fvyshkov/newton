# Заказ Galboreg — болты/гайки/шайбы для Newton 8"

**Магазин**: [galboreg-shop.co.il](https://galboreg-shop.co.il)
**Дата**: 2026-05-07
**Статус**: ✅ **ОПЛАЧЕНО**.

## Позиции (с учётом site min order = 5)

| # | Назначение | Hebrew | Кол-во | Цена/шт | Сумма | Ссылка |
|---|---|---|---:|---:|---:|---|
| 1 | M5×12 болт hex | בורג פלדה מגולבן M5X12 | 20 | ₪1.42 | ₪28.40 | [12232](https://galboreg-shop.co.il/index.php?route=product/product&product_id=12232) |
| 2 | M5×20 pull-болт | בורג פלדה מגולבן M5X20 | 5 | ₪1.53 | ₪7.65 | [12234](https://galboreg-shop.co.il/index.php?route=product/product&product_id=12234) |
| 3 | M5×50 push-болт | בורג פלדה מגולבן M5X50 | 5 | ₪2.12 | ₪10.60 | [12240](https://galboreg-shop.co.il/index.php?route=product/product&product_id=12240) |
| 4 | M10×60 partial thread | בורג פלדה מגולבן (הברגה חלקית) M10X60 | 5 | ₪4.13 | ₪20.65 | [12396](https://galboreg-shop.co.il/index.php?route=product/product&product_id=12396) |
| 5 | M5 гайка hex | אום מגולוון M5 | 20 | ₪0.35 | ₪7.00 | [2284](https://galboreg-shop.co.il/index.php?route=product/product&product_id=2284) |
| 6 | M5 барашковая гайка | אום כנף מגולוון M5 | 5 | ₪3.54 | ₪17.70 | [2068](https://galboreg-shop.co.il/index.php?route=product/product&product_id=2068) |
| 7 | M5 nylock | אום ניילוק מגולוון M5 | 5 | ₪0.71 | ₪3.55 | [2197](https://galboreg-shop.co.il/index.php?route=product/product&product_id=2197) |
| 8 | M10 гайка hex | אום מגולוון M10 | 5 | ₪0.83 | ₪4.15 | [2288](https://galboreg-shop.co.il/index.php?route=product/product&product_id=2288) |
| 9 | M10 fender washer | דיסקית רחבה מגולבנת M10 | 5 | ₪2.66 | ₪13.30 | [1624](https://galboreg-shop.co.il/index.php?route=product/product&product_id=1624) |
| 10 | Шуруп по дереву 4×40 | סיבית שטוח פיליפס מגולבן 4X40 | 30 | ₪0.90 | ₪27.00 | [4209](https://galboreg-shop.co.il/index.php?route=product/product&product_id=4209) |

**Подытог: ₪163.00** (вкл. НДС, без доставки)
**Доставка (flat ₪39.00)** + zcredit
**Итого: ~₪202.00**

## Заметки

- 7 из 10 позиций пришлось округлить до qty=5 — у Galboreg минимальный заказ позиции = 5 шт. Излишки = запас на будущее.
- Все болты — оцинкованная сталь (פלדה מגולבן). M10×60 — partial thread (для гладкой шейки rocker box).
- Wood screw — סיבית (chipboard screw, флэт-Phillips), 4×40.

## Чего нет на galboreg

- **Пружина сжатия M5 ~20 мм** (3 шт) — `קפיץ לחץ` пустой. → ACE локально.
- **Сонотуб, краска, силикон, войлочные прокладки** — Home Center / звонок (см. order_draft_supplies.md).

## Как оплатить

```bash
python3 /Users/mac/med/scripts/_browser_kit/sites/galboreg.py checkout
```

Скрипт открывает /checkout/checkout, выбирает доставку flat.flat ₪39, payment=zcredit, ставит agree, заполняет адрес из address book. Ты только нажимаешь **«אשר הזמנה»** → редирект на z-credit → вводишь карту.

Скриншот финальной формы: `/Users/mac/med/scripts/_browser_kit/sites/_dumps/galboreg/checkout_final.png`
