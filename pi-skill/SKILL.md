---
name: bbc
description: 播放/停止 BBC 广播电台（Radio 1-6、1Xtra、4 Extra、World Service），并用本地 faster-whisper 做实时语音转文字。当用户说"听bbc4/bbc1/bbcws"、"播放bbc"、"停/停止/别放了/关掉"、"转录/转文字/字幕"等时使用。Play, stop, or transcribe BBC radio stations with mpv and faster-whisper.
---

# BBC Radio 播放控制（pi 技能）

本技能是 [bbc-radio](https://github.com/mrusa01/bbc-radio) 项目的 pi 集成层，所有逻辑复用项目里的 `bbc_radio` 包。

## 前提

项目目录需在环境变量 `BBC_RADIO_HOME` 中，或放在默认位置 `~/apps/bbc-radio`。
若两者都没有，脚本会报错提示。

## 用法

- 播放：`scripts/play.sh <station>`
- 停止：`scripts/stop.sh`
- 转录：`scripts/transcribe.sh <station>`

播放后立即回复用户，不要等待。

## 电台对照

| 用户说法 | 参数 | 电台 |
|---|---|---|
| bbc1 / 一 | `1` | Radio 1 |
| bbc2 / 二 | `2` | Radio 2 |
| bbc3 / 三 | `3` | Radio 3 |
| bbc4 / 四 | `4` | Radio 4 |
| bbc5 / 五 | `5` | Radio 5 Live |
| bbc6 / 六 | `6` | Radio 6 Music |
| bbc1x | `1x` | Radio 1Xtra |
| bbc1a / anthems | `1a` | Radio 1 Anthems |
| bbc1d / dance | `1d` | Radio 1 Dance |
| bbc3u / unwind | `3u` | Radio 3 Unwind |
| bbc4x | `4x` | Radio 4 Extra |
| bbcws / 世界台 | `ws` | World Service |

- 用户说"听bbc4" → `scripts/play.sh 4`
- 用户说"停"、"停止"、"别放了" → `scripts/stop.sh`
- 未指定电台 → 默认 `4`

## 实时转录

- `scripts/transcribe.sh <station>`：后台启动，输出写入 `~/bbc_transcript.log`
- 用户说"转录"、"转文字"时启动；说"停转录"时 `pkill -f 'bbc_radio.transcri[b]e'`
- 每约 32 秒输出一段带时间戳的文本，可用 `tail -f ~/bbc_transcript.log` 查看
- 转录不影响播放

## 注意事项

- mpv 优先用系统 `mpv`，否则自动回退到 flatpak 版 `io.mpv.Mpv`。
- 流地址均为大陆可直连的 Akamai `ww` 池或 World Service。
- 转录依赖 faster-whisper，装在项目的 venv 里（`install.sh --with-asr`）。
