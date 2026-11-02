#!/usr/bin/env bash
# 定位 bbc-radio 项目目录
# 优先 $BBC_RADIO_HOME，其次 ~/apps/bbc-radio
set -euo pipefail

if [ -n "${BBC_RADIO_HOME:-}" ] && [ -d "$BBC_RADIO_HOME/bbc_radio" ]; then
  echo "$BBC_RADIO_HOME"
  exit 0
fi

for candidate in "$HOME/apps/bbc-radio" "$HOME/bbc-radio"; do
  if [ -d "$candidate/bbc_radio" ]; then
    echo "$candidate"
    exit 0
  fi
done

echo "错误: 找不到 bbc-radio 项目目录。" >&2
echo "请设置环境变量 BBC_RADIO_HOME 指向项目根目录，或克隆到 ~/apps/bbc-radio。" >&2
exit 1
