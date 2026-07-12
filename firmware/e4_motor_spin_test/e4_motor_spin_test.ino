/*
 * e4_motor_spin_test — минимальный «оживи мотор» для FYSETC E4 v1.0
 * (ESP32-WROOM-32 + 4× впаянных TMC2209 на общей UART-шине).
 *
 * ЧТО ДЕЛАЕТ: задаёт ток драйверам по UART и крутит мотор в разъёме X
 * (азимут / Axis1) — оборот в одну сторону, оборот в другую, по кругу.
 *
 * У E4 нет крутилок-Vref: ток можно задать ТОЛЬКО по UART. Поэтому обычный
 * STEP/DIR-скетч без UART тут не поедет — ток будет 0. Ниже настраиваем ток
 * по UART, потом шагаем.
 *
 * --- АППАРАТНАЯ ПОДГОТОВКА ПЛАТЫ (один раз, ОБЯЗАТЕЛЬНО) ---
 *   1. Снять все заводские шунты-джамперы с драйверов.
 *   2. Поставить ОДИН джампер Z-Min -> PDN (заводит UART-шину TMC на GPIO15).
 *   3. Мотор — в разъём X. Пары обмоток вместе: Чёрн+Зел = катушка A,
 *      Красн+Син = катушка B (звонятся ~1.4 Ω внутри пары).
 *   4. Питание: 12 В в зелёный винтовой клеммник Vin/GND (полярность
 *      ПРОВЕРИТЬ тестером — защиты от переполюсовки НЕТ). USB — для прошивки
 *      и питания ESP32. Для вращения нужны ОБА: USB + 12 В.
 *   !!! Мотор НИКОГДА не втыкать/вынимать под напряжением — убьёт TMC2209.
 *
 * --- TOOLCHAIN ---
 *   Плата: "ESP32 Dev Module".  ESP32 Arduino core 2.0.17.
 *   Библиотека: "TMCStepper" (teemuatlut) через Library Manager.
 *   Драйвер CH340 + ДАТА-USB-кабель. Если esptool "Failed to connect" —
 *   держать BOOT при старте заливки (или 10µF между EN и GND).
 */

#include <TMCStepper.h>

// --- пины E4 (из Pins.FYSETC_E4.h) ---
#define EN_PIN    25      // общий ENABLE всех драйверов, активен НИЗким
#define STEP_PIN  27      // X = Axis1 = азимут
#define DIR_PIN   26

// UART к драйверам. ВАРИАНТ A (без переделок платы, ПРОБУЙ ПЕРВЫМ):
//   заводские 2 синих джампера на месте -> UART TMC висит на GPIO21/22 (SCL/SDA).
#define TMC_RX    21
#define TMC_TX    22
// Если молчит — поменять местами (RX 22 / TX 21).
// ВАРИАНТ B (канон OnStep): снять 2 синих джампера + провод Z-MIN->PDN,
//   тогда single-wire: #define TMC_RX 15  и  #define TMC_TX 15.

#define R_SENSE   0.11f   // сенс-резистор TMC2209 на E4 (если ток врёт — тут 0.10/0.12)
#define CURRENT   400     // ток RMS, мА (стендовый безопасный 300..600; НЕ 2000!)
#define USTEPS    16      // микрошаг

HardwareSerial &tmc = Serial1;

// Один и тот же драйвер по всем 4 адресам — какой из них реально X, тот и
// настроится. Шагаем всё равно только по пинам X.
TMC2209Stepper drv[4] = {
  TMC2209Stepper(&tmc, R_SENSE, 0),
  TMC2209Stepper(&tmc, R_SENSE, 1),
  TMC2209Stepper(&tmc, R_SENSE, 2),
  TMC2209Stepper(&tmc, R_SENSE, 3),
};

void configure(TMC2209Stepper &d) {
  d.begin();                 // pdn_disable(true)=UART, I_scale_analog(false)=ток из регистра
  d.toff(4);                 // включить силовой каскад
  d.rms_current(CURRENT);
  d.microsteps(USTEPS);
  d.pwm_autoscale(true);     // StealthChop
}

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\nE4 motor spin test");

  pinMode(EN_PIN, OUTPUT);   digitalWrite(EN_PIN, HIGH);  // выкл, пока настраиваем ток
  pinMode(STEP_PIN, OUTPUT); digitalWrite(STEP_PIN, LOW);
  pinMode(DIR_PIN, OUTPUT);  digitalWrite(DIR_PIN, HIGH);

  // UART к драйверам (пишем «вслепую» — ответы не читаем, чтения не нужно).
  tmc.begin(115200, SERIAL_8N1, TMC_RX, TMC_TX);
  delay(200);
  for (int i = 0; i < 4; i++) configure(drv[i]);

  digitalWrite(EN_PIN, LOW);  // включить драйверы (активен низким)
  Serial.println("drivers on -> spinning X (azimuth)");
}

const long STEPS_PER_REV = 200L * USTEPS;   // 3200

void loop() {
  for (long i = 0; i < STEPS_PER_REV; i++) {
    digitalWrite(STEP_PIN, HIGH); delayMicroseconds(500);
    digitalWrite(STEP_PIN, LOW);  delayMicroseconds(500);
  }
  Serial.println("1 rev done, reversing");
  delay(400);
  digitalWrite(DIR_PIN, !digitalRead(DIR_PIN));  // сменить направление
}
