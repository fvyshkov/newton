#!/bin/bash
# Прошивка ESP32 по WiFi (OTA), без кабеля.
#   ./ota_flash.sh e4_wifi_jog            # E4 (10.0.0.230)
#   ./ota_flash.sh encoder_calib          # энкодерный ESP32 (10.0.0.231)
#   ./ota_flash.sh <дир> <ip>             # явно
# ВАЖНО: arduino-cli upload по сети не работает неинтерактивно (просит пароль) —
# поэтому espota.py напрямую. Первая прошивка новой платы — всегда по проводу.
set -e
cd "$(dirname "$0")/$1"
case "$1" in
  e4_wifi_jog)   IP="${2:-10.0.0.230}" ;;
  encoder_calib) IP="${2:-10.0.0.231}" ;;
  *)             IP="$2"; [ -n "$IP" ] || { echo "укажи IP: $0 <дир> <ip>"; exit 1; } ;;
esac
arduino-cli compile --fqbn esp32:esp32:esp32 --export-binaries . | tail -1
BIN="build/esp32.esp32.esp32/$1.ino.bin"
ESPOTA=$(ls ~/Library/Arduino15/packages/esp32/hardware/esp32/*/tools/espota.py | head -1)
/opt/homebrew/bin/python3 "$ESPOTA" -i "$IP" -p 3232 -f "$BIN"
echo "OK → $IP перезагружается (~10 c)"
