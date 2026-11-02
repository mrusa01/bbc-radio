#!/usr/bin/env bash
# 停止 BBC 播放。
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="$("$HERE/_home.sh")"
exec python3 "$HOME_DIR/bbc_radio_cli.py" stop
