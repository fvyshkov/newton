/*
 * encoder_calib — веб-центровка магнита над AS5048A (азимут az2).
 *
 * Железо: ESP32 DevKitC (CP2102) + плата AS5048A по SPI:
 *   VDD->3V3 (НЕ 5V!)  GND->GND  CLK->18  DO/MISO->19  DI/MOSI->23  CS->4
 *   Питание у монтировки — пауэрбанк в micro-USB.
 *
 * WiFi: дома STA http://10.0.0.231 (+ своя AP "EncoderCalib" 192.168.4.1),
 * OTA-прошивка: arduino-cli upload -p 10.0.0.231 --fqbn esp32:esp32:esp32 .
 *
 * ПРОЦЕДУРА ЦЕНТРОВКИ (плата чипа НЕ затянута, магнит в кармане спайдера):
 *   1. Открыть http://10.0.0.231 (телефон/мак).
 *   2. Нажать «Заново», МЕДЛЕННО провернуть азимут на ПОЛНЫЙ оборот (5–15 с).
 *      Страница копит поле по 36 секторам угла; когда покрыт весь круг —
 *      вердикт большими буквами (он не мигает и не уплывает).
 *   3. ❌ → чуть сдвинуть плату чипа вбок, «Заново», ещё оборот. Разброс поля
 *      падает → двигаешь в правильную сторону.
 *   4. ✅ УДОВЛЕТВОРИТЕЛЬНО (разброс ≤4% ≈ магнит в ~0.25 мм от оси, AGC в
 *      норме весь оборот, ошибок чипа нет) → затягивать винты и переставать
 *      дышать на неё. После затяжки — контрольный оборот.
 *
 * Что значат числа:
 *   MAG (сила поля): гуляет за оборот → магнит не по оси. Разброс = главный
 *     показатель центровки.  AGC: усиление чипа. 40..200 хорошо; >=250 магнит
 *     далеко/слабый (зазор!), <=8 слишком близко.  COF: ошибки CORDIC — 0.
 */
#include <SPI.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <ArduinoOTA.h>

#if __has_include("wifi_creds.h")
#include "wifi_creds.h"
#endif

// ---- SPI AS5048A (пины 1:1 из проверенного ~/esp32_encoder_test) ----
static const int PIN_SCK = 18, PIN_MISO = 19, PIN_MOSI = 23, PIN_CS = 4;
SPIClass spi(VSPI);
SPISettings spiSettings(1000000, MSBFIRST, SPI_MODE1);
static const uint16_t CMD_ANGLE = 0xFFFF, CMD_MAG = 0x7FFE, CMD_DIAG = 0x7FFD,
                      CMD_NOP = 0x0000;

// ---- пороги «удовлетворительно» ----
#define SPREAD_OK   4.0f    // % разброса MAG за оборот: ≤ → центровано (~0.25мм)
#define SPREAD_MEH  8.0f    // ≤ → почти, ещё чуть-чуть
#define AGC_LO      40
#define AGC_HI      200
#define BINS        36      // секторов угла на оборот
#define BINS_NEED   34      // сколько должно быть покрыто для вердикта

const char* AP_SSID = "EncoderCalib";
WebServer server(80);

// накопители с последнего «Заново»
uint32_t binSum[BINS]; uint32_t agcSum[BINS]; uint16_t binCnt[BINS];
uint32_t cofCnt = 0, errCnt = 0;
// живые значения
float curDeg = 0; uint16_t curMag = 0; uint8_t curAgc = 0;

uint16_t xfer(uint16_t v){
  digitalWrite(PIN_CS, LOW);
  uint16_t r = spi.transfer16(v);
  digitalWrite(PIN_CS, HIGH);
  return r;
}
uint16_t readReg(uint16_t cmd){        // ответ приходит СЛЕДУЮЩИМ фреймом
  xfer(cmd); delayMicroseconds(2); return xfer(CMD_NOP);
}

void resetAcc(){
  memset(binSum, 0, sizeof(binSum)); memset(agcSum, 0, sizeof(agcSum));
  memset(binCnt, 0, sizeof(binCnt));
  cofCnt = 0; errCnt = 0;
}

void sample(){
  uint16_t a = readReg(CMD_ANGLE), m = readReg(CMD_MAG), d = readReg(CMD_DIAG);
  if ((a | m | d) & 0x4000){                        // EF: сбойный кадр SPI —
    errCnt++; readReg(0x4001);                      // сбросить Clear Error Flag
    return;                                         // и сэмпл выбросить
  }
  curDeg = (a & 0x3FFF) * 360.0f / 16384.0f;
  curMag = m & 0x3FFF;
  curAgc = d & 0x00FF;
  if (d & (1 << 9)) cofCnt++;                       // COF: ошибка CORDIC
  int b = (int)(curDeg / (360.0f / BINS)); if (b >= BINS) b = BINS - 1;
  binSum[b] += curMag; agcSum[b] += curAgc; binCnt[b]++;
}

// вердикт по накопленному; всё по СРЕДНИМ в корзинах угла (глюки одиночных
// SPI-чтений усредняются и не портят min/max)
void verdict(float &spreadPct, int &covered, float &magMean,
             float &agcLo, float &agcHi, char *text, char *color){
  covered = 0;
  float mn = 1e9, mx = -1e9, sum = 0;
  agcLo = 255; agcHi = 0;
  for (int i = 0; i < BINS; i++){
    if (!binCnt[i]) continue;
    covered++;
    float v = (float)binSum[i] / binCnt[i];
    if (v < mn) mn = v;
    if (v > mx) mx = v;
    sum += v;
    float av = (float)agcSum[i] / binCnt[i];
    if (av < agcLo) agcLo = av;
    if (av > agcHi) agcHi = av;
  }
  magMean = covered ? sum / covered : 0;
  spreadPct = (covered && sum > 0) ? 100.0f * (mx - mn) / magMean : 0;
  if (covered < BINS_NEED){
    sprintf(text, "КРУТИ ОБОРОТ — покрыто %d%%", covered * 100 / BINS);
    strcpy(color, "#666"); return;
  }
  if (agcHi >= 250){ strcpy(text, "МАГНИТ ДАЛЕКО/СЛАБЫЙ — уменьшить зазор"); strcpy(color, "#c33"); return; }
  if (agcLo <= 5)  { strcpy(text, "МАГНИТ СЛИШКОМ БЛИЗКО — увеличить зазор"); strcpy(color, "#c33"); return; }
  if (cofCnt)       { sprintf(text, "ОШИБКИ ЧИПА (COF×%lu) — проверь зазор/провода", (unsigned long)cofCnt); strcpy(color, "#c33"); return; }
  if (spreadPct <= SPREAD_OK){
    sprintf(text, "УДОВЛЕТВОРИТЕЛЬНО ✓ разброс %.1f%% — можно затягивать", spreadPct);
    strcpy(color, "#2a7"); return;
  }
  if (spreadPct <= SPREAD_MEH){
    sprintf(text, "ПОЧТИ: разброс %.1f%% (цель ≤%.0f%%) — чуть сдвинь и заново", spreadPct, SPREAD_OK);
    strcpy(color, "#b80"); return;
  }
  sprintf(text, "МИМО ОСИ: разброс %.1f%% — сдвигай плату, заново, смотри меньше ли", spreadPct);
  strcpy(color, "#c33");
}

const char PAGE[] PROGMEM = R"HTML(
<!doctype html><html><head><meta charset="utf-8"><meta name=viewport content="width=device-width,initial-scale=1">
<title>Центровка энкодера</title><style>
body{font-family:sans-serif;text-align:center;background:#111;color:#eee;margin:0;padding:14px}
#v{font-size:22px;font-weight:bold;padding:18px 10px;border-radius:14px;background:#666;margin:10px 0}
.big{font-size:44px;font-weight:bold}
.lbl{color:#999;font-size:14px}
.grid{display:flex;justify-content:space-around;margin:12px 0}
button{font-size:22px;margin:6px;padding:14px 26px;border:0;border-radius:14px;background:#36c;color:#fff}
button.go{background:#2a7}
button.stop{background:#c33}
#bins{letter-spacing:1px;font-size:13px;word-break:break-all}
.hint{color:#888;font-size:13px;margin:8px}</style></head><body>
<div id=v>...</div>
<div class=grid>
<div><div class=big id=deg>—</div><div class=lbl>угол °</div></div>
<div><div class=big id=mag>—</div><div class=lbl>MAG поле</div></div>
<div><div class=big id=agc>—</div><div class=lbl>AGC (40..200 ок)</div></div>
</div>
<div class=lbl>разброс поля за оборот (цель ≤4%): <b id=sp>—</b> &nbsp;|&nbsp; средний MAG (максимизировать спайдером): <b id=mm>—</b> &nbsp;|&nbsp; AGC за оборот: <b id=ar>—</b></div>
<div id=bins class=lbl></div>
<div>
<button onclick="fetch('/reset')">ЗАНОВО (после сдвига)</button>
<button class=go onclick="spin()">ОБОРОТ МОТОРОМ</button>
<button class=stop onclick="mstop()">СТОП МОТОР</button>
</div>
<div class=hint>Порядок: ЗАНОВО → ОБОРОТ. Застряло — подтолкни рукой или жми ОБОРОТ ещё раз:
замер копится по углу, сбои кручения ему не вредят.</div>
<script>
const E4='http://10.0.0.230';
function spin(){fetch(`${E4}/go?ax=0&deg=370`).catch(e=>{})}
function mstop(){fetch(`${E4}/stop`).catch(e=>{})}
setInterval(async()=>{try{
 let d=await(await fetch('/data')).json();
 deg.textContent=d.deg.toFixed(1); mag.textContent=d.mag; agc.textContent=d.agc;
 sp.textContent=d.spread.toFixed(1)+'%'; mm.textContent=d.magMean; ar.textContent=d.agcMin+'..'+d.agcMax;
 v.textContent=d.text; v.style.background=d.color;
 bins.textContent=d.bins;
}catch(e){v.textContent='нет связи с платой';v.style.background='#666'}},250);
</script></body></html>
)HTML";

void handleRoot(){ server.send_P(200, "text/html", PAGE); }

void handleData(){
  float sp, mm, alo, ahi; int cov; char text[120], color[8];
  verdict(sp, cov, mm, alo, ahi, text, color);
  char bins[BINS + 1];
  for (int i = 0; i < BINS; i++) bins[i] = binCnt[i] ? '#' : '.';
  bins[BINS] = 0;
  char buf[460];
  snprintf(buf, sizeof(buf),
    "{\"deg\":%.2f,\"mag\":%u,\"agc\":%u,\"spread\":%.2f,\"cover\":%d,\"magMean\":%.0f,"
    "\"agcMin\":%.0f,\"agcMax\":%.0f,\"cof\":%lu,\"err\":%lu,\"text\":\"%s\",\"color\":\"%s\",\"bins\":\"%s\"}",
    curDeg, curMag, curAgc, sp, cov, mm, alo, ahi,
    (unsigned long)cofCnt, (unsigned long)errCnt, text, color, bins);
  server.send(200, "application/json", buf);
}

void handleReset(){ resetAcc(); server.send(200, "text/plain", "ok"); }

void setup(){
  Serial.begin(115200); delay(200);
  Serial.println("\nencoder_calib");
  pinMode(PIN_CS, OUTPUT); digitalWrite(PIN_CS, HIGH);
  spi.begin(PIN_SCK, PIN_MISO, PIN_MOSI, PIN_CS);
  spi.beginTransaction(spiSettings);
  resetAcc();

  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP(AP_SSID);
#ifdef HOME_SSID
  WiFi.setHostname("encoder");
#ifdef HOME_STATIC_IP
  WiFi.config(IPAddress(HOME_STATIC_IP), IPAddress(HOME_GATEWAY),
              IPAddress(255, 255, 255, 0), IPAddress(HOME_GATEWAY));
#endif
  WiFi.begin(HOME_SSID, HOME_PASS);
  for (int i = 0; i < 30 && WiFi.status() != WL_CONNECTED; i++){ delay(500); Serial.print("."); }
  Serial.print("\nSTA: http://"); Serial.println(WiFi.localIP());
#endif
  if (MDNS.begin("encoder")) MDNS.addService("http", "tcp", 80);

  server.on("/", handleRoot);
  server.on("/data", handleData);
  server.on("/reset", handleReset);
  server.begin();

  ArduinoOTA.setHostname("encoder");
  ArduinoOTA.begin();
  Serial.println("web up");
}

uint32_t lastSample = 0;

void loop(){
  server.handleClient();
  ArduinoOTA.handle();
  if (millis() - lastSample >= 50){ lastSample = millis(); sample(); }
}
