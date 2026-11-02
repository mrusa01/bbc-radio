#!/usr/bin/env bash
# BBC 实时转录（后台运行，输出到 ~/bbc_transcript.log）
# 用法: transcribe.sh [电台: 1-6,1x,4x,ws，默认4]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="$("$HERE/_home.sh")"
STATION="${1:-4}"
LOG="$HOME/bbc_transcript.log"

# 用项目 venv（若存在）以获得 faster-whisper
VENV_PY="$HOME/.local/share/bbc-radio/venv/bin/python3"
PY=python3
[ -x "$VENV_PY" ] && PY="$VENV_PY"

nohup "$PY" "$HOME_DIR/bbc_radio_cli.py" transcribe "$STATION" \
  >>"$LOG" 2>&1 &
echo "转录已启动（电台 $STATION），日志: $LOG"
