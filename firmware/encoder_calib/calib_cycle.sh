#!/bin/bash
# Один цикл центровки: сброс → оборот мотором → ждать покрытия круга → вердикт.
# УСТОЙЧИВ К ЗАСТРЕВАНИЯМ: если покрытие замерло —
#   мотор дошёл, а круг не покрыт (проскользнуло)  → докрутка ещё на 120°;
#   мотор шагает, а угол стоит (ротор застрял)      → стоп + перезапуск с разгоном.
# После 3 перезапусков подряд просит подтолкнуть рукой (замер при этом не портится:
# данные копятся по углу, продолжаем с того же места).
#   ./calib_cycle.sh            # полный цикл с мотором
#   ./calib_cycle.sh --no-spin  # без мотора (крутят рукой)
ENC="${ENC:-10.0.0.231}"
E4="${E4:-10.0.0.230}"
DEG="${DEG:-370}"
TIMEOUT="${TIMEOUT:-300}"
SPIN=1; [ "$1" = "--no-spin" ] && SPIN=0

jget(){ echo "$1" | sed "s/.*\"$2\":\([0-9.-]*\).*/\1/"; }

curl -fsS --max-time 4 "http://$ENC/reset" >/dev/null || { echo "энкодер не отвечает"; exit 1; }
if [ $SPIN = 1 ]; then
  curl -fsS --max-time 4 "http://$E4/go?ax=0&deg=$DEG" && echo || { echo "E4 не отвечает"; exit 1; }
fi

t0=$(date +%s); prev_cov=-1; stale=0; restarts=0
while :; do
  sleep 4
  D=$(curl -fsS --max-time 4 "http://$ENC/data") || { echo "потерял энкодер"; exit 1; }
  COV=$(jget "$D" cover); SPREAD=$(jget "$D" spread)
  XREM=0
  [ $SPIN = 1 ] && XREM=$(jget "$(curl -fsS --max-time 4 "http://$E4/status")" xRem)
  echo "  покрыто $COV/36, разброс $SPREAD%, мотору осталось $XREM шагов"
  if [ "$COV" -ge 34 ]; then
    [ $SPIN = 1 ] && { curl -fsS "http://$E4/stop" >/dev/null
                       curl -fsS "http://$E4/current?ma=900" >/dev/null; }  # ток в норму
    break
  fi
  if [ "$COV" -gt "$prev_cov" ]; then
    prev_cov=$COV; stale=0
    if [ $SPIN = 1 ] && [ "$XREM" -eq 0 ]; then
      # пошло (рукой или само), но мотор без команды — докручиваем сразу
      echo "  ⟳ движение есть, мотор простаивает — докрутка 120°"
      curl -fsS --max-time 4 "http://$E4/go?ax=0&deg=120" >/dev/null
    fi
  else
    stale=$((stale+1))
    if [ $SPIN = 1 ]; then
      if [ "$XREM" -eq 0 ] && [ $stale -ge 1 ]; then
        echo "  ⟳ мотор дошёл, круг не покрыт — докрутка 120°"
        curl -fsS --max-time 4 "http://$E4/go?ax=0&deg=120" >/dev/null
        stale=0
      elif [ "$XREM" -gt 0 ] && [ $stale -ge 3 ]; then
        restarts=$((restarts+1))
        BOOST=$(( 900 + restarts*150 )); [ $BOOST -gt 1300 ] && BOOST=1300
        echo "  ⟳ ротор застрял — ток $BOOST мА + перезапуск с разгоном ($restarts)"
        curl -fsS --max-time 4 "http://$E4/stop" >/dev/null; sleep 1
        curl -fsS --max-time 4 "http://$E4/current?ma=$BOOST" >/dev/null
        curl -fsS --max-time 4 "http://$E4/go?ax=0&deg=120" >/dev/null
        [ $restarts -ge 3 ] && echo "  ✋✋✋ ЗАСТРЯЛО НАМЕРТВО — УСТРАНИ (подтолкни/проверь зацепление)." \
          && echo "      Замер не портится; как пойдёт — докручу сам."
        stale=0
      fi
    fi
  fi
  [ $(( $(date +%s) - t0 )) -gt $TIMEOUT ] && { echo "ТАЙМАУТ"; echo "$D"; exit 2; }
done
echo "----"
echo "$D"
echo "ВЕРДИКТ: $(echo "$D" | sed 's/.*"text":"\([^"]*\)".*/\1/')"
