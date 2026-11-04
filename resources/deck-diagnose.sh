#!/usr/bin/env bash
# Deck Agent 一键诊断（只读，不修改系统，不输出密钥）。
#
# 在 Steam Deck 上执行：
#   bash ~/homebrew/plugins/deck-agent/resources/deck-diagnose.sh
#
# 可用环境变量覆盖路径：
#   DECK_AGENT_PLUGIN  插件目录
#   DECK_AGENT_LOG_DIR 日志目录
#   DECK_AGENT_LINES   日志尾部行数（默认 40）
set -u

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if [ -n "${DECK_AGENT_PLUGIN:-}" ]; then
  PLUGIN_DIR="$DECK_AGENT_PLUGIN"
elif [ -f "$SCRIPT_DIR/../plugin.json" ] && [ -d "$SCRIPT_DIR/../runtime" ]; then
  PLUGIN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
else
  PLUGIN_DIR="${HOME:-/home/deck}/homebrew/plugins/deck-agent"
fi
HOME_DIR="${HOME:-/home/deck}"
LOG_DIR="${DECK_AGENT_LOG_DIR:-$HOME_DIR/homebrew/logs/deck-agent}"
SETTINGS_DIR="$HOME_DIR/homebrew/settings/deck-agent"
DATA_DIR="$HOME_DIR/homebrew/data/deck-agent"
LINES="${DECK_AGENT_LINES:-40}"
STATUS=0

have() { command -v "$1" >/dev/null 2>&1; }
run_limited() { seconds="$1"; shift; if have timeout; then timeout "$seconds" "$@"; else "$@"; fi; }
section() { printf '\n== %s ==\n' "$1"; }
warn() { printf '! %s\n' "$1"; STATUS=1; }
value_of() {
  grep -o "\"$1\": *\"[^\"]*\"" "$2" 2>/dev/null | head -n 1 | sed 's/.*: *"//; s/"$//'
}

case "${1:-}" in
  -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
esac

section "设备"
date -Is 2>/dev/null || date
printf '主机：%s\n内核：%s\n' "$(hostname 2>/dev/null || echo 未知)" "$(uname -sr)"
if [ -r /etc/os-release ]; then grep -E '^(PRETTY_NAME|VERSION_ID)=' /etc/os-release; fi
uptime 2>/dev/null
printf 'IP：%s\n' "$(hostname -I 2>/dev/null || echo 未知)"

section "插件与构建"
if [ -d "$PLUGIN_DIR" ]; then
  printf '插件目录：%s\n' "$PLUGIN_DIR"
  printf '版本：%s\n' "$(value_of version "$PLUGIN_DIR/package.json")"
  if [ -f "$PLUGIN_DIR/build-info.json" ]; then
    printf '构建标识：%s\n' "$(value_of id "$PLUGIN_DIR/build-info.json")"
    printf '源码编号：%s\n' "$(value_of commit "$PLUGIN_DIR/build-info.json")"
    printf '打包时间：%s\n' "$(value_of builtAt "$PLUGIN_DIR/build-info.json")"
    printf '标记来源：%s\n' "$(value_of source "$PLUGIN_DIR/build-info.json")"
  else
    warn "没有 build-info.json：旧包或本地开发目录，不能确认设备上运行的是哪个构建"
  fi
else
  warn "没有找到插件目录：$PLUGIN_DIR"
fi

section "运行环境"
NODE="$PLUGIN_DIR/runtime/node/bin/node"
PI_CLI="$PLUGIN_DIR/runtime/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js"
STT="$PLUGIN_DIR/runtime/stt/bin/sherpa-onnx-offline"
if [ -x "$NODE" ]; then
  printf 'Node：%s\n' "$(run_limited 10 "$NODE" --version 2>&1 | tail -n 1)"
else
  warn "缺少 Node 运行环境：$NODE"
fi
if [ -x "$NODE" ] && [ -f "$PI_CLI" ]; then
  printf 'Pi：%s\n' "$(run_limited 60 "$NODE" "$PI_CLI" --version 2>&1 | tail -n 1)"
else
  warn "缺少 Pi 运行文件：$PI_CLI"
fi
if [ -x "$STT" ]; then
  if LD_LIBRARY_PATH="$PLUGIN_DIR/runtime/stt/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" run_limited 30 "$STT" --help >/dev/null 2>&1; then
    echo 'STT 引擎：可以启动'
  else
    warn 'STT 引擎无法启动'
  fi
else
  warn "缺少 STT 引擎：$STT"
fi
if have pw-record; then echo '录音工具：pw-record 可用'; else warn '缺少 pw-record，语音输入不可用'; fi
if have pactl; then pactl info 2>/dev/null | grep -E '^(Server Name|Default Source)'; fi

section "进程与内存"
FOUND=0
for pattern in 'pi-coding-agent/dist/bundle/cli.js' 'sherpa-onnx-offline' 'pw-record'; do
  while read -r pid; do
    [ -z "$pid" ] && continue
    FOUND=1
    rss="$(awk '/VmRSS/{print $2 $3}' "/proc/$pid/status" 2>/dev/null)"
    printf '%s  %-10s %s\n' "$pid" "${rss:-?}" "$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null | cut -c1-110)"
  done <<EOF
$(pgrep -f "$pattern" 2>/dev/null | grep -v "^$$\$")
EOF
done
[ "$FOUND" = 0 ] && echo '没有 Pi 或语音相关进程（空闲时正常）'
pgrep -af decky_plugin 2>/dev/null | head -n 3

section "存储"
df -h "$HOME_DIR" /tmp 2>/dev/null
free -m 2>/dev/null | head -n 3
du -sh "$DATA_DIR" "$LOG_DIR" 2>/dev/null

section "日志"
printf '日志目录：%s\n' "$LOG_DIR"
printf '调试日志：%s\n' "$(if [ -f "$SETTINGS_DIR/debug-log" ] || [ "${DECK_AGENT_DEBUG:-}" = "1" ]; then echo 已开启; else echo "未开启（需要细节时 touch $SETTINGS_DIR/debug-log 后在 Decky 重载插件）"; fi)"
if [ -d "$LOG_DIR" ]; then
  ls -lh "$LOG_DIR" 2>/dev/null | tail -n +2 | awk '{print $5, $6, $7, $8, $9}'
fi
CURRENT="$LOG_DIR/deck-agent.log"
if [ -f "$CURRENT" ]; then
  echo "--- 最近 $LINES 行 ---"
  tail -n "$LINES" "$CURRENT"
  echo '--- 最近的错误和警告 ---'
  grep -hE ' (ERROR|WARNING) ' "$CURRENT" 2>/dev/null | tail -n 20
else
  echo "还没有日志文件：$CURRENT"
fi

section "语音模型"
if [ -f "$DATA_DIR/voice/model/verified.json" ]; then
  echo "语音模型：已校验"
  du -h "$DATA_DIR/voice/model" 2>/dev/null
else
  echo '语音模型：未下载'
fi
[ -f "$DATA_DIR/voice/model.part" ] && echo "未完成下载：$(du -h "$DATA_DIR/voice/model.part" 2>/dev/null | cut -f1)"

section "数据"
if [ -d "$DATA_DIR/sessions" ]; then
  printf '会话文件：%s 个\n' "$(find "$DATA_DIR/sessions" -maxdepth 1 -name '*.jsonl' 2>/dev/null | wc -l)"
fi
[ -f "$DATA_DIR/sessions.json" ] && echo '会话元数据：存在'

if [ "$STATUS" = 0 ]; then
  printf '\n诊断完成：未发现缺失的运行文件。\n'
else
  printf '\n诊断完成：上面带 ! 的项目需要处理。\n'
fi
exit "$STATUS"
