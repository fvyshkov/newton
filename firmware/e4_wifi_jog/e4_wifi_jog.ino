/*
 * e4_wifi_jog — управление моторами рокера по WiFi (FYSETC E4).
 *
 * Плата поднимает СВОЮ точку доступа (без интернета/роутера):
 *   SSID: "NewtonRocker" (открытая), заходишь в браузере на http://192.168.4.1
 *   и кнопками крутишь азимут (X) и высоту (Y).
 *
 * Это НЕ OnStepX — это простой jog по WiFi поверх рабочего кода на UART 21/22.
 * Полный OnStepX (SkySafari, GoTo, слежение) — отдельная боевая прошивка.
 *
 * Питание: стабильные 12 В в клеммник (иначе CH340/плата не поднимутся).
 * Моторы: X = азимут, Y = высота. Втыкать только при снятом 12 В!
 * Аппаратно ничего менять не надо — заводские синие джамперы (UART TMC на 21/22)
 * оставить на месте.
 *
 * Тулчейн: плата "ESP32 Dev Module", esp32 core 3.x ок, библиотека TMCStepper.
 * Заливка: arduino-cli ... --fqbn esp32:esp32:esp32:UploadSpeed=115200
 */
#include <WiFi.h>
#include <WebServer.h>
#include <TMCStepper.h>

// ---- пины E4 (Pins.FYSETC_E4) ----
#define EN_PIN   25       // общий ENABLE, активен НИЗким
#define X_STEP   27
#define X_DIR    26
#define Y_STEP   33
#define Y_DIR    32
#define TMC_RX   21       // UART драйверов (заводские синие джамперы)
#define TMC_TX   22

#define R_SENSE  0.11f
#define CURRENT  400      // ток RMS, мА (стендовый; без радиатора не задирать)
#define USTEPS   16
#define STEP_HALF_US 500  // полупериод шага, мкс (меньше = быстрее)
#define CHUNK    40       // шагов за проход loop (между обработкой веба)

const char* AP_SSID = "NewtonRocker";   // открытая сеть

HardwareSerial &tmc = Serial1;
TMC2209Stepper drv[4] = {
  TMC2209Stepper(&tmc, R_SENSE, 0), TMC2209Stepper(&tmc, R_SENSE, 1),
  TMC2209Stepper(&tmc, R_SENSE, 2), TMC2209Stepper(&tmc, R_SENSE, 3),
};
WebServer server(80);

volatile long xRem = 0, yRem = 0;   // осталось шагов
bool xDir = true, yDir = true;

void cfg(TMC2209Stepper &d){
  d.begin(); d.toff(4); d.rms_current(CURRENT); d.microsteps(USTEPS); d.pwm_autoscale(true);
}

const char PAGE[] PROGMEM = R"HTML(
<!doctype html><html><head><meta charset="utf-8"><meta name=viewport content="width=device-width,initial-scale=1">
<title>Newton Rocker</title><style>
body{font-family:sans-serif;text-align:center;background:#111;color:#eee;margin:0;padding:16px}
h2{margin:10px}
button{font-size:28px;margin:6px;padding:20px 30px;border:0;border-radius:14px;background:#2a7;color:#fff}
button.stop{background:#c33;width:92%;padding:22px}
select{font-size:20px;padding:8px;border-radius:8px}
.row{margin:12px}</style></head><body>
<h2>Newton Rocker - WiFi</h2>
<div class=row>step: <select id=n>
<option value=200>small (200)</option>
<option value=800 selected>1/4 turn (800)</option>
<option value=3200>1 turn (3200)</option>
<option value=32000>~10 turns</option></select></div>
<h2>Azimuth (X)</h2>
<div class=row><button onclick="m(0,0)">&#9664;</button><button onclick="m(0,1)">&#9654;</button></div>
<h2>Altitude (Y)</h2>
<div class=row><button onclick="m(1,1)">&#9650;</button><button onclick="m(1,0)">&#9660;</button></div>
<div class=row><button class=stop onclick="s()">STOP</button></div>
<script>
function m(a,d){let n=document.getElementById('n').value;fetch(`/move?ax=${a}&dir=${d}&n=${n}`)}
function s(){fetch('/stop')}
</script></body></html>
)HTML";

void handleRoot(){ server.send_P(200, "text/html", PAGE); }

void handleMove(){
  int ax = server.arg("ax").toInt();
  int dir = server.arg("dir").toInt();
  long n = server.arg("n").toInt();
  if (ax == 0) { xDir = dir; xRem = n; }
  else         { yDir = dir; yRem = n; }
  server.send(200, "text/plain", "ok");
}

void handleStop(){ xRem = 0; yRem = 0; server.send(200, "text/plain", "stop"); }

void stepChunk(int stepPin, int dirPin, bool dir, volatile long &rem){
  digitalWrite(dirPin, dir ? HIGH : LOW);
  long c = rem < CHUNK ? rem : CHUNK;
  for (long i = 0; i < c; i++){
    digitalWrite(stepPin, HIGH); delayMicroseconds(STEP_HALF_US);
    digitalWrite(stepPin, LOW);  delayMicroseconds(STEP_HALF_US);
  }
  rem -= c;
}

void setup(){
  Serial.begin(115200); delay(200);
  Serial.println("\nE4 WiFi jog");

  pinMode(EN_PIN, OUTPUT); digitalWrite(EN_PIN, HIGH);   // выкл, пока настраиваем ток
  pinMode(X_STEP, OUTPUT); pinMode(X_DIR, OUTPUT);
  pinMode(Y_STEP, OUTPUT); pinMode(Y_DIR, OUTPUT);

  tmc.begin(115200, SERIAL_8N1, TMC_RX, TMC_TX); delay(200);
  for (int i = 0; i < 4; i++) cfg(drv[i]);
  digitalWrite(EN_PIN, LOW);                              // драйверы вкл

  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID);
  Serial.print("AP: "); Serial.print(AP_SSID);
  Serial.print("  ->  http://"); Serial.println(WiFi.softAPIP());

  server.on("/", handleRoot);
  server.on("/move", handleMove);
  server.on("/stop", handleStop);
  server.begin();
  Serial.println("web up");
}

void loop(){
  server.handleClient();
  if (xRem > 0) stepChunk(X_STEP, X_DIR, xDir, xRem);
  if (yRem > 0) stepChunk(Y_STEP, Y_DIR, yDir, yRem);
}
