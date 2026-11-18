/*
 * e4_wifi_jog — управление моторами рокера по WiFi (FYSETC E4).
 *
 * Два режима СРАЗУ (AP+STA):
 *   1) ДОМА: подключается к домашнему WiFi (креды в wifi_creds.h — НЕ в гите),
 *      доступна как http://newton.local (mDNS) со всех устройств сети,
 *      включая curl с мака (см. jog.sh).
 *   2) В ПОЛЕ (роутера нет): своя точка "NewtonRocker" (открытая),
 *      с телефона http://192.168.4.1 — как раньше.
 *
 * HTTP API: /move?ax=0|1&dir=0|1&n=шаги   /stop   /status (JSON)
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
#include <ESPmDNS.h>
#include <ArduinoOTA.h>
#include <TMCStepper.h>

#if __has_include("wifi_creds.h")
#include "wifi_creds.h"          // #define HOME_SSID "..." / HOME_PASS "..."
#endif

// ---- пины E4 (Pins.FYSETC_E4) ----
#define EN_PIN   25       // общий ENABLE, активен НИЗким
#define X_STEP   27
#define X_DIR    26
#define Y_STEP   33
#define Y_DIR    32
#define TMC_RX   21       // UART драйверов (заводские синие джамперы)
#define TMC_TX   22

#define R_SENSE  0.11f
#define CURRENT  900      // ток RMS, мА (мотор 2А; 0.9А ок для джога без радиатора,
                          // непрерывно минутами не гонять — чипы на плате греются)
#define USTEPS   16
#define STEP_HALF_US 500  // полупериод шага на полной скорости, мкс
#define RAMP_STEPS 300    // разгон: столько шагов от старта до полной скорости
#define RAMP_EXTRA 600    // добавка к полупериоду на старте, мкс (старт ~45% скорости)
#define CHUNK    40       // шагов за проход loop (между обработкой веба)

// ---- градусы → шаги ----
// вал мотора: 200 полных шагов × USTEPS = 3200 µшагов/оборот
// азимут: прямой привод az2 — пинион 16T в венец 224T = 14:1
#define AZ_STEPS_PER_DEG  (3200.0 * 14.0 / 360.0)   // 124.44 µшага на градус ВЕНЦА
// высота: привода пока нет — градусы ВАЛА мотора; поменять при сборке качалки
#define ALT_STEPS_PER_DEG (3200.0 / 360.0)          // 8.89

const char* AP_SSID = "NewtonRocker";   // открытая сеть

HardwareSerial &tmc = Serial1;
TMC2209Stepper drv[4] = {
  TMC2209Stepper(&tmc, R_SENSE, 0), TMC2209Stepper(&tmc, R_SENSE, 1),
  TMC2209Stepper(&tmc, R_SENSE, 2), TMC2209Stepper(&tmc, R_SENSE, 3),
};
WebServer server(80);

volatile long xRem = 0, yRem = 0;   // осталось шагов
volatile long xDone = 0, yDone = 0; // сделано с начала команды (для разгона)
bool xDir = true, yDir = true;
uint32_t idleSince = 0;             // отключаем ток удержания при простое
bool enOn = true;                   // (стоя 900мА только греет и гудит)

void cfg(TMC2209Stepper &d){
  d.begin(); d.toff(4); d.rms_current(CURRENT); d.microsteps(USTEPS); d.pwm_autoscale(true);
  d.en_spreadCycle(true);   // момент важнее тишины: stealthChop срывается на рывках
}

const char PAGE[] PROGMEM = R"HTML(
<!doctype html><html><head><meta charset="utf-8"><meta name=viewport content="width=device-width,initial-scale=1">
<title>Newton Rocker</title><style>
body{font-family:sans-serif;text-align:center;background:#111;color:#eee;margin:0;padding:16px}
h2{margin:10px}
button{font-size:28px;margin:6px;padding:20px 30px;border:0;border-radius:14px;background:#2a7;color:#fff}
button.stop{background:#c33;width:92%;padding:22px}
button.pre{font-size:18px;padding:10px 14px;background:#345}
input{font-size:26px;width:120px;padding:8px;border-radius:8px;border:0;text-align:center}
.row{margin:12px}</style></head><body>
<h2>Newton Rocker - WiFi</h2>
<div class=row><input id=deg type=number step=0.1 min=0 value=30> &deg;</div>
<div class=row>
<button class=pre onclick="p(0.5)">0.5&deg;</button><button class=pre onclick="p(2)">2&deg;</button>
<button class=pre onclick="p(10)">10&deg;</button><button class=pre onclick="p(30)">30&deg;</button>
<button class=pre onclick="p(90)">90&deg;</button></div>
<h2>Azimuth (14:1)</h2>
<div class=row><button onclick="g(0,-1)">&#9664;</button><button onclick="g(0,1)">&#9654;</button></div>
<h2>Altitude (вал)</h2>
<div class=row><button onclick="g(1,1)">&#9650;</button><button onclick="g(1,-1)">&#9660;</button></div>
<div class=row><button class=stop onclick="s()">STOP</button></div>
<script>
function p(v){document.getElementById('deg').value=v}
function g(a,sg){let d=parseFloat(document.getElementById('deg').value)||0;fetch(`/go?ax=${a}&deg=${sg*d}`)}
function s(){fetch('/stop')}
</script></body></html>
)HTML";

void handleRoot(){ server.send_P(200, "text/html", PAGE); }

void handleMove(){
  int ax = server.arg("ax").toInt();
  int dir = server.arg("dir").toInt();
  long n = server.arg("n").toInt();
  if (ax == 0) { xDir = dir; xRem = n; xDone = 0; }
  else         { yDir = dir; yRem = n; yDone = 0; }
  server.send(200, "text/plain", "ok");
}

void handleStop(){ xRem = 0; yRem = 0; server.send(200, "text/plain", "stop"); }

void handleGo(){                       // /go?ax=0|1&deg=±градусы (дробные ок)
  int ax = server.arg("ax").toInt();
  float deg = server.arg("deg").toFloat();
  long n = lroundf(fabsf(deg) * (ax == 0 ? AZ_STEPS_PER_DEG : ALT_STEPS_PER_DEG));
  if (ax == 0) { xDir = deg >= 0; xRem = n; xDone = 0; }
  else         { yDir = deg >= 0; yRem = n; yDone = 0; }
  char buf[64];
  snprintf(buf, sizeof(buf), "ok %.1fdeg = %ld steps", deg, n);
  server.send(200, "text/plain", buf);
}

void handleCurrent(){                  // /current?ma=300..1300 — ток RMS на лету
  int ma = server.arg("ma").toInt();
  if (ma < 300) ma = 300;
  if (ma > 1300) ma = 1300;            // >1.3А без радиатора нельзя
  for (int i = 0; i < 4; i++) drv[i].rms_current(ma);
  char buf[32];
  snprintf(buf, sizeof(buf), "ok %d mA", ma);
  server.send(200, "text/plain", buf);
}

void handleStatus(){
  char buf[160];
  snprintf(buf, sizeof(buf),
           "{\"xRem\":%ld,\"yRem\":%ld,\"sta_ip\":\"%s\",\"rssi\":%d}",
           xRem, yRem, WiFi.localIP().toString().c_str(), WiFi.RSSI());
  server.send(200, "application/json", buf);
}

void stepChunk(int stepPin, int dirPin, bool dir, volatile long &rem, volatile long &done){
  digitalWrite(dirPin, dir ? HIGH : LOW);
  long c = rem < CHUNK ? rem : CHUNK;
  for (long i = 0; i < c; i++){
    // линейный разгон: первые RAMP_STEPS шагов от старта — медленнее
    long ramp = RAMP_STEPS - done;
    long half = STEP_HALF_US + (ramp > 0 ? RAMP_EXTRA * ramp / RAMP_STEPS : 0);
    digitalWrite(stepPin, HIGH); delayMicroseconds(half);
    digitalWrite(stepPin, LOW);  delayMicroseconds(half);
    done++;
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

  WiFi.mode(WIFI_AP_STA);                                 // своя AP + клиент дома
  WiFi.softAP(AP_SSID);
  Serial.print("AP: "); Serial.print(AP_SSID);
  Serial.print("  ->  http://"); Serial.println(WiFi.softAPIP());
#ifdef HOME_SSID
  WiFi.setHostname("newton");
#ifdef HOME_STATIC_IP
  WiFi.config(IPAddress(HOME_STATIC_IP), IPAddress(HOME_GATEWAY),
              IPAddress(255, 255, 255, 0), IPAddress(HOME_GATEWAY));
#endif
  WiFi.begin(HOME_SSID, HOME_PASS);
  Serial.print("STA: connecting to "); Serial.print(HOME_SSID);
  for (int i = 0; i < 30 && WiFi.status() != WL_CONNECTED; i++){
    delay(500); Serial.print(".");
  }
  if (WiFi.status() == WL_CONNECTED){
    Serial.print("\nSTA: http://"); Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nSTA: не подключилась (работает только AP)");
  }
#endif
  if (MDNS.begin("newton")) {                             // http://newton.local
    MDNS.addService("http", "tcp", 80);
    Serial.println("mDNS: http://newton.local");
  }

  server.on("/", handleRoot);
  server.on("/move", handleMove);
  server.on("/go", handleGo);
  server.on("/stop", handleStop);
  server.on("/current", handleCurrent);
  server.on("/status", handleStatus);
  server.enableCORS(true);   // страница центровки (10.0.0.231) командует мотором
  server.begin();
  Serial.println("web up");

  // прошивка по WiFi, USB-кабель больше не нужен:
  //   arduino-cli upload -p 10.0.0.230 --fqbn esp32:esp32:esp32 .
  ArduinoOTA.setHostname("newton");
  ArduinoOTA.onStart([](){ xRem = yRem = 0; digitalWrite(EN_PIN, HIGH); });  // моторы стоп
  ArduinoOTA.begin();
}

void loop(){
  server.handleClient();
  ArduinoOTA.handle();
  bool busy = (xRem > 0) || (yRem > 0);
  if (busy){
    if (!enOn){ digitalWrite(EN_PIN, LOW); enOn = true; delayMicroseconds(200); }
    idleSince = millis();
  } else if (enOn && millis() - idleSince > 3000){
    digitalWrite(EN_PIN, HIGH); enOn = false;      // стоим — ток удержания долой
  }
  if (xRem > 0) stepChunk(X_STEP, X_DIR, xDir, xRem, xDone);
  if (yRem > 0) stepChunk(Y_STEP, Y_DIR, yDir, yRem, yDone);
}
