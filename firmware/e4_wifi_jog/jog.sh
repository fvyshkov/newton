#!/bin/bash
# Джог моторов рокера с мака (плата на домашнем WiFi, прошивка e4_wifi_jog).
#   ./jog.sh azdeg +5.5   # азимут: 5.5° ВЕНЦА вправо (привод 14:1)
#   ./jog.sh altdeg -30   # высота: 30° вала вниз (привода пока нет)
#   ./jog.sh az +800      # то же в шагах (3200 = оборот вала)
#   ./jog.sh stop         # стоп оба
#   ./jog.sh status       # что осталось докрутить + IP/RSSI
# Хост можно переопределить: NEWTON=192.168.1.42 ./jog.sh azdeg +5
HOST="${NEWTON:-10.0.0.230}"
case "$1" in
  azdeg|altdeg)
    AX=0; [ "$1" = altdeg ] && AX=1
    D="${2#+}"
    [ -n "$D" ] || { echo "нужны градусы, напр.: $0 $1 +5.5"; exit 1; }
    curl -fsS --max-time 5 "http://$HOST/go?ax=$AX&deg=$D" && echo
    ;;
  az|alt)
    AX=0; [ "$1" = alt ] && AX=1
    N="$2"
    case "$N" in
      +*) DIR=1; N="${N#+}" ;;
      -*) DIR=0; N="${N#-}" ;;
      *)  DIR=1 ;;
    esac
    [ -n "$N" ] || { echo "нужно число шагов, напр.: $0 $1 +800"; exit 1; }
    curl -fsS --max-time 5 "http://$HOST/move?ax=$AX&dir=$DIR&n=$N" && echo
    ;;
  stop)   curl -fsS --max-time 5 "http://$HOST/stop" && echo ;;
  status) curl -fsS --max-time 5 "http://$HOST/status" && echo ;;
  *) sed -n '2,9p' "$0"; exit 1 ;;
esac
