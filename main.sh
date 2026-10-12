#!/bin/sh

scripts_dir=$(CDPATH='' cd "$(dirname "$0")" && pwd)
pid_file="$scripts_dir/telegram_bot.pid"

RED=''
GREEN=''
YELLOW=''
BLUE=''
CYAN=''
RESET=''
if [ -t 1 ]; then
  RED=$(printf '\033[0;31m')
  GREEN=$(printf '\033[0;32m')
  YELLOW=$(printf '\033[0;33m')
  BLUE=$(printf '\033[0;34m')
  CYAN=$(printf '\033[0;36m')
  RESET=$(printf '\033[0m')
fi

print_message() {
  printf '%b\n' "$1"
}

read_pid() {
  [ -r "$pid_file" ] || return 1
  PID=''
  IFS= read -r PID < "$pid_file" || [ -n "${PID:-}" ]
  case "${PID:-}" in
    ''|*[!0-9]*) return 1 ;;
  esac
}

show_status() {
  if ! read_pid; then
    print_message "${RED}✿ No running twnesss found.${RESET}"
    return
  fi

  if kill -0 "$PID" 2>/dev/null && [ -r "/proc/$PID/status" ]; then
    rss=$(awk '/VmRSS/ { print $2; exit }' "/proc/$PID/status")
    swap=$(awk '/VmSwap/ { print $2; exit }' "/proc/$PID/status")
    state=$(awk '/State/ { print $2, $3; exit }' "/proc/$PID/status")
    running_time=$(ps -o etime= -p "$PID" 2>/dev/null | tr -d ' ')

    [ -n "$rss" ] || rss=0
    [ -n "$swap" ] || swap=0
    [ -n "$running_time" ] || running_time=unknown
    if [ "$rss" -ge 1024 ]; then
      bin_rss="$((rss / 1024)) MB"
    else
      bin_rss="$rss KB"
    fi
    if [ "$swap" -ge 1024 ]; then
      bin_swap="$((swap / 1024)) MB"
    else
      bin_swap="$swap KB"
    fi

    print_message "${GREEN}✿ twnesss bot Status:${RESET} ${CYAN}${state}${RESET} (PID: ${YELLOW}${PID}${RESET})"
    print_message "${GREEN}✿ twnesss memory Usage:${RESET} ${YELLOW}${bin_rss}${RESET}, ${GREEN}Swap:${RESET} ${YELLOW}${bin_swap}${RESET}"
    print_message "${GREEN}✿ twnesss running Time:${RESET} ${YELLOW}${running_time}${RESET}"
  else
    print_message "${RED}✿ Found stale twnesss PID file. Cleaning up...${RESET}"
    rm -f "$pid_file"
  fi
}

case "${1:-}" in
  r|start)
    if read_pid; then
      if kill -0 "$PID" 2>/dev/null; then
        print_message "${YELLOW}✿ twnesss is already running with PID:${RESET} $PID"
        exit 1
      fi
      print_message "${RED}✿ Found stale twnesss PID file. Cleaning up...${RESET}"
      rm -f "$pid_file"
    fi
    nohup python3 "$scripts_dir/main.py" >/dev/null 2>&1 &
    PID=$!
    printf '%s\n' "$PID" > "$pid_file"
    print_message "${GREEN}✿ twnesss started with PID:${RESET} $PID"
    ;;
  k|stop)
    if read_pid && kill -0 "$PID" 2>/dev/null; then
      kill "$PID"
      print_message "${RED}✿ twnesss stopped.${RESET}"
    else
      print_message "${YELLOW}✿ No active twnesss process found.${RESET}"
    fi
    rm -f "$pid_file"
    ;;
  l|restart)
    print_message "${BLUE}✿ Restarting twnesss...${RESET}"
    "$scripts_dir/main.sh" stop
    "$scripts_dir/main.sh" start
    ;;
  s|status)
    show_status
    ;;
  d|daemon)
    if ! read_pid || ! kill -0 "$PID" 2>/dev/null; then
      print_message "Bot is not active. Restarting..."
      "$scripts_dir/main.sh" restart
    fi
    ;;
  *)
    print_message "${YELLOW}Usage:${RESET} $0 {start|stop|restart|status|daemon}"
    exit 1
    ;;
esac
