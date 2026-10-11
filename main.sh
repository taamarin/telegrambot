#!/bin/sh

# Warna ANSI
if [[ -t 1 ]]; then
  RED='\033[0;31m'
  GREEN='\033[0;32m'
  YELLOW='\033[0;33m'
  BLUE='\033[0;34m'
  CYAN='\033[0;36m'
  RESET='\033[0m'
else
  RED=''
  GREEN=''
  YELLOW=''
  BLUE=''
  CYAN=''
  RESET=''
fi

scripts_dir="${0%/*}"

PYs() {
  PID=$(cat $scripts_dir/telegram_bot.pid)
  if [ -e /proc/$PID ]; then
    rss=$(grep VmRSS /proc/$PID/status | awk '{ print $2 }')
    [ "${rss}" -ge 1024 ] && bin_rss="$(expr ${rss} / 1024) MB" || bin_rss="${rss} KB"
    swap=$(grep VmSwap /proc/$PID/status | awk '{ print $2 }')
    [ "${swap}" -ge 1024 ] && bin_swap="$(expr ${swap} / 1024) MB" || bin_swap="${swap} KB"

    state=$(grep State /proc/$PID/status | awk '{ print $2" "$3 }')
    running_time=$(/root/clash/bin/busybox ps -o pid,comm,etime | awk -v pid="$PID" '$1 == pid {print $3}')

    echo -e "${GREEN}✿ twnesss bot Status:${RESET} ${CYAN}${state}${RESET} (PID: ${YELLOW}$PID${RESET})"
    echo -e "${GREEN}✿ twnesss memory Usage:${RESET} ${YELLOW}${bin_rss}${RESET}, ${GREEN}Swap:${RESET} ${YELLOW}${bin_swap}${RESET}"
    echo -e "${GREEN}✿ twnesss running Time:${RESET} ${YELLOW}${running_time}${RESET}"
  else
    echo -e "${RED}✿ twnesss No active process with PID:${RESET} $PID"
  fi
}

case "$1" in
  r|start)
    chmod +x /root/telegram/main.py
    if [ -f $scripts_dir/telegram_bot.pid ]; then
      PID=$(cat $scripts_dir/telegram_bot.pid)
      if [ -e /proc/$PID ]; then
        echo -e "${YELLOW}✿ twnesss is already running with PID:${RESET} $PID"
        exit 1
      else
        echo -e "${RED}✿ Found stale twnesss PID file. Cleaning up...${RESET}"
        rm -f $scripts_dir/telegram_bot.pid
      fi
    fi
    # if ping -c 3 -W 2 api.telegram.org >/dev/null 2>&1; then
        nohup python3 "$scripts_dir/main.py" >/dev/null 2>&1 &
        pid=$!
        echo "$pid" > "$scripts_dir/telegram_bot.pid"
        echo -e "${GREEN}✿ twnesss started with PID:${RESET} $pid"
    # else
        # echo -e "${RED}✖ Failed to reach api.telegram.org. Bot not started.${RESET}"
    # fi
    # nohup python3 $scripts_dir/main.py >/dev/null 2>&1 &
    # echo $! > $scripts_dir/telegram_bot.pid
    # echo -e "${GREEN}✿ twnesss started with PID:${RESET} $(cat $scripts_dir/telegram_bot.pid)"
    ;;
  k|stop)
    if [ -f $scripts_dir/telegram_bot.pid ]; then
      PID=$(cat $scripts_dir/telegram_bot.pid)
      if [ -e /proc/$PID ]; then
        kill -9 $PID
        echo -e "${RED}✿ twnesss stopped.${RESET}"
      else
        echo -e "${YELLOW}✿ No active process found with twnesss PID:${RESET} $PID. Cleaning up stale PID file..."
      fi
      rm -f $scripts_dir/telegram_bot.pid
    else
      echo -e "${RED}✿ No running twnesss found.${RESET}"
    fi
    ;;
  l|restart)
    echo -e "${BLUE}✿ Restarting twnesss...${RESET}"
    $0 stop
    $0 start
    ;;
  s|status)
    if [ -f $scripts_dir/telegram_bot.pid ]; then
      PYs
    else
      echo -e "${RED}✿ No running twnesss found.${RESET}"
    fi
    ;;
  d|daemon)
    pid_file="$scripts_dir/telegram_bot.pid"
    # Cek apakah file PID ada
    if [ -f "$pid_file" ]; then
        PID=$(cat "$pid_file")
        # Cek apakah proses dengan PID itu masih hidup
        if kill -0 "$PID" 2>/dev/null; then
            true
        else
            echo "User bot tidak aktif. Melakukan restart..."
            /root/telegram/main.sh l
        fi
    else
        echo "File PID tidak ditemukan. Melakukan restart..."
        /root/telegram/main.sh l
    fi
    ;;
  *)
    echo -e "${YELLOW}Usage:${RESET} $0 {start|stop|restart|status}"
    exit 1
    ;;
esac