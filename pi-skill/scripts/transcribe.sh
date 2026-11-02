#!/usr/bin/env bash
# BBC 实时转录（后台运行，输出到 ~/bbc_transcript.log）
# 用法: transcribe.sh [电台: 1-6,1x,4x,ws，默认4]
#
# 会依次尝试：
#   1. $BBC_RADIO_PYTHON
#   2. ~/.local/share/bbc-radio/venv/bin/python3   （install.sh --with-asr 建的）
#   3. ~/.local/venvs/whisper/bin/python3          （用户已有的 whisper 环境）
#   4. 系统 python3
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="$("$HERE/_home.sh")"
STATION="${1:-4}"
LOG="$HOME/bbc_transcript.log"

pick_python() {
  local c
  for c in "${BBC_RADIO_PYTHON:-}" \
           "$HOME/.local/share/bbc-radio/venv/bin/python3" \
           "$HOME/.local/venvs/whisper/bin/python3"; do
    [ -n "$c" ] && [ -x "$c" ] || continue
    if "$c" -c 'import faster_whisper' >/dev/null 2>&1; then
      echo "$c"; return 0
    fi
  done
  if python3 -c 'import faster_whisper' >/dev/null 2>&1; then
    echo python3; return 0
  fi
  return 1
}

PY="$(pick_python)" || {
  echo "错误: 未找到装有 faster-whisper 的 Python。" >&2
  echo "  安装：./install.sh --with-asr" >&2
  exit 1
}

nohup "$PY" "$HOME_DIR/bbc_radio_cli.py" transcribe "$STATION" \
  >>"$LOG" 2>&1 &
echo "转录已启动（电台 $STATION，解释器 $PY），日志: $LOG"
