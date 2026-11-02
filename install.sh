#!/usr/bin/env bash
# BBC Radio 安装脚本
#
# 用法:
#   ./install.sh              安装命令行 + 图形界面 + 桌面图标
#   ./install.sh --cli-only   只装命令行
#   ./install.sh --with-asr   额外安装实时转录依赖（faster-whisper）
#
# 会把可执行文件软链到 ~/.local/bin，桌面图标装到 ~/.local/share/applications。
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
CLI_ONLY=0
WITH_ASR=0

for arg in "$@"; do
  case "$arg" in
    --cli-only)  CLI_ONLY=1 ;;
    --with-asr)  WITH_ASR=1 ;;
    -h|--help)   sed -n '3,9p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "未知参数: $arg" >&2; exit 1 ;;
  esac
done

info() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*"; }

# ---------- 检查 mpv ----------
info "检查 mpv…"
if command -v mpv >/dev/null 2>&1; then
  info "找到 mpv: $(command -v mpv)"
elif command -v flatpak >/dev/null 2>&1 && flatpak list --app --columns=application 2>/dev/null | grep -q '^io\.mpv\.Mpv$'; then
  info "找到 flatpak 版 mpv (io.mpv.Mpv)"
else
  warn "未找到 mpv。请任选一种安装："
  warn "  sudo apt install mpv"
  warn "  flatpak install flathub io.mpv.Mpv"
fi

# ---------- 命令行入口 ----------
info "安装命令行入口到 $BIN_DIR"
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/bbc-radio" <<EOF
#!/usr/bin/env bash
exec python3 "$HERE/bbc_radio_cli.py" "\$@"
EOF
chmod +x "$BIN_DIR/bbc-radio"

# ---------- 图形界面 + 桌面图标 ----------
if [ "$CLI_ONLY" -eq 0 ]; then
  info "安装图形界面入口"
  cat > "$BIN_DIR/bbc-radio-gui" <<EOF
#!/usr/bin/env bash
exec python3 "$HERE/bbc_radio_gui.py" "\$@"
EOF
  chmod +x "$BIN_DIR/bbc-radio-gui"

  info "安装桌面图标"
  mkdir -p "$APP_DIR"
  cat > "$APP_DIR/bbc-radio.desktop" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=BBC Radio
Name[zh_CN]=BBC 电台
Comment=BBC Radio player with station select and live transcription
Comment[zh_CN]=BBC 电台播放器（选台 / 音量 / 实时转录）
Exec=$BIN_DIR/bbc-radio-gui
Icon=audio-x-generic
Terminal=false
Categories=AudioVideo;Audio;Player;
StartupNotify=true
EOF
  chmod +x "$APP_DIR/bbc-radio.desktop"
  command -v update-desktop-database >/dev/null 2>&1 && \
    update-desktop-database "$APP_DIR" 2>/dev/null || true
fi

# ---------- 转录依赖 ----------
if [ "$WITH_ASR" -eq 1 ]; then
  info "安装转录依赖（faster-whisper）…"
  VENV="$HOME/.local/share/bbc-radio/venv"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --upgrade pip
  "$VENV/bin/pip" install faster-whisper==1.2.1 'av==12.3.0'
  warn "转录会让 bbc-radio 使用该 venv 的 python："
  warn "  $VENV/bin/python $HERE/bbc_radio_cli.py transcribe 4"
fi

cat <<EOF

安装完成。

  播放：      bbc-radio play 4
  停止：      bbc-radio stop
  列出电台：  bbc-radio list
  实时转录：  bbc-radio transcribe 4
  图形界面：  bbc-radio-gui      （或从应用菜单搜索 "BBC"）

如果 bbc-radio 命令找不到，请确认 $BIN_DIR 在 PATH 中。
EOF
