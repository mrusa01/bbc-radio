#!/usr/bin/env bash
# 播放 BBC 电台。用法: play.sh <station>
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="$("$HERE/_home.sh")"
exec python3 "$HOME_DIR/bbc_radio_cli.py" play "${1:-4}"
